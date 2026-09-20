#!/usr/bin/env python3
"""AutoFlow AI - backup operations helper.

A single, dependency-light CLI used by ``backup.sh`` for the parts that are
awkward to do safely in shell:

    s3-upload      upload a *verified* local backup to S3-compatible storage
    s3-verify      verify a remote object (existence, size, sha256)
    write-status   atomically write the machine-readable backup status file
    send-alert     POST a redacted failure alert to a configured webhook

Design rules (required by the Step 2 security review):

* Secrets are NEVER printed. Only env var *names* ever appear in messages.
* The webhook URL is never echoed.
* Every free-text field that leaves this process is passed through
  :func:`redact`, which strips ``scheme://user:pass@`` and
  ``password=``/``token=``/``key=`` style values.
* ``s3-upload`` refuses to overwrite an existing object unless the remote
  content is byte-identical (idempotent retry) or overwrite is explicitly
  enabled.

Exit codes for the S3 subcommands:

    0  success
    1  error (transient/unknown - caller may retry)
    2  conflict (object exists with different content and overwrite disabled -
       NOT retryable, a configuration/design error)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------
_REDACTIONS = (
    # scheme://user:password@host  ->  scheme://***:***@host
    (re.compile(r"(://[^/\s:@]+):([^/\s@]+)@"), r"\1:***@"),
    # password=... / token=... / api_key=... / secret=...
    (
        re.compile(
            r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|"
            r"access[_-]?key|secret[_-]?key)\b\s*([=:])\s*([^\s&,;\"']+)"
        ),
        r"\1\2***",
    ),
)


def redact(value: Any) -> str:
    """Return *value* as a string with credential-like substrings masked."""
    text = "" if value is None else str(value)
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------
def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_text(path: str, text: str) -> None:
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# S3-compatible client
# ---------------------------------------------------------------------------
def _truthy(value: Optional[str]) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _insecure_endpoints_allowed() -> bool:
    """Test/dev escape hatch; never enable in production."""
    return _truthy(os.environ.get("BACKUP_ALLOW_INSECURE_ENDPOINTS", "false"))


def check_secure_url(url: Optional[str], label: str) -> Optional[str]:
    """Return an error message if *url* is not HTTPS, else ``None``.

    Off-host storage and alerting carry credentials in transit, so both must
    use TLS. ``BACKUP_ALLOW_INSECURE_ENDPOINTS=true`` permits plain ``http://``
    for local-only testing and must not be set in production.
    """
    if not url:
        return None
    scheme = urlsplit(url).scheme.lower()
    if scheme == "https":
        return None
    if scheme == "http" and _insecure_endpoints_allowed():
        return None
    if scheme == "http":
        return (
            f"{label} must use an https:// URL "
            "(set BACKUP_ALLOW_INSECURE_ENDPOINTS=true only for local testing)"
        )
    return f"{label} must be a valid https:// URL"


def _build_s3_client(
    endpoint: Optional[str],
    region: Optional[str],
    path_style: str,
):
    """Create a boto3 S3 client. Credentials come from the environment only."""
    import boto3  # imported lazily so tests can stub it
    from botocore.config import Config

    if path_style == "auto":
        addressing = "path" if endpoint else "auto"
    elif _truthy(path_style):
        addressing = "path"
    else:
        addressing = "auto"

    config = Config(s3={"addressing_style": addressing}, retries={"max_attempts": 3})
    kwargs: Dict[str, Any] = {"config": config}
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    if region:
        kwargs["region_name"] = region
    return boto3.client("s3", **kwargs)


def _is_not_found(exc: Exception) -> bool:
    from botocore.exceptions import ClientError

    if not isinstance(exc, ClientError):
        return False
    code = str(exc.response.get("Error", {}).get("Code", ""))
    status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in ("404", "NoSuchKey", "NotFound") or status == 404


def _head_object(s3, bucket: str, key: str):
    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 - narrowed to ClientError below
        if _is_not_found(exc):
            return None
        raise


def cmd_s3_upload(args: argparse.Namespace) -> int:
    path = args.file
    if not os.path.isfile(path):
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1
    size = os.path.getsize(path)
    if size <= 0:
        print("error: refusing to upload a zero-byte file", file=sys.stderr)
        return 1

    endpoint_error = check_secure_url(args.endpoint, "BACKUP_S3_ENDPOINT_URL")
    if endpoint_error:
        print(f"error: {endpoint_error}", file=sys.stderr)
        return 1

    sha = args.sha256 or sha256_file(path)
    s3 = _build_s3_client(args.endpoint, args.region, args.path_style)

    existing = _head_object(s3, args.bucket, args.key)
    if existing is not None:
        remote_sha = (existing.get("Metadata") or {}).get("sha256")
        remote_size = existing.get("ContentLength")
        if remote_sha == sha and remote_size == size:
            print(
                json.dumps(
                    {
                        "status": "already_present",
                        "bucket": args.bucket,
                        "key": args.key,
                        "size": size,
                        "sha256": sha,
                    }
                )
            )
            return 0
        if not args.allow_overwrite:
            print(
                "error: remote object already exists with different content; "
                "refusing to overwrite (set BACKUP_REMOTE_ALLOW_OVERWRITE=true to replace)",
                file=sys.stderr,
            )
            return 2

    s3.put_object(
        Bucket=args.bucket,
        Key=args.key,
        Body=Path(path).read_bytes(),
        ContentType="application/sql",
        Metadata={"sha256": sha, "autoflow-backup": "1"},
    )

    # Verify the remote object after upload.
    head = _head_object(s3, args.bucket, args.key)
    if head is None:
        print("error: uploaded object not found during verification", file=sys.stderr)
        return 1
    remote_sha = (head.get("Metadata") or {}).get("sha256")
    remote_size = head.get("ContentLength")
    if remote_size != size or remote_sha != sha:
        print(
            "error: remote verification mismatch after upload "
            f"(size local={size} remote={remote_size}, sha256 {'match' if remote_sha == sha else 'mismatch'})",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "status": "uploaded",
                "bucket": args.bucket,
                "key": args.key,
                "size": size,
                "sha256": sha,
            }
        )
    )
    return 0


def cmd_s3_verify(args: argparse.Namespace) -> int:
    endpoint_error = check_secure_url(args.endpoint, "BACKUP_S3_ENDPOINT_URL")
    if endpoint_error:
        print(f"error: {endpoint_error}", file=sys.stderr)
        return 1
    s3 = _build_s3_client(args.endpoint, args.region, args.path_style)
    head = _head_object(s3, args.bucket, args.key)
    if head is None:
        print("error: remote object not found", file=sys.stderr)
        return 1
    remote_sha = (head.get("Metadata") or {}).get("sha256")
    remote_size = head.get("ContentLength")

    if args.file:
        if not os.path.isfile(args.file):
            print(f"error: local file missing for comparison: {args.file}", file=sys.stderr)
            return 1
        local_size = os.path.getsize(args.file)
        local_sha = args.sha256 or sha256_file(args.file)
        if local_size != remote_size:
            print(
                f"error: size mismatch (local={local_size} remote={remote_size})",
                file=sys.stderr,
            )
            return 1
        if local_sha != remote_sha:
            print("error: sha256 mismatch between local file and remote object", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "status": "verified",
                    "bucket": args.bucket,
                    "key": args.key,
                    "size": remote_size,
                    "sha256": remote_sha,
                }
            )
        )
        return 0

    print(
        json.dumps(
            {
                "status": "present",
                "bucket": args.bucket,
                "key": args.key,
                "size": remote_size,
                "sha256": remote_sha,
            }
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Status file
# ---------------------------------------------------------------------------
def cmd_write_status(args: argparse.Namespace) -> int:
    payload = {
        "service": "autoflow-backup",
        "timestamp": args.timestamp,
        "status": args.status,
        "stage": args.stage,
        "attempts": args.attempts,
        "duration_seconds": args.duration_seconds,
        "host": args.host,
        "environment": args.environment,
        "backup_target": args.target,
        "file": args.file or None,
        "size_bytes": args.size,
        "sha256": args.sha256,
        "remote": {
            "enabled": _truthy(args.remote_enabled),
            "bucket": args.remote_bucket or None,
            "key": args.remote_key or None,
            "verified": _truthy(args.remote_verified),
        },
        "error": redact(args.error) if args.error else None,
    }
    _atomic_write_text(args.out, json.dumps(payload, indent=2) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Alert webhook
# ---------------------------------------------------------------------------
def build_alert_payload(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "service": "autoflow-backup",
        "status": args.status,
        "timestamp": args.timestamp,
        "host": args.host,
        "environment": args.environment,
        "backup_target": args.target,
        "failure_stage": args.stage,
        "attempts": args.attempts,
        "error_summary": redact(args.error) if args.error else "",
    }


def cmd_send_alert(args: argparse.Namespace) -> int:
    if not args.url:
        print("error: no alert webhook configured", file=sys.stderr)
        return 1
    url_error = check_secure_url(args.url, "BACKUP_ALERT_WEBHOOK_URL")
    if url_error:
        print(f"error: {url_error}", file=sys.stderr)
        return 1
    body = json.dumps(build_alert_payload(args)).encode("utf-8")
    request = urllib.request.Request(
        args.url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "autoflow-backup/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            status = getattr(response, "status", response.getcode())
    except urllib.error.HTTPError as exc:
        print(f"error: alert webhook returned HTTP {exc.code}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - never leak the URL
        print(f"error: alert delivery failed: {redact(exc)}", file=sys.stderr)
        return 1
    if 200 <= int(status) < 300:
        return 0
    print(f"error: alert webhook returned HTTP {status}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _add_s3_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--endpoint", default=os.environ.get("BACKUP_S3_ENDPOINT_URL")
                        or os.environ.get("S3_ENDPOINT_URL") or None)
    parser.add_argument("--region", default=os.environ.get("BACKUP_S3_REGION")
                        or os.environ.get("AWS_REGION") or None)
    parser.add_argument("--path-style", default=os.environ.get("BACKUP_S3_FORCE_PATH_STYLE", "auto"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AutoFlow AI backup operations helper")
    sub = parser.add_subparsers(dest="command", required=True)

    upload = sub.add_parser("s3-upload")
    upload.add_argument("--file", required=True)
    upload.add_argument("--sha256", default=None)
    upload.add_argument("--allow-overwrite", action="store_true")
    _add_s3_options(upload)
    upload.set_defaults(func=cmd_s3_upload)

    verify = sub.add_parser("s3-verify")
    verify.add_argument("--file", default=None)
    verify.add_argument("--sha256", default=None)
    _add_s3_options(verify)
    verify.set_defaults(func=cmd_s3_verify)

    status = sub.add_parser("write-status")
    status.add_argument("--out", required=True)
    status.add_argument("--status", required=True)
    status.add_argument("--timestamp", required=True)
    status.add_argument("--stage", default="")
    status.add_argument("--attempts", default="")
    status.add_argument("--duration-seconds", default="")
    status.add_argument("--host", default="")
    status.add_argument("--environment", default="")
    status.add_argument("--target", default="")
    status.add_argument("--file", default="")
    status.add_argument("--size", default="")
    status.add_argument("--sha256", default="")
    status.add_argument("--remote-enabled", default="false")
    status.add_argument("--remote-bucket", default="")
    status.add_argument("--remote-key", default="")
    status.add_argument("--remote-verified", default="false")
    status.add_argument("--error", default="")
    status.set_defaults(func=cmd_write_status)

    alert = sub.add_parser("send-alert")
    alert.add_argument("--url", default=os.environ.get("BACKUP_ALERT_WEBHOOK_URL", ""))
    alert.add_argument("--status", default="FAILED")
    alert.add_argument("--timestamp", default="")
    alert.add_argument("--stage", default="")
    alert.add_argument("--error", default="")
    alert.add_argument("--host", default="")
    alert.add_argument("--environment", default="")
    alert.add_argument("--target", default="")
    alert.add_argument("--attempts", default="")
    alert.add_argument("--timeout", type=float, default=10.0)
    alert.set_defaults(func=cmd_send_alert)

    return parser


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
