"""B1 — env config: require API key, enforce https base URL."""

from __future__ import annotations

import pytest

from fintaro_mcp.config import Config, ConfigError


def test_from_env_reads_key_and_base_url(monkeypatch):
    monkeypatch.setenv("FINTARO_API_KEY", "ftk_test")
    monkeypatch.setenv("FINTARO_BASE_URL", "https://api.fintaro.ai")
    cfg = Config.from_env()
    assert cfg.api_key == "ftk_test"
    assert cfg.base_url == "https://api.fintaro.ai"


def test_from_env_requires_api_key(monkeypatch):
    monkeypatch.delenv("FINTARO_API_KEY", raising=False)
    monkeypatch.setenv("FINTARO_BASE_URL", "https://api.fintaro.ai")
    with pytest.raises(ConfigError):
        Config.from_env()


def test_from_env_rejects_non_https_base_url(monkeypatch):
    monkeypatch.setenv("FINTARO_API_KEY", "ftk_test")
    monkeypatch.setenv("FINTARO_BASE_URL", "http://api.fintaro.ai")
    with pytest.raises(ConfigError):
        Config.from_env()


def test_from_env_default_base_url_is_https(monkeypatch):
    monkeypatch.setenv("FINTARO_API_KEY", "ftk_test")
    monkeypatch.delenv("FINTARO_BASE_URL", raising=False)
    cfg = Config.from_env()
    assert cfg.base_url.startswith("https://")
