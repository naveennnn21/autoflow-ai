#!/usr/bin/env python3
"""AutoFlow AI - lightweight production smoke test.

Exercises the running stack through the public edge (Caddy) without touching
cloud services. Docker-dependent checks (Redis / Celery / backup) are reported
as BLOCKED when the Docker CLI is unavailable or the containers cannot be
found, so the HTTP checks still run anywhere.

No S3/off-host/webhook validation is performed - Step 3 requires real
infrastructure and is intentionally out of scope here.

Configuration (environment variables):
    SMOKE_BASE      base URL of the edge        (default: https://localhost)
    SMOKE_API       API prefix                  (default: /api/v1)
    SMOKE_INSECURE  "1" to skip TLS verification for the local internal CA
                                                (default: 1)
    SMOKE_RATE_BURST number of burst requests   (default: 135)

Exit code 0 when every non-blocked check passes, 1 otherwise.

Usage:
    python scripts/smoke_test.py
"""
from __future__ import annotations

import json
import os
import random
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from http.client import HTTPConnection, HTTPSConnection

BASE = os.environ.get("SMOKE_BASE", "https://localhost").rstrip("/")
API = os.environ.get("SMOKE_API", "/api/v1")
INSECURE = os.environ.get("SMOKE_INSECURE", "1") == "1"
RATE_BURST = int(os.environ.get("SMOKE_RATE_BURST", "135"))

_USE_TLS = BASE.startswith("https://")
_HOSTPORT = BASE.split("://", 1)[-1].split("/", 1)[0]
if ":" in _HOSTPORT:
    _HOST, _PORT = _HOSTPORT.rsplit(":", 1)
    _PORT = int(_PORT)
else:
    _HOST, _PORT = _HOSTPORT, (443 if _USE_TLS else 80)

_results: list[tuple[str, str, str]] = []  # (name, status, detail)


def report(name: str, status: str, detail: str = "") -> None:
    _results.append((name, status, detail))
    print(f"[{status:7}] {name}" + (f" :: {detail}" if detail else ""))


def _ctx() -> ssl.SSLContext | None:
    if not _USE_TLS:
        return None
    ctx = ssl.create_default_context()
    if INSECURE:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def http(method, path, body=None, token=None, headers=None, timeout=30):
    """Return (status, raw_text, headers_dict)."""
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, context=_ctx(), timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace"), dict(exc.headers)


def docker(*args, timeout=20):
    """Run a docker command; returns (ok, output)."""
    try:
        proc = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False,
        )
        return proc.returncode == 0, (proc.stdout or proc.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False, "docker unavailable"


def find_container(fragment: str):
    ok, out = docker("ps", "--format", "{{.Names}}")
    if not ok:
        return None
    for name in out.splitlines():
        if fragment in name:
            return name.strip()
    return None


def check_http_basics():
    status, _, headers = http("GET", "/")
    report("HTTPS availability (GET /)", "PASS" if status == 200 else "FAIL", f"status={status}")
    if status == 200:
        hsts = headers.get("Strict-Transport-Security")
        report("HSTS header present on edge response", "PASS" if hsts else "WARN", str(hsts or ""))

    status, body, _ = http("GET", "/health")
    ok = status == 200 and json.loads(body or "{}").get("status") == "healthy"
    report("Liveness /health", "PASS" if ok else "FAIL", f"status={status}")

    status, body, _ = http("GET", "/readiness")
    payload = json.loads(body or "{}")
    ok = status == 200 and payload.get("status") == "healthy" and payload.get("database") == "connected"
    report("Readiness /readiness (database)", "PASS" if ok else "FAIL", f"status={status} body={payload}")


def check_auth_boundary_and_api():
    status, _, _ = http("GET", f"{API}/workflow")
    report("Auth boundary: unauthenticated API -> 401", "PASS" if status == 401 else "FAIL", f"status={status}")

    email = f"smoke-{random.randint(100000, 999999)}@example.invalid"
    status, body, _ = http("POST", f"{API}/auth/register",
                           {"email": email, "password": "SmokePass123!", "full_name": "Smoke Test"})
    token = ""
    if status == 201:
        token = (json.loads(body).get("access_token") or "")
    report("Register smoke user", "PASS" if status == 201 and token else "FAIL", f"status={status}")
    if not token:
        return None
    status, _, _ = http("GET", f"{API}/workflow", token=token)
    report("Authenticated API request -> 200", "PASS" if status == 200 else "FAIL", f"status={status}")
    return token


def check_frontend():
    status, body, headers = http("GET", "/login")
    ctype = headers.get("Content-Type", "")
    ok = status == 200 and "html" in ctype.lower()
    report("Frontend availability (GET /login)", "PASS" if ok else "FAIL", f"status={status} ctype={ctype}")


def check_sse(token: str):
    conn = HTTPSConnection(_HOST, _PORT, timeout=60, context=_ctx()) if _USE_TLS else \
        HTTPConnection(_HOST, _PORT, timeout=60)
    try:
        conn.request(
            "POST", f"{API}/planner/chat/stream",
            body=json.dumps({"message": "Create a workflow that posts to Slack"}),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}",
                     "Accept": "text/event-stream"},
        )
        resp = conn.getresponse()
        ctype = resp.getheader("content-type", "")
        chunks, frames = b"", 0
        while True:
            chunk = resp.read(256)
            if not chunk:
                break
            chunks += chunk
            frames = chunks.count(b"\n\n")
            if frames >= 2:
                break
        ok = resp.status == 200 and "text/event-stream" in ctype and frames >= 1
        report("SSE streaming (planner/chat/stream)",
               "PASS" if ok else "FAIL", f"status={resp.status} ctype={ctype} frames={frames}")
    finally:
        conn.close()


def check_rate_limit():
    codes: dict[int, int] = {}
    for _ in range(RATE_BURST):
        status, _, _ = http("GET", f"{API}/workflow")
        codes[status] = codes.get(status, 0) + 1
    ok = 429 in codes
    report("Rate limiting enforced (429 under burst)", "PASS" if ok else "FAIL",
           f"histogram={dict(sorted(codes.items()))}")


def check_docker_services():
    redis = find_container("redis")
    if redis:
        ok, out = docker("exec", redis, "redis-cli", "ping")
        # A configured password yields NOAUTH - which proves Redis is reachable.
        reachable = ok and ("NOAUTH" in out or "PONG" in out)
        report("Redis connectivity", "PASS" if reachable else "FAIL", out or "no output")
    else:
        report("Redis connectivity", "BLOCKED", "docker/redis container unavailable")

    worker = find_container("celery")
    if worker:
        ok, out = docker("exec", worker, "celery", "-A", "app.tasks", "inspect", "ping", "--timeout", "10")
        report("Celery health", "PASS" if ok and "pong" in out.lower() else "FAIL",
               (out.splitlines() or [""])[-1][:80])
    else:
        report("Celery health", "BLOCKED", "docker/celery container unavailable")

    backup = find_container("backup")
    if backup:
        ok, _ = docker("exec", backup, "test", "-f", "/backups/.scheduler_heartbeat")
        report("Backup scheduler heartbeat", "PASS" if ok else "FAIL",
               "local backup only - off-host upload is Step 3")
    else:
        report("Backup scheduler heartbeat", "BLOCKED", "docker/backup container unavailable")


def main() -> int:
    print(f"AutoFlow smoke test -> {BASE}{API}  (tls={'on' if _USE_TLS else 'off'})\n")
    check_http_basics()
    token = check_auth_boundary_and_api()
    check_frontend()
    if token:
        check_sse(token)
    check_rate_limit()
    check_docker_services()

    failed = [r for r in _results if r[1] == "FAIL"]
    blocked = [r for r in _results if r[1] == "BLOCKED"]
    print("\n=== SUMMARY ===")
    print(f"passed={sum(1 for r in _results if r[1] == 'PASS')} "
          f"failed={len(failed)} blocked={len(blocked)}")
    for name, status, detail in _results:
        if status != "PASS":
            print(f"  {status}: {name} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
