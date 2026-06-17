"""B2 — gateway client: bearer injection + auth-error mapping."""

from __future__ import annotations

import httpx
import pytest
import respx

from fintaro_mcp.client import AuthError, GatewayClient, GatewayError

BASE = "https://api.fintaro.ai/api/v1"


def _client() -> GatewayClient:
    return GatewayClient(base_url=BASE, api_key="ftk_test")


@respx.mock
def test_get_injects_bearer_header():
    route = respx.get(f"{BASE}/invoices/abc").mock(
        return_value=httpx.Response(200, json={"id": "abc"})
    )
    with _client() as client:
        data = client.get("/invoices/abc")
    assert data == {"id": "abc"}
    assert route.calls.last.request.headers["Authorization"] == "Bearer ftk_test"


@respx.mock
def test_get_401_raises_auth_error_with_scope_hint():
    respx.get(f"{BASE}/invoices/abc").mock(return_value=httpx.Response(401, json={}))
    with _client() as client:
        with pytest.raises(AuthError) as exc:
            client.get("/invoices/abc")
    assert "scope" in str(exc.value).lower() or "key" in str(exc.value).lower()


@respx.mock
def test_get_403_raises_auth_error():
    respx.get(f"{BASE}/invoices/abc").mock(return_value=httpx.Response(403, json={}))
    with _client() as client:
        with pytest.raises(AuthError):
            client.get("/invoices/abc")


# --- Gap 2: revocation-style 401 must surface re-authenticate wording -------- #
@respx.mock
def test_get_401_revoked_key_maps_to_autherror_with_reauth_wording():
    """A 401 carrying a revocation-style detail still maps to AuthError, and the
    surfaced message tells the user the key is invalid/expired (re-authenticate),
    not merely that a scope is missing."""
    respx.get(f"{BASE}/invoices/abc").mock(
        return_value=httpx.Response(
            401, json={"detail": "API key has been revoked"}
        )
    )
    with _client() as client:
        with pytest.raises(AuthError) as exc:
            client.get("/invoices/abc")
    msg = str(exc.value).lower()
    # Re-authentication signal: the key itself is bad (invalid/expired/revoked).
    assert "invalid" in msg or "expired" in msg
    assert "401" in msg


@respx.mock
def test_get_500_raises_gateway_error_not_auth_error():
    respx.get(f"{BASE}/invoices/abc").mock(return_value=httpx.Response(500, json={}))
    with _client() as client:
        with pytest.raises(GatewayError) as exc:
            client.get("/invoices/abc")
    assert not isinstance(exc.value, AuthError)


@respx.mock
def test_get_404_raises_gateway_error():
    respx.get(f"{BASE}/invoices/abc").mock(return_value=httpx.Response(404, json={}))
    with _client() as client:
        with pytest.raises(GatewayError):
            client.get("/invoices/abc")


@respx.mock
def test_post_multipart_injects_bearer_and_sends_file():
    route = respx.post(f"{BASE}/upload/").mock(
        return_value=httpx.Response(200, json={"id": "inv1", "status": "processing"})
    )
    with _client() as client:
        data = client.post_multipart(
            "/upload/",
            files={"file": ("a.pdf", b"%PDF-1.4 data", "application/pdf")},
            data={"organization_id": "org1"},
        )
    assert data["id"] == "inv1"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer ftk_test"
    assert b"a.pdf" in req.content
