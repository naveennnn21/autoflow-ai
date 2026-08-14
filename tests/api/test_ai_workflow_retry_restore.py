"""AutoFlow AI - Retry + version restore integration tests.

These run the real ASGI app against a real PostgreSQL instance (the same
gate as the generated tests/api suite: skipped when PostgreSQL is down).
They exercise the runtime-backed retry and immutable version restore with
real org scoping - no mocks.
"""

import asyncio
import time
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


def _pg_available() -> bool:
    import socket
    from urllib.parse import urlparse

    from app.core.config import settings

    parts = urlparse(settings.database_url)
    host = parts.hostname or "localhost"
    port = parts.port or 5432
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not _pg_available(),
        reason="requires PostgreSQL to run AI workflow integration tests",
    ),
]


# The auth-free green path (webhook trigger + REST post) compiles, deploys,
# and completes without credentials.
GREEN_DEF = {
    "name": "Green WF",
    "nodes": [
        {"id": "n1", "kind": "trigger", "connector": "webhook",
         "action": "", "label": "Webhook", "config": {}},
        {"id": "n2", "kind": "action", "connector": "rest",
         "action": "post", "label": "Post to REST",
         "config": {"url": "https://example.com"}},
    ],
    "edges": [{"source": "n1", "target": "n2"}],
}

# Slack requires OAuth2 credentials: deploys with a warning, execution then
# fails with a needs_oauth2 error - a deterministic retryable failure.
FAIL_DEF = {
    "name": "Fail WF",
    "nodes": [
        {"id": "n1", "kind": "trigger", "connector": "webhook",
         "action": "", "label": "Webhook", "config": {}},
        {"id": "n2", "kind": "action", "connector": "slack",
         "action": "send_message", "label": "Slack", "config": {}},
    ],
    "edges": [{"source": "n1", "target": "n2"}],
}

V2_DEF = {
    "name": "Green WF v2",
    "nodes": [
        {"id": "t1", "kind": "trigger", "connector": "webhook",
         "action": "", "label": "Webhook", "config": {}},
        {"id": "a2", "kind": "action", "connector": "rest",
         "action": "post", "label": "Post to REST (v2)",
         "config": {"url": "https://example.com/v2"}},
    ],
    "edges": [{"source": "t1", "target": "a2"}],
}


class Client:
    """Real-tenant wrapper over the ASGI app.

    Registers a fresh user + personal org through the real auth endpoint so
    the workflows/executions FK constraints (organization_id NOT NULL) are
    satisfied by actual rows - mirroring the product flow.
    """

    def __init__(self):
        self.headers = {}
        self.org = ""

    async def __aenter__(self):
        email = f"rr.{uuid.uuid4().hex[:12]}@autoflow.test"
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://test") as reg:
            resp = await reg.post("/api/v1/auth/register", json={
                "email": email,
                "password": "e2e-pass-12345",
                "full_name": "Retry Restore",
            })
            assert resp.status_code in (200, 201), resp.text
            data = resp.json()
        self.org = str((data.get("org") or {}).get("id")
                       or data.get("org_id")
                       or uuid.uuid4())
        user_id = str((data.get("user") or {}).get("id") or uuid.uuid4())
        self.headers = {"X-User-Id": user_id, "X-Org-Id": self.org}
        self._client = AsyncClient(transport=ASGITransport(app=app),
                                   base_url="http://test")
        return self

    async def __aexit__(self, *exc):
        await self._client.aclose()

    async def post(self, path, body):
        resp = await self._client.post(f"/api/v1{path}", json=body,
                                       headers=self.headers)
        return resp.status_code, (resp.json() if resp.content else None)

    async def get(self, path):
        resp = await self._client.get(f"/api/v1{path}", headers=self.headers)
        return resp.status_code, (resp.json() if resp.content else None)


async def _deploy(client: Client, definition: dict, workflow_id=None):
    st, res = await client.post("/ai_workflow/deploy", {
        "definition": definition,
        "workflow_id": workflow_id,
    })
    assert st == 200 and res and res.get("ok") is True, res
    return res


async def _execute(client: Client, workflow_id: str, definition: dict,
                   pacing: int = 120):
    st, res = await client.post("/ai_workflow/execute", {
        "workflow_id": workflow_id,
        "definition": definition,
        "node_pacing_ms": pacing,
    })
    assert st == 200, res
    return res["execution_id"]


async def _wait_db_status(execution_id: str, statuses: set,
                          timeout: float = 12.0):
    """Poll the persisted execution record until it reaches a status."""
    from app.core.database import async_session_factory
    from app.repositories.execution import ExecutionRepository

    deadline = time.time() + timeout
    while time.time() < deadline:
        async with async_session_factory() as session:
            rec = await ExecutionRepository(session).get(execution_id)
            if rec and rec.status and str(rec.status.value) in statuses:
                return rec
        await asyncio.sleep(0.1)
    raise AssertionError(
        f"execution {execution_id} not in {statuses} within {timeout}s")


async def _execution_count(workflow_id: str, org: str) -> int:
    from sqlalchemy import func, select

    from app.core.database import async_session_factory
    from app.models.execution import Execution

    async with async_session_factory() as session:
        stmt = select(func.count(Execution.id)).where(
            Execution.workflow_id == workflow_id,
            Execution.organization_id == org,
        )
        return (await session.execute(stmt)).scalar_one()


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------

async def test_retry_failed_execution_creates_new_attempt():
    async with Client() as c:
        dep = await _deploy(c, FAIL_DEF)
        wid = dep["workflow_id"]
        eid = await _execute(c, wid, FAIL_DEF)
        await _wait_db_status(eid, {"failed"})

        st, res = await c.post(f"/ai_workflow/executions/{eid}/retry", {})
        assert st == 200, res
        assert res["retry_of"] == eid
        assert res["status"] == "running"
        new_id = res["execution_id"]
        assert new_id != eid

        # The retry is a real runtime run that fails deterministically again.
        rec = await _wait_db_status(new_id, {"failed"})
        assert rec.retry_attempt == 1
        # Execution history now holds both attempts.
        assert await _execution_count(wid, c.org) == 2


async def test_retry_via_control_action():
    async with Client() as c:
        dep = await _deploy(c, FAIL_DEF)
        eid = await _execute(c, dep["workflow_id"], FAIL_DEF)
        await _wait_db_status(eid, {"failed"})
        st, res = await c.post(
            f"/ai_workflow/executions/{eid}/control", {"action": "retry"})
        assert st == 200, res
        assert res["action"] == "retry"
        assert res["retry_of"] == eid
        assert res["execution_id"] != eid


async def test_retry_via_control_works_after_run_trimmed():
    """Retry via the control endpoint must work off the persisted record
    even when the in-memory run registry has already dropped the run
    (registry is capped and trimmed) - regression for the gate that used to
    404 retries once a run left ``_RUNS``."""
    async with Client() as c:
        dep = await _deploy(c, FAIL_DEF)
        eid = await _execute(c, dep["workflow_id"], FAIL_DEF)
        await _wait_db_status(eid, {"failed"})

        # Simulate the run having been trimmed from the in-memory registry.
        from app.services.ai_runtime import _RUNS
        _RUNS.pop(eid, None)

        st, res = await c.post(
            f"/ai_workflow/executions/{eid}/control", {"action": "retry"})
        assert st == 200, res
        assert res["action"] == "retry"
        assert res["retry_of"] == eid
        assert res["execution_id"] != eid
        assert res["status"] == "running"


async def test_retry_completed_execution_rejected():
    async with Client() as c:
        dep = await _deploy(c, GREEN_DEF)
        eid = await _execute(c, dep["workflow_id"], GREEN_DEF)
        await _wait_db_status(eid, {"completed"})
        st, res = await c.post(f"/ai_workflow/executions/{eid}/retry", {})
        assert st == 409, (st, res)
        assert res["detail"]["code"] == "EXECUTION_NOT_RETRYABLE"


async def test_retry_running_execution_rejected():
    async with Client() as c:
        dep = await _deploy(c, FAIL_DEF)
        eid = await _execute(c, dep["workflow_id"], FAIL_DEF, pacing=600)
        # Immediately retry while the run is in flight.
        st, res = await c.post(f"/ai_workflow/executions/{eid}/retry", {})
        assert st == 409, (st, res)
        assert res["detail"]["code"] == "EXECUTION_NOT_RETRYABLE"
        await _wait_db_status(eid, {"failed"})


async def test_retry_missing_execution_404():
    async with Client() as c:
        st, res = await c.post(
            f"/ai_workflow/executions/{uuid.uuid4()}/retry", {})
        assert st == 404


async def test_retry_cross_tenant_404():
    async with Client() as c1, Client() as c2:
        dep = await _deploy(c1, FAIL_DEF)
        eid = await _execute(c1, dep["workflow_id"], FAIL_DEF)
        await _wait_db_status(eid, {"failed"})
        st, res = await c2.post(f"/ai_workflow/executions/{eid}/retry", {})
        assert st == 404  # no information leakage


async def test_retry_preserves_workflow_version():
    async with Client() as c:
        dep1 = await _deploy(c, FAIL_DEF)                # v1
        eid = await _execute(c, dep1["workflow_id"], FAIL_DEF)
        await _wait_db_status(eid, {"failed"})
        await _deploy(c, V2_DEF, dep1["workflow_id"])    # v2 (workflow changed)

        st, res = await c.post(f"/ai_workflow/executions/{eid}/retry", {})
        assert st == 200, res
        assert res["version"] == 1  # retried at the ORIGINAL version
        await _wait_db_status(res["execution_id"], {"failed"})


# ---------------------------------------------------------------------------
# Version restore
# ---------------------------------------------------------------------------

async def test_restore_creates_new_version_history_immutable():
    async with Client() as c:
        dep1 = await _deploy(c, GREEN_DEF)               # v1
        wid = dep1["workflow_id"]
        await _deploy(c, V2_DEF, wid)                    # v2

        st, res = await c.post(
            f"/ai_workflow/workflows/{wid}/versions/1/restore", {})
        assert st == 200, res
        assert res["restored_from_version"] == 1
        assert res["new_version_number"] == 3

        st, versions = await c.get(f"/ai_workflow/workflows/{wid}/versions")
        assert st == 200
        numbers = [int(v["version"]) for v in versions["versions"]]
        assert numbers == [1, 2, 3]
        assert versions["current_version"] == 3

        # The new version carries the v1 definition, unchanged.
        by = {int(v["version"]): v for v in versions["versions"]}
        assert (by[3]["definition"]["nodes"]
                == by[1]["definition"]["nodes"])
        # Historical snapshots untouched.
        assert by[2]["definition"]["nodes"] != by[1]["definition"]["nodes"]


async def test_restore_first_and_middle_versions():
    async with Client() as c:
        dep1 = await _deploy(c, GREEN_DEF)
        wid = dep1["workflow_id"]
        await _deploy(c, V2_DEF, wid)
        await _deploy(c, GREEN_DEF, wid)                 # v3
        st, res = await c.post(
            f"/ai_workflow/workflows/{wid}/versions/2/restore", {})
        assert st == 200 and res["new_version_number"] == 4
        st, versions = await c.get(f"/ai_workflow/workflows/{wid}/versions")
        by = {int(v["version"]): v for v in versions["versions"]}
        assert set(by) == {1, 2, 3, 4}
        assert (by[4]["definition"]["nodes"]
                == by[2]["definition"]["nodes"])


async def test_restore_diff_remains_correct():
    async with Client() as c:
        dep1 = await _deploy(c, GREEN_DEF)
        wid = dep1["workflow_id"]
        await _deploy(c, V2_DEF, wid)
        await c.post(f"/ai_workflow/workflows/{wid}/versions/1/restore", {})
        st, diff = await c.get(
            f"/ai_workflow/versions/diff?workflow_id={wid}"
            "&from_version=2&to_version=3")
        assert st == 200
        assert sorted(diff["added_nodes"]) == ["n1", "n2"]
        assert sorted(diff["removed_nodes"]) == ["a2", "t1"]


async def test_restored_workflow_executes():
    async with Client() as c:
        dep1 = await _deploy(c, GREEN_DEF)
        wid = dep1["workflow_id"]
        await _deploy(c, V2_DEF, wid)
        await c.post(f"/ai_workflow/workflows/{wid}/versions/1/restore", {})
        eid = await _execute(c, wid, GREEN_DEF)
        await _wait_db_status(eid, {"completed"})


async def test_restore_missing_workflow_404():
    async with Client() as c:
        st, res = await c.post(
            f"/ai_workflow/workflows/{uuid.uuid4()}/versions/1/restore", {})
        assert st == 404


async def test_restore_invalid_version_404():
    async with Client() as c:
        dep = await _deploy(c, GREEN_DEF)
        st, res = await c.post(
            f"/ai_workflow/workflows/{dep['workflow_id']}/versions/99/restore",
            {})
        assert st == 404


async def test_restore_cross_tenant_404():
    async with Client() as c1, Client() as c2:
        dep = await _deploy(c1, GREEN_DEF)
        await _deploy(c1, V2_DEF, dep["workflow_id"])
        st, res = await c2.post(
            f"/ai_workflow/workflows/{dep['workflow_id']}/versions/1/restore",
            {})
        assert st == 404


async def test_restore_invalid_definition_rejected():
    async with Client() as c:
        dep = await _deploy(c, GREEN_DEF)
        wid = dep["workflow_id"]
        await _deploy(c, V2_DEF, wid)

        # Corrupt the v1 snapshot definition (unknown connector) directly in
        # the DB, then verify restore refuses it with 422.
        from sqlalchemy import update as sa_update

        from app.core.database import async_session_factory
        from app.models.workflow import Workflow as WF

        async with async_session_factory() as session:
            row = await session.get(WF, wid)
            cfg = dict(row.config or {})
            versions = list(cfg.get("versions") or [])
            bad = dict(versions[0])
            bad_def = dict(bad["definition"])
            bad_def["nodes"] = [
                {"id": "x1", "kind": "action", "connector": "nope_connector",
                 "action": "run", "label": "Broken", "config": {}},
            ]
            bad["definition"] = bad_def
            versions[0] = bad
            await session.execute(
                sa_update(WF).where(WF.id == wid)
                .values(config={**cfg, "versions": versions}),
            )
            await session.commit()

        st, res = await c.post(
            f"/ai_workflow/workflows/{wid}/versions/1/restore", {})
        assert st == 422, (st, res)
        assert res["detail"]["code"] == "VERSION_INVALID"
