"""Integration tests for infra/docker/backup.sh orchestration.

PostgreSQL itself is not required: ``pg_dump`` and ``pg_isready`` are replaced
by deterministic stubs on PATH so every stage (connectivity, dump, integrity,
atomic publish, retention, retry, failure recording) can be exercised. The
real PostgreSQL path is validated live in the Step 2 report.
"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_SH = REPO_ROOT / "infra" / "docker" / "backup.sh"

BASH = shutil.which("bash") or shutil.which("sh")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not available")


def _make_stub(bindir: Path, name: str, body: str) -> None:
    path = bindir / name
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def stub_env(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _make_stub(bindir, "pg_isready", '#!/usr/bin/env bash\n[ "${FAKE_PG_ISREADY:-0}" = "1" ] && exit 1\nexit 0\n')
    _make_stub(bindir, "pg_dump", r"""#!/usr/bin/env bash
set -u
case "${FAKE_MODE:-ok}" in
  fail)  echo "pg_dump: error: connection to server failed" >&2; exit 1 ;;
  empty) exit 0 ;;
  invalid) printf '%s\n' '-- not a real dump' ; exit 0 ;;
  ddl) printf '%s\n' 'DROP DATABASE IF EXISTS autoflow;' 'CREATE DATABASE autoflow;' ; exit 0 ;;
  ok) printf '%s\n' '--' '-- PostgreSQL database dump' '--' '-- Dumped by pg_dump version 16' \
        'SELECT 1;' 'CREATE TABLE public.t (id integer);' 'CREATE INDEX ix_t ON public.t (id);' \
        '-- PostgreSQL database dump complete' '--' ; exit 0 ;;
esac
""")

    backup_dir = tmp_path / "backups"

    def run(fake_mode="ok", extra_env=None, attempts="1"):
        env = dict(os.environ)
        env.update({
            "PATH": f"{bindir}{os.pathsep}{env.get('PATH', '')}",
            "POSTGRES_USER": "autoflow",
            "POSTGRES_PASSWORD": "test-password",
            "POSTGRES_DB": "autoflow",
            "BACKUP_PG_MODE": "direct",
            "BACKUP_DIR": str(backup_dir),
            "BACKUP_RETRY_ATTEMPTS": attempts,
            "BACKUP_RETRY_DELAY_SECONDS": "0",
            "BACKUP_REMOTE_ENABLED": "false",
            "BACKUP_ALERT_ENABLED": "false",
            "FAKE_MODE": fake_mode,
        })
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [BASH, str(BACKUP_SH)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    return {"run": run, "backup_dir": backup_dir}


def _backups(backup_dir: Path):
    return sorted(backup_dir.glob("backup_*.sql")) if backup_dir.exists() else []


def test_successful_local_backup(stub_env):
    result = stub_env["run"]()
    assert result.returncode == 0, result.stderr
    files = _backups(stub_env["backup_dir"])
    assert len(files) == 1
    assert files[0].stat().st_size > 0
    assert not (stub_env["backup_dir"] / ".backup.lock").exists()


def test_pg_dump_failure_leaves_no_artifact(stub_env):
    result = stub_env["run"](fake_mode="fail")
    assert result.returncode == 1
    assert _backups(stub_env["backup_dir"]) == []
    assert (stub_env["backup_dir"] / ".backup_failed.log").exists()


def test_empty_dump_rejected(stub_env):
    result = stub_env["run"](fake_mode="empty")
    assert result.returncode == 1
    assert _backups(stub_env["backup_dir"]) == []


def test_invalid_dump_rejected(stub_env):
    result = stub_env["run"](fake_mode="invalid")
    assert result.returncode == 1
    assert _backups(stub_env["backup_dir"]) == []


def test_database_level_ddl_rejected(stub_env):
    result = stub_env["run"](fake_mode="ddl")
    assert result.returncode == 1
    assert _backups(stub_env["backup_dir"]) == []


def test_postgres_unavailable_fails_without_artifact(stub_env):
    result = stub_env["run"](extra_env={"FAKE_PG_ISREADY": "1"})
    assert result.returncode == 1
    assert _backups(stub_env["backup_dir"]) == []


def test_retry_attempts_are_bounded(stub_env):
    result = stub_env["run"](fake_mode="fail", attempts="3")
    assert result.returncode == 1
    assert result.stdout.count("Backup attempt") == 3
    assert "FAILED after 3 attempt" in result.stderr


def test_status_file_written_on_success(stub_env):
    import json

    result = stub_env["run"]()
    assert result.returncode == 0
    status = json.loads((stub_env["backup_dir"] / ".last_backup_status.json").read_text())
    assert status["status"] == "SUCCESS"
    assert status["file"].startswith("backup_")


def _kill_zero_supported() -> bool:
    """MSYS/Git Bash cannot signal native Windows PIDs, so lock-owner liveness
    is only meaningful on a POSIX host. Skip there rather than assert wrongly."""
    probe = subprocess.run(
        [BASH, "-c", f"kill -0 {os.getpid()} 2>/dev/null && echo yes || echo no"],
        capture_output=True, text=True, timeout=30,
    )
    return probe.stdout.strip() == "yes"


def test_overlap_protection_skips_second_run(stub_env):
    if not _kill_zero_supported():
        pytest.skip("bash cannot signal host PIDs here; covered by live scheduler validation")
    backup_dir = stub_env["backup_dir"]
    backup_dir.mkdir(parents=True, exist_ok=True)
    lock = backup_dir / ".backup.lock"
    lock.mkdir()
    (lock / "pid").write_text(str(os.getpid()))  # a live owner
    result = stub_env["run"]()
    assert result.returncode == 0
    assert "skipping this run" in result.stdout
    assert _backups(backup_dir) == []


def test_stale_lock_is_reclaimed(stub_env):
    """A lock owned by a dead PID must not block backups forever."""
    backup_dir = stub_env["backup_dir"]
    backup_dir.mkdir(parents=True, exist_ok=True)
    lock = backup_dir / ".backup.lock"
    lock.mkdir()
    (lock / "pid").write_text("999999")
    result = stub_env["run"]()
    assert result.returncode == 0
    assert len(_backups(backup_dir)) == 1
