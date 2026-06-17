"""Environment configuration for the Fintaro MCP server.

The server is configured entirely from environment variables so it can run as a
``uvx`` stdio process under an MCP client. Two invariants are enforced
(validated on the first tool call):

* ``FINTARO_API_KEY`` is required — the server has no anonymous mode.
* ``FINTARO_BASE_URL`` must be ``https://`` — the bearer key must never travel
  over plaintext.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

#: Default gateway base URL. Includes the ``/api/v1`` mount so tool paths are
#: gateway-relative (``/upload/``, ``/invoices/{id}``, ``/api-keys/whoami`` …).
DEFAULT_BASE_URL = "https://api.fintaro.ai/api/v1"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str

    @classmethod
    def from_env(cls) -> "Config":
        api_key = os.environ.get("FINTARO_API_KEY", "").strip()
        if not api_key:
            raise ConfigError(
                "FINTARO_API_KEY is required. Mint a scoped ftk_ key in Fintaro "
                "settings and set it in the MCP client environment."
            )

        base_url = os.environ.get("FINTARO_BASE_URL", "").strip() or DEFAULT_BASE_URL
        if not base_url.startswith("https://"):
            raise ConfigError(
                f"FINTARO_BASE_URL must be an https:// URL, got: {base_url!r}. "
                "The API key must never travel over plaintext."
            )

        return cls(api_key=api_key, base_url=base_url.rstrip("/"))
