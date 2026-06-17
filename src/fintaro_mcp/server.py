"""Fintaro MCP server — FastMCP stdio entrypoint.

Tools (all bound to the org carried by the presented ``ftk_`` key):

* ``whoami`` — which org/scopes/expiry the key carries.
* ``upload_invoice`` — upload a local receipt (PDF/PNG/JPEG/WebP), client-side
  validated, returns ``{invoice_id, status: "processing", deduplicated}``.
* ``get_invoice`` — a narrow, PII-stripped projection of one invoice.
* ``list_invoices`` — one bounded page of narrow invoice projections.
* ``list_transactions`` — one bounded page of narrow, PII-stripped transaction
  projections: ``{"transactions": [...], "total", "offset", "limit", "returned",
  "hasMore"}``. The caller pages with ``offset``/``limit`` and may narrow with
  ``date_from``/``date_to`` instead of pulling all history.
* ``list_unmatched`` — same shape/paging, only transactions still missing a receipt.

The pure ``*_impl`` functions take an explicit client so they are unit-testable
against a fake/mocked gateway; the ``@mcp.tool()`` wrappers build a real client
from the environment.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Mapping

from mcp.server.fastmcp import FastMCP

from fintaro_mcp.client import GatewayClient
from fintaro_mcp.config import Config
from fintaro_mcp.schemas import InvoiceSummary, TransactionSummary

mcp = FastMCP("fintaro")

#: Client-side upload guards.
_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


def _client() -> GatewayClient:
    cfg = Config.from_env()
    return GatewayClient(base_url=cfg.base_url, api_key=cfg.api_key)


def _org() -> str:
    """The org the key is bound to, discovered via whoami at tool time."""
    with _client() as client:
        return whoami_impl(client)["organization_id"]


# --------------------------------------------------------------------------- #
# Pure impls (testable with a fake client)
# --------------------------------------------------------------------------- #
def whoami_impl(client: Any) -> dict:
    """Introspect the presented key: org/scopes/expiry.

    The gateway derives the org from the key itself, so there is NO
    ``organization_id`` param.
    """
    return client.get("/api-keys/whoami")


def upload_invoice_impl(client: Any, organization_id: str, file_path: str) -> dict:
    """Validate a local file client-side, then upload it as a receipt."""
    path = Path(file_path)
    if not path.is_file():
        raise ValueError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type {ext!r}. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}.")

    size = path.stat().st_size
    if size == 0:
        raise ValueError("File is empty.")
    if size > _MAX_UPLOAD_BYTES:
        raise ValueError(f"File is {size} bytes; the maximum upload size is {_MAX_UPLOAD_BYTES} bytes (25 MB).")

    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as fh:
        files = {"file": (path.name, fh.read(), content_type)}
        result = client.post_multipart(
            "/upload/",
            files=files,
            data={"organization_id": organization_id},
        )

    return {
        "invoice_id": result.get("id"),
        "status": "processing",
        "deduplicated": bool(result.get("deduplicated", False)),
    }


def get_invoice_impl(client: Any, organization_id: str, invoice_id: str) -> dict:
    """Fetch one invoice as a narrow, PII-stripped projection."""
    row = client.get(f"/invoices/{invoice_id}", params={"organization_id": organization_id})
    return InvoiceSummary.from_gateway(row).model_dump()


#: Gateway max page size for /invoices/; also the default and clamp ceiling.
_INVOICE_PAGE_LIMIT = 100


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(int(value), hi))


def list_invoices_impl(client: Any, organization_id: str, *, offset: int = 0, limit: int = _INVOICE_PAGE_LIMIT) -> dict:
    """List one bounded page of the org's invoices, newest-first.

    The gateway orders ``/invoices/`` by ``created_at`` desc, so page 0 holds the
    newest invoices (a just-uploaded one is reachable there). ONE call fetches ONE
    page; the caller advances ``offset`` to read further. ``/invoices/`` returns a
    bare list with no total, so ``hasMore`` is inferred from page fullness and
    ``total`` is ``None`` (unknown).

    Returns ``{"invoices", "total", "offset", "limit", "returned", "hasMore"}``.
    """
    offset = max(0, int(offset))
    limit = _clamp(limit, 1, _INVOICE_PAGE_LIMIT)
    page = (
        client.get(
            "/invoices/",
            params={"organization_id": organization_id, "offset": offset, "limit": limit},
        )
        or []
    )
    summaries = [InvoiceSummary.from_gateway(row).model_dump() for row in page]
    return {
        "invoices": summaries,
        "total": None,
        "offset": offset,
        "limit": limit,
        "returned": len(summaries),
        "hasMore": len(page) >= limit,
    }


#: Gateway max page size for /transactions/search; also the default and clamp ceiling.
_SEARCH_PAGE_LIMIT = 200


def _transaction_rows(payload: Any) -> list:
    """Unwrap the gateway's ``{data, pagination}`` search envelope (a bare list
    is accepted too, for forward/backward compatibility). A mapping WITHOUT a
    ``data`` key is an unexpected contract change — fail loudly rather than
    silently reporting "no transactions"."""
    if isinstance(payload, Mapping):
        if "data" not in payload:
            raise ValueError("Unexpected /transactions/search payload: missing 'data' key")
        return list(payload.get("data") or [])
    return list(payload or [])


def _search_transaction_summaries(
    client: Any,
    organization_id: str,
    *,
    offset: int = 0,
    limit: int = _SEARCH_PAGE_LIMIT,
    date_from: str | None = None,
    date_to: str | None = None,
    extra_params: Mapping[str, Any] | None = None,
) -> dict:
    """Fetch ONE bounded page of matching transactions as narrow projections.

    One call == one gateway request. ``offset``/``limit`` (clamped to the gateway
    page size) and the optional ``date_from``/``date_to`` ISO bounds let the caller
    page and narrow the result; ``hasMore`` (verbatim from the gateway) and
    ``total`` tell the caller whether to advance ``offset``. This replaces the old
    page-to-a-safety-cap loop that silently dropped everything past 1000 rows.

    Returns ``{"transactions", "total", "offset", "limit", "returned", "hasMore"}``.
    """
    offset = max(0, int(offset))
    limit = _clamp(limit, 1, _SEARCH_PAGE_LIMIT)
    params: dict = {"organization_id": organization_id, "limit": limit, "offset": offset}
    if date_from is not None:
        params["dateFrom"] = date_from
    if date_to is not None:
        params["dateTo"] = date_to
    if extra_params:
        params.update(extra_params)

    payload = client.get("/transactions/search", params=params)
    rows = _transaction_rows(payload)
    transactions = [TransactionSummary.from_gateway(row).model_dump() for row in rows]

    pagination: Mapping = {}
    if isinstance(payload, Mapping):
        pagination = payload.get("pagination") or {}
    total = pagination.get("total")
    return {
        "transactions": transactions,
        "total": total if total is not None else len(transactions),
        "offset": offset,
        "limit": limit,
        "returned": len(transactions),
        "hasMore": bool(pagination.get("hasMore")),
    }


def list_transactions_impl(
    client: Any,
    organization_id: str,
    *,
    offset: int = 0,
    limit: int = _SEARCH_PAGE_LIMIT,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """One page of the org's transactions as narrow, PII-stripped projections.

    Returns ``{"transactions", "total", "offset", "limit", "returned", "hasMore"}``;
    ``hasMore`` true means advance ``offset`` by ``limit`` for the next page."""
    return _search_transaction_summaries(
        client, organization_id, offset=offset, limit=limit, date_from=date_from, date_to=date_to
    )


def list_unmatched_impl(
    client: Any,
    organization_id: str,
    *,
    offset: int = 0,
    limit: int = _SEARCH_PAGE_LIMIT,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """One page of transactions that still need a receipt (unmatched).

    Same envelope as ``list_transactions_impl``."""
    return _search_transaction_summaries(
        client,
        organization_id,
        offset=offset,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        extra_params={"matchStatus": "unmatched"},
    )


def monatsabschluss_check_text() -> str:
    """German guidance prompt for a pre-close ("Monatsabschluss") review."""
    return (
        "Du bist Buchhaltungs-Assistent fuer den Monatsabschluss.\n\n"
        "Vorgehen vor dem Abschluss:\n"
        "1. Rufe das Tool `list_unmatched` auf, um Transaktionen ohne Beleg "
        "(unmatched) zu finden. Das Tool liefert eine Seite pro Aufruf; solange "
        "`hasMore` true ist, rufe es erneut mit um `limit` erhoehtem `offset` auf, "
        "bis alle offenen Posten erfasst sind. Fuer einen Monat kannst du den "
        "Zeitraum mit `date_from`/`date_to` (ISO) eingrenzen.\n"
        "2. Fasse zusammen, welche Belege noch fehlen — pro offener Transaktion "
        "Datum, Betrag und Gegenseite —, damit der Nutzer sie nachreichen kann.\n"
        "3. Weise darauf hin, dass eine automatische Pruefung des Export-Status "
        "(BMD/UVA) noch nicht verfuegbar ist und spaeter kommt.\n\n"
        "Schliesse den Monat erst ab, wenn keine Transaktionen mehr unmatched "
        "sind bzw. der Nutzer die fehlenden Belege bestaetigt hat."
    )


# --------------------------------------------------------------------------- #
# MCP tool / prompt wrappers
# --------------------------------------------------------------------------- #
@mcp.tool()
def whoami() -> dict:
    """Show which organization and scopes the configured API key is bound to."""
    with _client() as client:
        return whoami_impl(client)


@mcp.tool()
def upload_invoice(file_path: str) -> dict:
    """Upload a local receipt file (PDF/PNG/JPEG/WebP) to Fintaro for processing."""
    with _client() as client:
        return upload_invoice_impl(client, _org(), file_path)


@mcp.tool()
def get_invoice(invoice_id: str) -> dict:
    """Return a narrow, PII-free summary of a single invoice."""
    with _client() as client:
        return get_invoice_impl(client, _org(), invoice_id)


@mcp.tool()
def list_invoices(offset: int = 0, limit: int = _INVOICE_PAGE_LIMIT) -> dict:
    """List one page of the organization's invoices as narrow, PII-free summaries.

    Newest-first. One call returns one page; if `hasMore` is true, call again with
    `offset` advanced by `limit` (clamped to 100). `total` is unknown (the gateway
    list endpoint returns no count).

    Returns {"invoices", "total", "offset", "limit", "returned", "hasMore"}."""
    with _client() as client:
        return list_invoices_impl(client, _org(), offset=offset, limit=limit)


@mcp.tool()
def list_transactions(
    offset: int = 0,
    limit: int = _SEARCH_PAGE_LIMIT,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """List one page of the organization's bank transactions as narrow summaries.

    One call returns one page; if `hasMore` is true, call again with `offset`
    advanced by `limit` (clamped to 200). Narrow the window with `date_from` /
    `date_to` (ISO dates, e.g. "2026-06-01") to cover a period without paging all
    history.

    Returns {"transactions", "total", "offset", "limit", "returned", "hasMore"}."""
    with _client() as client:
        return list_transactions_impl(client, _org(), offset=offset, limit=limit, date_from=date_from, date_to=date_to)


@mcp.tool()
def list_unmatched(
    offset: int = 0,
    limit: int = _SEARCH_PAGE_LIMIT,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """List one page of transactions that still need a matching receipt.

    Same paging/filtering contract as `list_transactions`: one page per call,
    advance `offset` by `limit` while `hasMore`, optionally bound by `date_from` /
    `date_to`. For a month-end close, pass the period's bounds.

    Returns {"transactions", "total", "offset", "limit", "returned", "hasMore"}."""
    with _client() as client:
        return list_unmatched_impl(client, _org(), offset=offset, limit=limit, date_from=date_from, date_to=date_to)


@mcp.prompt()
def monatsabschluss_check() -> str:
    """Guided pre-close review: find transactions still missing a receipt."""
    return monatsabschluss_check_text()


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
