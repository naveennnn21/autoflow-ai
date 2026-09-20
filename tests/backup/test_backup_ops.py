"""Unit tests for infra/docker/backup_ops.py.

These use a stub S3 client and a real local HTTP server for webhook delivery,
so they exercise the real code paths without requiring cloud credentials.
Live S3 validation against MinIO is performed separately (see
docs/BACKUP_STEP2_VALIDATION_REPORT.md).
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

DOCKER_DIR = Path(__file__).resolve().parents[2] / "infra" / "docker"
sys.path.insert(0, str(DOCKER_DIR))

import backup_ops  # noqa: E402


# ---------------------------------------------------------------------------
# Stub S3
# ---------------------------------------------------------------------------
class _NotFound(Exception):
    pass


class FakeS3:
    def __init__(self):
        self.objects = {}

    def head_object(self, Bucket, Key):  # noqa: N803 - boto3 signature
        if Key not in self.objects:
            raise _NotFound()
        obj = self.objects[Key]
        return {"ContentLength": obj["size"], "Metadata": obj["metadata"]}

    def put_object(self, Bucket, Key, Body, ContentType=None, Metadata=None):  # noqa: N803
        self.objects[Key] = {"size": len(Body), "metadata": Metadata or {}}


@pytest.fixture
def fake_s3(monkeypatch):
    client = FakeS3()
    monkeypatch.setattr(backup_ops, "_build_s3_client", lambda *a, **k: client)
    monkeypatch.setattr(backup_ops, "_is_not_found", lambda exc: isinstance(exc, _NotFound))
    return client


def _write(path: Path, text: str = "x") -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Redaction / hashing
# ---------------------------------------------------------------------------
def test_redact_masks_credentials():
    text = "connect postgresql://autoflow:supersecret@db:5432/autoflow failed; password=hunter2 token=abc123"
    out = backup_ops.redact(text)
    assert "supersecret" not in out
    assert "hunter2" not in out
    assert "abc123" not in out
    assert "autoflow:***@db" in out


def test_sha256_file_matches_hashlib(tmp_path):
    import hashlib

    data = b"postgresql dump payload"
    path = tmp_path / "x.sql"
    path.write_bytes(data)
    assert backup_ops.sha256_file(str(path)) == hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# S3 upload / verify
# ---------------------------------------------------------------------------
def test_s3_upload_success(tmp_path, fake_s3, capsys):
    path = _write(tmp_path / "backup.sql", "-- PostgreSQL database dump\n")
    rc = backup_ops.main(["s3-upload", "--file", str(path), "--bucket", "b", "--key", "k"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "uploaded"
    assert out["key"] == "k"
    assert "k" in fake_s3.objects


def test_s3_upload_zero_byte_refused(tmp_path, fake_s3):
    path = tmp_path / "empty.sql"
    path.write_text("", encoding="utf-8")
    rc = backup_ops.main(["s3-upload", "--file", str(path), "--bucket", "b", "--key", "k"])
    assert rc == 1
    assert not fake_s3.objects


def test_s3_upload_idempotent_when_identical(tmp_path, fake_s3, capsys):
    path = _write(tmp_path / "backup.sql", "data")
    backup_ops.main(["s3-upload", "--file", str(path), "--bucket", "b", "--key", "k"])
    capsys.readouterr()
    rc = backup_ops.main(["s3-upload", "--file", str(path), "--bucket", "b", "--key", "k"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "already_present"


def test_s3_upload_conflict_refused(tmp_path, fake_s3, capsys):
    fake_s3.objects["k"] = {"size": 3, "metadata": {"sha256": "deadbeef"}}
    path = _write(tmp_path / "backup.sql", "different content")
    rc = backup_ops.main(["s3-upload", "--file", str(path), "--bucket", "b", "--key", "k"])
    assert rc == 2  # non-retryable conflict
    assert fake_s3.objects["k"]["metadata"]["sha256"] == "deadbeef"


def test_s3_upload_overwrite_allowed(tmp_path, fake_s3):
    fake_s3.objects["k"] = {"size": 3, "metadata": {"sha256": "deadbeef"}}
    path = _write(tmp_path / "backup.sql", "new content")
    rc = backup_ops.main(
        ["s3-upload", "--file", str(path), "--bucket", "b", "--key", "k", "--allow-overwrite"]
    )
    assert rc == 0
    assert fake_s3.objects["k"]["metadata"]["sha256"] == backup_ops.sha256_file(str(path))


def test_s3_verify_detects_size_mismatch(tmp_path, fake_s3):
    path = _write(tmp_path / "backup.sql", "local-data")
    fake_s3.objects["k"] = {"size": 999, "metadata": {"sha256": "x"}}
    rc = backup_ops.main(["s3-verify", "--file", str(path), "--bucket", "b", "--key", "k"])
    assert rc == 1


def test_s3_verify_missing_object(tmp_path, fake_s3):
    path = _write(tmp_path / "backup.sql", "local-data")
    rc = backup_ops.main(["s3-verify", "--file", str(path), "--bucket", "b", "--key", "k"])
    assert rc == 1


def test_s3_verify_matches(tmp_path, fake_s3):
    path = _write(tmp_path / "backup.sql", "local-data")
    fake_s3.objects["k"] = {
        "size": path.stat().st_size,
        "metadata": {"sha256": backup_ops.sha256_file(str(path))},
    }
    rc = backup_ops.main(["s3-verify", "--file", str(path), "--bucket", "b", "--key", "k"])
    assert rc == 0


# ---------------------------------------------------------------------------
# Status file
# ---------------------------------------------------------------------------
def test_write_status_atomic_and_redacted(tmp_path):
    out = tmp_path / "status.json"
    rc = backup_ops.main([
        "write-status", "--out", str(out), "--status", "FAILED",
        "--timestamp", "2026-09-20T00:00:00+0000", "--stage", "pg_dump",
        "--attempts", "3", "--target", "autoflow@postgres:5432",
        "--error", "auth failed for postgresql://user:leakedpw@db/autoflow",
    ])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "FAILED"
    assert payload["stage"] == "pg_dump"
    assert "leakedpw" not in json.dumps(payload)


# ---------------------------------------------------------------------------
# Alert webhook (real local HTTP server)
# ---------------------------------------------------------------------------
class _CaptureHandler(BaseHTTPRequestHandler):
    received = []
    status_code = 200

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        type(self).received.append(json.loads(body))
        self.send_response(type(self).status_code)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # silence test output
        return


@pytest.fixture
def alert_server():
    _CaptureHandler.received = []
    _CaptureHandler.status_code = 200
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/hook"
    try:
        yield url
    finally:
        server.shutdown()


def test_send_alert_delivers_and_redacts(alert_server, capsys):
    rc = backup_ops.main([
        "send-alert", "--url", alert_server, "--status", "FAILED",
        "--timestamp", "2026-09-20T00:00:00+0000", "--stage", "remote_upload",
        "--error", "upload failed for postgresql://user:topsecret@db/autoflow",
        "--host", "backup-1", "--environment", "production",
        "--target", "autoflow@postgres:5432", "--attempts", "3",
    ])
    assert rc == 0
    assert len(_CaptureHandler.received) == 1
    payload = _CaptureHandler.received[0]
    assert payload["status"] == "FAILED"
    assert payload["failure_stage"] == "remote_upload"
    assert "topsecret" not in json.dumps(payload)
    assert payload["attempts"] == "3"


def test_send_alert_http_error_returns_nonzero(alert_server):
    _CaptureHandler.status_code = 500
    rc = backup_ops.main([
        "send-alert", "--url", alert_server, "--status", "FAILED",
        "--error", "boom",
    ])
    assert rc == 1
    assert len(_CaptureHandler.received) == 1


def test_send_alert_missing_url_returns_nonzero(monkeypatch):
    monkeypatch.delenv("BACKUP_ALERT_WEBHOOK_URL", raising=False)
    rc = backup_ops.main(["send-alert", "--status", "FAILED", "--error", "x"])
    assert rc == 1
