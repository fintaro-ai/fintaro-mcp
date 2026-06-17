"""Schema-drift contract for the narrow invoice/transaction projections.

These guards run standalone in this repo: the projections must never carry raw
OCR text, raw extraction JSON, tax-IDs/emails, or transaction match internals.

The field-existence cross-check against the backend models (that every projected
field actually exists on the source model / the gateway allowlist) runs in
Fintaro's internal CI, where the backend models are importable. It is
intentionally not reproduced here to avoid a coupling that would silently skip
in this repo.
"""

from __future__ import annotations

from fintaro_mcp.schemas import InvoiceSummary, TransactionSummary

_FORBIDDEN_RAW_PII = {
    "ocr_text",
    "raw_json",
    "seller_tax_id",
    "buyer_tax_id",
    "seller_emails",
    "sender_email",
}

# Transaction-side forbidden keys: match internals, flags, and the
# attacker-influenceable reasoning text must never be projected.
_FORBIDDEN_TX = {
    "organizationId",
    "isPrivate",
    "aiReasoning",
    "matchConfidence",
    "matchType",
    "matchGroups",
    "documents",
}


def test_projection_excludes_raw_and_pii():
    projected = set(InvoiceSummary.model_fields.keys())
    leaked = _FORBIDDEN_RAW_PII & projected
    assert not leaked, f"InvoiceSummary must not expose raw/PII fields: {leaked}"


def test_transaction_projection_excludes_match_internals():
    projected = set(TransactionSummary.model_fields.keys())
    leaked = _FORBIDDEN_TX & projected
    assert not leaked, f"TransactionSummary must not expose match internals/flags: {leaked}"
