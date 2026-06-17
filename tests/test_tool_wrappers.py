"""Tests for MCP _org() binding and auth-error propagation (review, 2026-06-13T1357Z).

Covers:
- test-mcp-tool-wrapper-binds-discovered-org: _org() resolves org-id via whoami
  and the org-id is bound into the downstream impl call (caller cannot override).
- test-mcp-tool-wrapper-propagates-auth-error: whoami raises AuthError ->
  wrapper raises, not an opaque crash.

The @mcp.tool() wrappers all share the same pattern:
  with _client() as client:
      return *_impl(client, _org(), ...)

We test _org() directly and one wrapper's full call chain by patching _client()
to return a controlled fake context manager.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fintaro_mcp import server
from fintaro_mcp.client import AuthError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeClient:
    """Records get() calls; returns configured results."""

    def __init__(self, whoami_result=None, raise_on_get: Exception | None = None):
        self._whoami_result = whoami_result
        self._raise_on_get = raise_on_get
        self.get_calls: list[tuple] = []

    def get(self, path, *, params=None):
        self.get_calls.append((path, params))
        if self._raise_on_get is not None:
            raise self._raise_on_get
        return self._whoami_result


def _patch_client(fake: _FakeClient):
    """Return a context-manager patch for server._client() that yields fake."""

    @contextmanager
    def _ctx_mgr():
        yield fake

    return patch.object(server, "_client", return_value=_ctx_mgr())


# ---------------------------------------------------------------------------
# test-mcp-tool-wrapper-binds-discovered-org
# ---------------------------------------------------------------------------


def test_org_resolves_organization_id_from_whoami() -> None:
    """_org() calls whoami and returns the organization_id."""
    fake = _FakeClient(whoami_result={"organization_id": "org-X", "scopes": ["invoices:read"], "expires_at": None})

    with _patch_client(fake):
        org_id = server._org()

    assert org_id == "org-X"
    assert len(fake.get_calls) == 1
    assert fake.get_calls[0][0] == "/api-keys/whoami"


def test_list_invoices_wrapper_uses_org_from_whoami(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_invoices() wrapper binds the org discovered via whoami — caller cannot override."""
    # We need two sequential client calls: one for _org() (whoami), one for
    # list_invoices_impl (the gateway GET).  Use a list to serve results in order.
    get_results = [
        {"organization_id": "org-X"},  # _org() whoami call
        [
            {
                "id": "inv1",
                "status": "processed",  # list_invoices_impl data
                "seller_name": "A",
                "invoice_number": "N",
                "invoice_date": "2026-01-01",
                "amount_gross": 10.0,
                "currency": "EUR",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ],
    ]

    class _SequentialFakeClient:
        def __init__(self):
            self.get_calls: list[tuple] = []

        def get(self, path, *, params=None):
            self.get_calls.append((path, params))
            return get_results.pop(0)

    fake = _SequentialFakeClient()
    captured_org_ids: list[str] = []
    original_impl = server.list_invoices_impl

    def _spy_impl(client, organization_id: str, **kwargs):
        captured_org_ids.append(organization_id)
        return original_impl(client, organization_id, **kwargs)

    monkeypatch.setattr(server, "list_invoices_impl", _spy_impl)

    with patch.object(server, "_client") as mock_client:
        mock_client.return_value.__enter__ = lambda self: fake
        mock_client.return_value.__exit__ = lambda self, *a: None

        server.list_invoices()

    # The org passed to list_invoices_impl MUST come from whoami, not from any caller argument
    assert captured_org_ids == ["org-X"]
    # First call was whoami
    assert fake.get_calls[0][0] == "/api-keys/whoami"


# ---------------------------------------------------------------------------
# test-mcp-tool-wrapper-propagates-auth-error
# ---------------------------------------------------------------------------


def test_org_propagates_auth_error_from_whoami() -> None:
    """When whoami raises AuthError, _org() re-raises it (not an opaque crash)."""
    auth_err = AuthError("API key is revoked or invalid")
    fake = _FakeClient(raise_on_get=auth_err)

    with _patch_client(fake):
        with pytest.raises(AuthError, match="revoked or invalid"):
            server._org()


def test_list_invoices_wrapper_surfaces_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auth error from _org() propagates through the list_invoices wrapper."""
    auth_err = AuthError("Token expired")
    fake = _FakeClient(raise_on_get=auth_err)

    with patch.object(server, "_client") as mock_client:
        mock_client.return_value.__enter__ = lambda self: fake
        mock_client.return_value.__exit__ = lambda self, *a: None

        with pytest.raises(AuthError, match="Token expired"):
            server.list_invoices()
