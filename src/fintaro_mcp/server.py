"""Fintaro MCP server — FastMCP stdio entrypoint.

Tools (all bound to the org carried by the presented ``ftk_`` key):

* ``whoami`` — which org/scopes/expiry the key carries.
* ``upload_invoice`` — upload a local receipt (PDF/PNG/JPEG/WebP), client-side
  validated, returns ``{invoice_id, status: "processing", deduplicated}``.
* ``get_invoice`` — a narrow, PII-stripped projection of one invoice.
* ``list_invoices`` — narrow projections of the org's invoices.
* ``list_transactions`` — narrow, PII-stripped projections of the org's
  transactions, paginated to exhaustion: ``{"transactions": [...], "total": n}``.
* ``list_unmatched`` — same shape, only transactions still missing a receipt.

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


#: Gateway page size for /invoices/, and a safety cap across pages.
_INVOICE_PAGE_LIMIT = 100
_INVOICE_MAX_ROWS = 1000


def list_invoices_impl(client: Any, organization_id: str) -> list[dict]:
    """List the org's invoices as narrow projections, newest-first.

    The gateway orders ``/invoices/`` by ``created_at`` desc and caps each page,
    so this pages through to exhaustion (bounded by a safety cap). Paging is what
    makes a just-uploaded invoice reachable instead of stranded beyond an
    unpaginated first page.
    """
    summaries: list[dict] = []
    offset = 0
    while True:
        page = (
            client.get(
                "/invoices/",
                params={
                    "organization_id": organization_id,
                    "offset": offset,
                    "limit": _INVOICE_PAGE_LIMIT,
                },
            )
            or []
        )
        summaries.extend(InvoiceSummary.from_gateway(row).model_dump() for row in page)
        if len(page) < _INVOICE_PAGE_LIMIT or len(summaries) >= _INVOICE_MAX_ROWS:
            break
        offset += len(page)
    return summaries


#: Gateway page-size cap for /transactions/search, and a safety cap across pages.
_SEARCH_PAGE_LIMIT = 200
_SEARCH_MAX_ROWS = 1000


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
    client: Any, organization_id: str, extra_params: Mapping[str, Any] | None = None
) -> dict:
    """Fetch matching transactions across ALL result pages as narrow projections.

    Returns ``{"transactions": [...], "total": n}`` so the caller can detect the
    rare case where the safety cap truncated the list (``total > len(transactions)``).
    """
    params: dict = {"organization_id": organization_id, "limit": _SEARCH_PAGE_LIMIT, "offset": 0}
    if extra_params:
        params.update(extra_params)

    transactions: list[dict] = []
    total: int | None = None
    while True:
        payload = client.get("/transactions/search", params=dict(params))
        rows = _transaction_rows(payload)
        transactions.extend(TransactionSummary.from_gateway(row).model_dump() for row in rows)
        if not isinstance(payload, Mapping):
            break
        pagination = payload.get("pagination") or {}
        if total is None:
            total = pagination.get("total")
        if not pagination.get("hasMore") or not rows or len(transactions) >= _SEARCH_MAX_ROWS:
            break
        params["offset"] += len(rows)

    return {"transactions": transactions, "total": total if total is not None else len(transactions)}


def list_transactions_impl(client: Any, organization_id: str) -> dict:
    """The org's transactions as narrow, PII-stripped projections.

    Returns ``{"transactions": [...], "total": n}``; ``total > len(transactions)``
    means the safety cap truncated the list."""
    return _search_transaction_summaries(client, organization_id)


def list_unmatched_impl(client: Any, organization_id: str) -> dict:
    """Transactions that still need a receipt (unmatched), as narrow projections.

    Same ``{"transactions", "total"}`` shape as ``list_transactions_impl``."""
    return _search_transaction_summaries(client, organization_id, {"matchStatus": "unmatched"})


def monatsabschluss_check_text() -> str:
    """German guidance prompt for a pre-close ("Monatsabschluss") review."""
    return (
        "Du bist Buchhaltungs-Assistent fuer den Monatsabschluss.\n\n"
        "Vorgehen vor dem Abschluss:\n"
        "1. Rufe das Tool `list_unmatched` auf, um alle Transaktionen zu finden, "
        "die noch keinen Beleg haben (unmatched).\n"
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
def list_invoices() -> list[dict]:
    """List the organization's invoices as narrow, PII-free summaries."""
    with _client() as client:
        return list_invoices_impl(client, _org())


@mcp.tool()
def list_transactions() -> dict:
    """List the organization's bank transactions as narrow, PII-free summaries.

    Returns {"transactions": [...], "total": n} across all result pages."""
    with _client() as client:
        return list_transactions_impl(client, _org())


@mcp.tool()
def list_unmatched() -> dict:
    """List transactions that still need a matching receipt, as narrow summaries.

    Returns {"transactions": [...], "total": n} across all result pages."""
    with _client() as client:
        return list_unmatched_impl(client, _org())


@mcp.prompt()
def monatsabschluss_check() -> str:
    """Guided pre-close review: find transactions still missing a receipt."""
    return monatsabschluss_check_text()


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
