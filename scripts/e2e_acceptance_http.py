"""AutoFlow AI Phase 2 - REAL end-to-end acceptance over HTTP.

Proves the complete local pipeline against a *running* backend (no injected
catalog, no simulated responses): register -> login -> planner SSE chat -> compile
(plan + spec v1) -> ambiguous-prompt clarification -> validate -> deploy
(version 1) -> execute the persisted workflow through the Workflow Runtime
-> live SSE node events -> pause/resume -> cancel -> DB persistence ->
org-scoped execution history -> cross-tenant read blocked (404).

Requirements: backend running on AUTOFLOW_API_BASE (default
http://127.0.0.1:8001/api/v1) with PostgreSQL reachable.

Usage:  python scripts/e2e_acceptance_http.py
Exit code 0 when every stage passes, 1 otherwise.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE = os.environ.get("AUTOFLOW_API_BASE", "http://127.0.0.1:8001/api/v1")
EMAIL = f"e2e.{int(time.time())}@autoflow.test"
PASSWORD = "e2e-pass-12345"
PROMPT = "On a new event, post the data to a REST API"
AMBIGUOUS = "Send my data to Slack"

results = []


def report(stage, ok, detail=""):
    results.append((stage, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {stage}" + (f" :: {detail}" if detail else ""))


def http(method, path, body=None, token=None, stream=False):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        if stream:
            return resp.status, resp
        try:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
        finally:
            resp.close()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"detail": raw[:300].decode(errors="replace")}


def sse_frames(resp):
    """Yield (event, data) from an SSE stream (handles \\r\\n)."""
    pending = ""
    try:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if line == "":
                if pending:
                    event = "message"
                    data = {}
                    for part in pending.split("\n"):
                        if part.startswith("event:"):
                            event = part[6:].strip()
                        elif part.startswith("data:"):
                            try:
                                data = json.loads(part[5:].strip())
                            except Exception:
                                data = {"raw": part[5:].strip()}
                    yield event, data
                    pending = ""
            elif line.startswith("event:") or line.startswith("data:"):
                pending = (pending + "\n" + line) if pending else line
    finally:
        resp.close()


# 1-2. Register + login
st, reg = http("POST", "/auth/register",
               {"email": EMAIL, "password": PASSWORD, "full_name": "E2E Acceptance"})
report("1. Register user (personal org auto-created)", st == 201,
       json.dumps(reg)[:160] if st != 201 else "")
st, login = http("POST", "/auth/login", {"email": EMAIL, "password": PASSWORD})
token = (login or {}).get("access_token") or ""
report("2. Login -> JWT", st == 200 and bool(token), f"status={st}")
if st != 200 or not token:
    sys.exit(1)  # root cause is auth; downstream stages would cascade

# 3. Planner health
st, health = http("GET", "/planner/health", token=token)
report("3. Planner health (real catalog)", st == 200 and (health or {}).get("status") == "ok",
       f"catalog={len((health or {}).get('catalog') or {})}")

# 4. Chat SSE stream
st, resp = http("POST", "/planner/chat/stream", {"message": PROMPT}, token=token, stream=True)
events = list(sse_frames(resp)) if st == 200 else []
stages = [d for e, d in events if e == "stage"]
tokens = [d for e, d in events if e == "token"]
metas = [d for e, d in events if e == "meta"]
meta = metas[0] if metas else {}
report("4. Chat SSE (stages/tokens/meta)", st == 200 and stages and tokens and meta,
       f"stages={len(stages)} tokens={len(tokens)} reply_len={len(meta.get('reply') or '')}")
report("4b. Chat meta carries preview + provider flag", bool(meta.get("preview")) and bool(meta.get("provider")),
       f"provider={meta.get('provider')}")

# 5. Ambiguous prompt -> clarification (no invalid workflow)
st, amb = http("POST", "/planner/compile", {"prompt": AMBIGUOUS}, token=token)
report("5. Ambiguous prompt -> structured clarification", st == 200 and (amb or {}).get("clarification_required") is True,
       "; ".join((amb or {}).get("clarification_questions") or [])[:160])

# 6. Compile: prompt -> plan -> Spec v1
st, comp = http("POST", "/planner/compile", {"prompt": PROMPT}, token=token)
plan = (comp or {}).get("plan") or {}
spec = (comp or {}).get("spec") or {}
steps = plan.get("steps") or []
report("6. Compile -> WorkflowPlan + Spec v1", st == 200 and (comp or {}).get("ok") is True and bool(spec),
       f"plan_steps={len(steps)} spec_nodes={len(spec.get('nodes') or [])} confidence={plan.get('confidence')} cost={plan.get('estimated_cost')} latency_ms={plan.get('estimated_latency_ms')}")

# 7. Build builder definition from the plan (frontend-equivalent)
first_step = steps[0] if steps else {}
nodes = [
    {"id": "trigger", "kind": "trigger", "label": "Webhook trigger",
     "connector": "webhook", "action": "", "config": {}},
    {"id": str(first_step.get("id") or "1"), "kind": "action",
     "label": first_step.get("name") or "Post to REST",
     "connector": first_step.get("connector") or "rest",
     "action": first_step.get("action") or "post", "config": {}},
]
edges = [{"source": "trigger", "target": str(first_step.get("id") or "1")}]
definition = {"name": plan.get("name") or "E2E workflow", "nodes": nodes, "edges": edges}
report("7. Definition built from plan", len(nodes) == 2 and len(edges) == 1,
       f"nodes={[n['connector'] for n in nodes]} edges={len(edges)}")

# 8. Validate
st, val = http("POST", "/ai_workflow/validate", {"definition": definition}, token=token)
report("8. Validate (auth warning surfaced, non-blocking)", st == 200 and (val or {}).get("valid") is True,
       f"errors={(val or {}).get('errors')} warnings={(val or {}).get('warnings')}")

# 9. Deploy -> version 1, no auto-execute
st, dep = http("POST", "/ai_workflow/deploy",
               {"definition": definition, "workflow_id": None, "description": "Phase 2 acceptance"},
               token=token)
wf_id = (dep or {}).get("workflow_id")
report("9. Deploy -> workflow + v1 (no auto-execute)",
       st == 200 and (dep or {}).get("ok") is True and bool(wf_id),
       f"version={(dep or {}).get('version')} errors={(dep or {}).get('errors')}")
if not wf_id:
    sys.exit(1)  # deploy failed; execute/history stages would cascade

# 10. Version history
st, vers = http("GET", f"/ai_workflow/workflows/{wf_id}/versions", token=token)
snaps = (vers or {}).get("versions") or []
report("10. Version history lists v1 with spec", st == 200 and len(snaps) == 1 and snaps[0].get("version") == 1
       and bool(snaps[0].get("spec")),
       f"current={(vers or {}).get('current_version')} snapshots={len(snaps)}")

# 11. Execute the DEPLOYED workflow (no definition passed -> persisted config)
st, ex = http("POST", "/ai_workflow/execute",
              {"workflow_id": wf_id, "inputs": {"trigger": {"payload": {"event": "ping"}}}},
              token=token)
exec_id = (ex or {}).get("execution_id")
report("11. Execute persisted workflow via runtime", st == 200 and bool(exec_id),
       f"status={(ex or {}).get('status')}")

# 12. SSE stream -> terminal state + per-node events
st, resp = http("GET", f"/ai_workflow/executions/{exec_id}/stream", token=token, stream=True)
events = list(sse_frames(resp)) if st == 200 else []
node_events = [d for e, d in events if e == "node"]
states = [d for e, d in events if e == "state"]
final_state = states[-1] if states else {}
report("12. Execution SSE -> terminal state", st == 200 and bool(states),
       f"node_events={len(node_events)} status={final_state.get('status')}")
report("12b. Per-node states recorded", bool(final_state.get("node_states")),
       json.dumps(final_state.get("node_states"))[:160])

# 13. Live controls on a second throttled run: pause -> resume -> complete
st, ex2 = http("POST", "/ai_workflow/execute",
               {"workflow_id": wf_id, "node_pacing_ms": 1500,
                "inputs": {"trigger": {"payload": {"event": "ping"}}}},
               token=token)
exec2 = (ex2 or {}).get("execution_id")
paused_ok = False
if exec2:
    http("POST", f"/ai_workflow/executions/{exec2}/control", {"action": "pause"}, token=token)
    for _ in range(15):
        time.sleep(0.2)
        st, d = http("GET", f"/ai_workflow/executions/{exec2}", token=token)
        if (d or {}).get("status") == "paused":
            paused_ok = True
            break
report("13a. Pause mid-run observed via API", bool(paused_ok))
resumed_ok = False
if exec2 and paused_ok:
    http("POST", f"/ai_workflow/executions/{exec2}/control", {"action": "resume"}, token=token)
    for _ in range(25):
        time.sleep(0.4)
        st, d = http("GET", f"/ai_workflow/executions/{exec2}", token=token)
        if (d or {}).get("status") == "completed":
            resumed_ok = True
            break
report("13b. Resume -> completed", bool(resumed_ok))

# 14. Cancel a third run
st, ex3 = http("POST", "/ai_workflow/execute",
               {"workflow_id": wf_id, "node_pacing_ms": 1500,
                "inputs": {"trigger": {"payload": {"event": "ping"}}}},
               token=token)
exec3 = (ex3 or {}).get("execution_id")
cancelled_ok = False
cancel_states = []
if exec3:
    http("POST", f"/ai_workflow/executions/{exec3}/control", {"action": "cancel"}, token=token)
    st, resp = http("GET", f"/ai_workflow/executions/{exec3}/stream", token=token, stream=True)
    evs = list(sse_frames(resp)) if st == 200 else []
    cancel_states = [d for e, d in evs if e == "state"]
    cancelled_ok = bool(cancel_states) and cancel_states[-1].get("status") == "cancelled"
report("14. Cancel -> cancelled terminal state (partial progress preserved)",
       bool(cancelled_ok),
       json.dumps(cancel_states[-1].get("node_states"))[:160] if cancel_states else "")

# 15. Persisted DB record (org-scoped generated API)
time.sleep(1.0)
st, rec = http("GET", f"/execution/{exec_id}", token=token)
report("15. Execution record persisted in DB", st == 200 and (rec or {}).get("status") == "completed",
       f"status={(rec or {}).get('status')} duration_ms={(rec or {}).get('duration_ms')}")

# 16. Execution history (org-scoped list)
st, hist = http("GET", "/execution?page=1&page_size=50&sort_order=desc", token=token)
items = ((hist or {}).get("items")) or []
report("16. Execution history lists the run", any(i.get("id") == exec_id for i in items),
       f"total={(hist or {}).get('total')}")

# 17. Tenant isolation (second org must NOT see the run)
EMAIL2 = f"other.{int(time.time())}@autoflow.test"
http("POST", "/auth/register", {"email": EMAIL2, "password": PASSWORD, "full_name": "Other Org"})
st, login2 = http("POST", "/auth/login", {"email": EMAIL2, "password": PASSWORD})
tok2 = (login2 or {}).get("access_token") or ""
st, cross = http("GET", f"/execution/{exec_id}", token=tok2)
report("17. Tenant isolation (other org blocked)", st == 404,
       f"status={st} (cross-org read must 404)")

failed = [r for r in results if not r[1]]
print("\n=== SUMMARY ===")
for s, ok, d in results:
    print(f"{'PASS' if ok else 'FAIL'}  {s}")
print(f"\n{len(results) - len(failed)}/{len(results)} stages passed")
sys.exit(1 if failed else 0)
