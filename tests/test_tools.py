"""B4 — whoami + upload_invoice impls against a fake client."""

from __future__ import annotations

from pathlib import Path

import pytest
from fintaro_mcp import server


class FakeClient:
    """Records calls; returns canned gateway responses."""

    def __init__(self, get_result=None, post_result=None):
        self._get_result = get_result
        self._post_result = post_result or {"id": "inv1", "status": "processing"}
        self.get_calls: list[tuple] = []
        self.post_calls: list[dict] = []

    def get(self, path, *, params=None):
        self.get_calls.append((path, params))
        return self._get_result

    def post_multipart(self, path, *, files, data=None):
        self.post_calls.append({"path": path, "files": files, "data": data})
        return self._post_result


def test_whoami_calls_api_keys_whoami_without_org_param():
    client = FakeClient(get_result={"organization_id": "org1", "scopes": ["invoices:read"], "expires_at": None})
    result = server.whoami_impl(client)
    assert client.get_calls == [("/api-keys/whoami", None)]
    assert result["organization_id"] == "org1"


def test_upload_invoice_sends_multipart_with_org_and_returns_processing(tmp_path: Path):
    f = tmp_path / "receipt.pdf"
    f.write_bytes(b"%PDF-1.4 minimal")
    client = FakeClient(post_result={"id": "inv9", "status": "processing", "deduplicated": False})
    result = server.upload_invoice_impl(client, "org1", str(f))
    assert result["invoice_id"] == "inv9"
    assert result["status"] == "processing"
    assert result["deduplicated"] is False
    call = client.post_calls[0]
    assert call["path"] == "/upload/"
    assert call["data"]["organization_id"] == "org1"
    assert "file" in call["files"]


def test_upload_invoice_rejects_bad_extension(tmp_path: Path):
    f = tmp_path / "malware.exe"
    f.write_bytes(b"MZ")
    client = FakeClient()
    with pytest.raises(ValueError):
        server.upload_invoice_impl(client, "org1", str(f))
    assert client.post_calls == []


def test_upload_invoice_rejects_oversize(tmp_path: Path):
    f = tmp_path / "big.pdf"
    f.write_bytes(b"x" * (26 * 1024 * 1024))
    client = FakeClient()
    with pytest.raises(ValueError):
        server.upload_invoice_impl(client, "org1", str(f))
    assert client.post_calls == []


def test_upload_invoice_rejects_empty_file(tmp_path: Path):
    f = tmp_path / "empty.pdf"
    f.write_bytes(b"")
    client = FakeClient()
    with pytest.raises(ValueError):
        server.upload_invoice_impl(client, "org1", str(f))
    assert client.post_calls == []


def test_upload_invoice_rejects_missing_file(tmp_path: Path):
    client = FakeClient()
    with pytest.raises(ValueError):
        server.upload_invoice_impl(client, "org1", str(tmp_path / "nope.pdf"))
    assert client.post_calls == []


def test_upload_invoice_accepts_png_jpeg_webp(tmp_path: Path):
    client = FakeClient(post_result={"id": "x", "status": "processing", "deduplicated": False})
    for ext in ("png", "jpg", "jpeg", "webp"):
        f = tmp_path / f"img.{ext}"
        f.write_bytes(b"data")
        result = server.upload_invoice_impl(client, "org1", str(f))
        assert result["status"] == "processing"


# --- Gap 1: positive accept-path per allowed type with real magic bytes ----- #
# Realistic leading bytes so the test exercises a true "valid file of this type"
# path, not just an arbitrary extension. The client-side guard keys off the
# extension allowlist, so each must reach the multipart POST and come back
# {invoice_id, status: "processing"}.
_MAGIC_BYTES = {
    "pdf": b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n",
    "png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
    "jpg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01",
    "jpeg": b"\xff\xd8\xff\xe1\x00\x10Exif\x00\x00",
    "webp": b"RIFF\x24\x00\x00\x00WEBPVP8 ",
}


@pytest.mark.parametrize("ext", ["pdf", "png", "jpg", "jpeg", "webp"])
def test_upload_invoice_accepts_each_allowed_type_and_posts_multipart(ext, tmp_path: Path):
    f = tmp_path / f"receipt.{ext}"
    f.write_bytes(_MAGIC_BYTES[ext])
    client = FakeClient(post_result={"id": f"inv-{ext}", "status": "processing", "deduplicated": False})

    result = server.upload_invoice_impl(client, "org-acc", str(f))

    # The multipart POST is actually sent for this accepted type.
    assert len(client.post_calls) == 1
    call = client.post_calls[0]
    assert call["path"] == "/upload/"
    assert call["data"]["organization_id"] == "org-acc"
    fname, content, _ctype = call["files"]["file"]
    assert fname == f"receipt.{ext}"
    assert content == _MAGIC_BYTES[ext]
    # Normalized return contract.
    assert result == {"invoice_id": f"inv-{ext}", "status": "processing", "deduplicated": False}


def test_upload_invoice_oversize_raises_valueerror_before_post(tmp_path: Path):
    f = tmp_path / "huge.pdf"
    # One byte over the 25 MB cap.
    f.write_bytes(b"%PDF-1.4" + b"\x00" * (server._MAX_UPLOAD_BYTES + 1 - 8))
    client = FakeClient()
    with pytest.raises(ValueError, match="maximum upload size"):
        server.upload_invoice_impl(client, "org1", str(f))
    assert client.post_calls == []


def test_upload_invoice_empty_raises_valueerror_before_post(tmp_path: Path):
    f = tmp_path / "empty.png"
    f.write_bytes(b"")
    client = FakeClient()
    with pytest.raises(ValueError, match="empty"):
        server.upload_invoice_impl(client, "org1", str(f))
    assert client.post_calls == []
