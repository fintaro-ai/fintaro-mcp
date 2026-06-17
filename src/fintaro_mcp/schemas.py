"""Vendored, narrow projections of gateway payloads.

The ``InvoiceSummary`` projection is the in-band PII / prompt-injection guard.
It is a strict allowlist: attacker-controlled raw fields on an invoice
(``ocr_text``, ``raw_json``) and PII (``seller_tax_id``, ``buyer_tax_id``,
``seller_emails``, ``sender_email``) must NEVER reach the agent context.

``from_gateway`` builds the projection by iterating the projection's *own*
``model_fields`` — never the gateway row's keys — so any new/unknown gateway
field (raw or PII) is structurally incapable of passing through.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from pydantic import BaseModel


class InvoiceSummary(BaseModel):
    """Narrow, safe view of an invoice for the agent.

    Every field here MUST exist on the backend invoice model (enforced by the
    schema-drift contract test) and MUST NOT be a raw/PII field.
    """

    id: str
    status: Optional[str] = None
    seller_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    amount_gross: Optional[float] = None
    currency: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_gateway(cls, row: Mapping[str, Any]) -> "InvoiceSummary":
        """Project a raw gateway invoice row through the allowlist.

        Iterates the projection's own fields so unknown gateway keys (raw OCR,
        PII, …) can never leak into the output.
        """
        projected = {name: row.get(name) for name in cls.model_fields}
        return cls.model_validate(projected)


class TransactionSummary(BaseModel):
    """Narrow, safe view of a bank transaction for the agent.

    Field names match the gateway's serialized ``/transactions/search`` row keys
    (camelCase where the wire format is camelCase). Match internals
    (``matchGroups``/``documents``/``aiReasoning``) and flags
    (``isPrivate``/``organizationId``) must NEVER reach the agent context; the
    gateway projects server-side and this model mirrors that allowlist as
    defense-in-depth (pinned by the schema-contract tests).
    """

    id: str
    date: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    merchant: Optional[str] = None
    counterparty: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    matchStatus: Optional[str] = None

    @classmethod
    def from_gateway(cls, row: Mapping[str, Any]) -> "TransactionSummary":
        """Project a raw gateway transaction row through the allowlist."""
        projected = {name: row.get(name) for name in cls.model_fields}
        return cls.model_validate(projected)
