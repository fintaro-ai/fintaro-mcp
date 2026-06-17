"""B6 — monatsabschluss_check prompt text."""

from __future__ import annotations

from fintaro_mcp import server


def test_prompt_text_mentions_unmatched_or_fehlt():
    text = server.monatsabschluss_check_text()
    lowered = text.lower()
    assert "unmatched" in lowered or "fehlt" in lowered


def test_prompt_text_does_not_reference_dropped_exports_tool():
    text = server.monatsabschluss_check_text()
    assert "list_exports" not in text
    assert "get_export" not in text
