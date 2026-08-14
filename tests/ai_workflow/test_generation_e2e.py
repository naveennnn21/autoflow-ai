"""End-to-end AI workflow generation test.

Natural-language prompt -> AI Planner (deterministic fallback) ->
WorkflowPlan -> Prompt Compiler -> Workflow Specification v1 -> runtime
definition -> Workflow Runtime execution. Hermetic: injected connector
catalog, no network, no API keys.
"""

import asyncio

from app.ai import AIPlanner
from app.compiler.compiler import PromptCompiler
from app.services.ai_runtime import StreamingExecutor

# Connector catalog injected into the planner + runtime so the whole flow
# is hermetic. Every connector is auth-free so execution completes.
CATALOG = {
    "webhook": {
        "name": "webhook",
        "version": "1.0.0",
        "authentication": {"type": "none"},
        "actions": ["run", "transform_payload", "verify_signature"],
        "triggers": ["webhook_received"],
        "capabilities": {"actions": True, "triggers": True},
    },
    "manual": {
        "name": "manual",
        "version": "1.0.0",
        "authentication": {"type": "none"},
        "actions": ["run"],
        "triggers": [],
        "capabilities": {"actions": True},
    },
}

PROMPT = "when a webhook is received, transform the payload"


async def test_prompt_to_plan_to_spec_to_runtime_execution():
    # 1. Planner: natural language -> WorkflowPlan
    planner = AIPlanner(provider=None, catalog=CATALOG, use_cache=False)
    result = planner.plan(
        PROMPT,
        organization_id="org-1",
        session_memory={"credentials": {"webhook": "secret"}},
    )
    assert result.plan is not None, result.errors
    assert result.plan.clarification_required is False
    assert result.intent

    # 2. Prompt Compiler: WorkflowPlan -> Workflow Specification v1
    compiler = PromptCompiler(connector_names=sorted(CATALOG))
    spec, report = compiler.compile_with_report(result.plan)
    assert not report.errors, report.errors
    spec_dict = spec.to_dict()
    assert spec_dict["version"] == 1
    assert spec_dict["nodes"]
    assert spec_dict["edges"] is not None

    # 3. Runtime contract: spec -> definition the Workflow Runtime consumes
    runtime_def = spec.to_runtime_definition()
    assert runtime_def["nodes"], "spec must emit runtime nodes"
    assert runtime_def["workflow_id"]

    # 4. Workflow Runtime: execute to completion through the real executor
    queue: asyncio.Queue = asyncio.Queue()
    executor = StreamingExecutor(queue, "exec-e2e", catalog=CATALOG,
                                 node_pacing_ms=0)
    state = await executor.execute(
        runtime_def,
        inputs={"trigger": {"payload": {"event": "ping"}}},
        execution_id="exec-e2e",
    )
    assert state.status == "completed", state.error
    assert state.node_states, "execution must record per-node states"
    assert all(
        st == "completed" for st in state.node_states.values()
    )

    # Events were published for live streaming consumers.
    node_events = []
    while not queue.empty():
        event = queue.get_nowait()
        if event["type"] == "node":
            node_events.append(event)
    assert node_events


async def test_ambiguous_prompt_requires_clarification_not_spec():
    # "create a report" is ambiguous - the planner must ask, not generate.
    planner = AIPlanner(provider=None, catalog=CATALOG, use_cache=False)
    result = planner.plan("create a report", organization_id="org-1")
    assert result.plan is not None
    assert result.plan.clarification_required is True
    assert result.plan.clarification_questions


def test_plan_carries_estimates_and_confidence():
    planner = AIPlanner(provider=None, catalog=CATALOG, use_cache=False)
    result = planner.plan(
        PROMPT, organization_id="org-1",
        session_memory={"credentials": {"webhook": "secret"}},
    )
    assert result.plan is not None
    assert result.plan.confidence >= 0.0
    assert result.plan.estimated_cost >= 0.0
    assert result.plan.estimated_latency_ms >= 0.0
