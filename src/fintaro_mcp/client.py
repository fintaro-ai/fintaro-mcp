"""Thin synchronous HTTP client over the Fintaro API gateway.

Injects the bearer ``ftk_`` key on every request and maps gateway responses to
two error classes the tool layer can surface cleanly:

* ``401``/``403`` → :class:`AuthError` (the key is missing a scope or is
  invalid/expired) — a scope-aware message so the agent can tell the user which
  permission to grant.
* any other ``4xx``/``5xx`` → :class:`GatewayError`.
"""

from __future__ import annotations

from typing import Any, Mapping

import httpx

_DEFAULT_TIMEOUT = 30.0


class GatewayError(RuntimeError):
    """A non-auth error from the Fintaro gateway (4xx/5xx)."""


class AuthError(GatewayError):
    """A 401/403 from the gateway — the ftk_ key is invalid or lacks a scope."""


class GatewayClient:
    """Synchronous gateway client with bearer auth and error mapping."""

    def __init__(self, base_url: str, api_key: str, *, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def __enter__(self) -> "GatewayClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get(self, path: str, *, params: Mapping[str, Any] | None = None) -> Any:
        resp = self._client.get(path, params=params)
        return self._handle(resp)

    def post_multipart(
        self,
        path: str,
        *,
        files: Mapping[str, Any],
        data: Mapping[str, Any] | None = None,
    ) -> Any:
        resp = self._client.post(path, files=files, data=data)
        return self._handle(resp)

    @staticmethod
    def _handle(resp: httpx.Response) -> Any:
        if resp.status_code in (401, 403):
            raise AuthError(
                f"Authentication failed ({resp.status_code}). The ftk_ key is invalid, "
                "expired, or is missing the required scope for this operation."
            )
        if resp.status_code >= 400:
            raise GatewayError(
                f"Gateway request to {resp.request.url.path} failed "
                f"with status {resp.status_code}."
            )
        if not resp.content:
            return None
        return resp.json()
