"""AIPlannerGenerator class + builders (appended to ai_planner_generator.py).

This module is READ as source text and appended to the generator file by
scripts/build_ai_planner.py. Keeping it a standalone module avoids nested
triple-quote escaping inside the generator.
"""

# ---------------------------------------------------------------------------
# app/ai/__init__.py builder
# ---------------------------------------------------------------------------


def _build_ai_package_init(pdef):
    """backend/app/ai/__init__.py"""
    return '''"""AutoFlow AI - AI module (generated from metadata).

Exposes the AI planner facade and the LLM provider factory. The planner
reasons and plans; the Workflow Runtime executes.
"""

from app.ai.planner import AIPlanner, PlanRequest, PlanResult, WorkflowPlan
from app.ai.providers import BaseLLMProvider, provider_factory, provider_names

__all__ = [
    "AIPlanner", "BaseLLMProvider", "PlanRequest", "PlanResult",
    "WorkflowPlan", "provider_factory", "provider_names",
]
'''


# ---------------------------------------------------------------------------
# Tests builder
# ---------------------------------------------------------------------------


def _build_tests(pdef):
    """tests/ai/test_ai_planner.py"""
    return _AI_TEST_TEMPLATE


# ---------------------------------------------------------------------------
# Docs builder
# ---------------------------------------------------------------------------


def _build_docs(pdef):
    """docs/ai_planner.md"""
    providers = sorted(pdef.providers.keys()) or ["openai", "anthropic"]
    strategy = pdef.strategies[0] if pdef.strategies else "structured"
    lines = [
        "# AutoFlow AI - AI Planner",
        "",
        "The AI Planner converts natural language into deterministic, validated",
        "workflow execution plans. **The planner reasons, plans and validates; it",
        "never executes workflows.** Its output (a `WorkflowPlan`) is consumed by",
        "the Workflow Runtime, and it discovers connector capabilities through the",
        "Connector Registry.",
        "",
        "## Architecture",
        "",
        "```",
        "User Prompt",
        "    |",
        "    v",
        "Prompt Normalizer -> Intent Analyzer -> Entity Extractor -> Task Extractor",
        "    -> Connector Discovery -> Capability Matcher -> Constraint Solver",
        "    -> Workflow/Graph Builder -> Validator -> Optimizer",
        "    -> WorkflowPlan (Runtime input)",
        "```",
        "",
        "## Planning pipeline",
        "",
        "The 11 deterministic stages live in `backend/app/ai/planner/`:",
        "",
        "| Stage | Module | Deterministic |",
        "|-------|--------|---------------|",
        "| 1 Normalize | `normalizer.py` | yes |",
        "| 2 Intent | `intent.py` | yes (LLM-optional) |",
        "| 3 Entities | `entity_extractor.py` | yes (LLM-optional) |",
        "| 4 Tasks | `task_extractor.py` | yes (LLM-optional) |",
        "| 5 Connectors | `connector_selector.py` | yes |",
        "| 6 Capabilities | `capability_matcher.py` | yes |",
        "| 7 Constraints | `constraint_solver.py` | yes |",
        "| 8 Workflow+Graph | `workflow_builder.py`, `graph_builder.py` | yes |",
        "| 9 Validate | `validator.py` | yes |",
        "| 10 Optimize | `optimizer.py` | yes |",
        "| 11 Specify | `pipeline.py`/`planner.py` | yes |",
        "",
        "LLM-dependent stages (intent, entities, tasks, clarification) fall back",
        "to deterministic heuristics when no provider is configured, so the",
        "planner works offline and tests are hermetic.",
        "",
        "## Metadata",
        "",
        "The planner is fully metadata-driven from `metadata/ai/`:",
        "",
        "- `planner.yaml` - strategies, models, constraints",
        "- `reasoning.yaml` - reasoning strategies and step types",
        "- `constraints.yaml` - hard plan constraints",
        "- `optimization.yaml` - optimizer rules and cost/latency defaults",
        "- `providers.yaml` - LLM provider registry",
        "- `memory.yaml` - memory backend configuration",
        "- `examples.yaml` - few-shot planning examples",
        "",
        f"Default strategy: **{strategy}**. Providers: {', '.join(providers)}.",
        "",
        "## Usage",
        "",
        "```python",
        "from app.ai import AIPlanner",
        "",
        "planner = AIPlanner()  # deterministic fallback when no API key",
        "result = planner.plan(\"when a new email arrives, send a message to slack\")",
        "plan = result.plan",
        "print(plan.name, plan.confidence, plan.estimated_cost)",
        "# plan.to_runtime_definition() -> app.runtime.WorkflowCompiler input",
        "```",
        "",
        "## LLM providers",
        "",
        "The planner depends only on `BaseLLMProvider` "
        "(`backend/app/ai/providers/base.py`). Concrete SDKs are wrapped in",
        "import-safe adapters:",
        "",
        "- OpenAI (`providers/openai.py`) - SDK or httpx fallback",
        "- Anthropic (`providers/anthropic.py`) - SDK or httpx fallback",
        "- Gemini (`providers/gemini.py`) - REST",
        "- OpenRouter (`providers/openrouter.py`) - REST",
        "- Ollama (`providers/ollama.py`) - local, no key",
        "- vLLM (`providers/vllm.py`) - local OpenAI-compatible",
        "",
        "Providers resolve through `providers/factory.py` by name and env key.",
        "",
        "## Extending the planner",
        "",
        "1. Add a stage module under `backend/app/ai/planner/`.",
        "2. Register the stage in `pipeline.py` (see `stage_names()`).",
        "3. Add/adjust metadata in `metadata/ai/` and regenerate:",
        "",
        "```bash",
        "python scripts/generate.py backend.ai --force",
        "python scripts/validate_ai_planner.py",
        "```",
        "",
        "## Troubleshooting",
        "",
        "- **No API key configured** - the planner falls back to deterministic",
        "  heuristics; plans are still produced for known connectors.",
        "- **Unknown connector** - the prompt names a connector not in the",
        "  registry; the planner asks a clarification question instead of",
        "  guessing.",
        "- **Missing credentials** - plans warn (never guess) when a private",
        "  connector has no credentials.",
        "- **Validation failures** - `PlanValidationError` carries `errors`;",
        "  inspect `result.reasoning` for the full stage trace.",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# AIPlannerGenerator
# ---------------------------------------------------------------------------


class AIPlannerGenerator:
    """Generates the AI planner package from metadata."""

    def __init__(self, writer=None, model=None):
        self.writer = writer
        self.model = model or MetadataLoader("metadata").load_all()

    def generate(self, writer=None, force=False):
        """Generate all AI planner files; returns written paths."""
        writer = writer or self.writer
        if writer is None:
            raise ValueError("no writer provided")
        pdef = self.model.planner or PlannerDef()
        files = []

        # Planner framework modules
        for rel_path, source in sorted(MODULE_SOURCES.items()):
            if rel_path.startswith("providers/"):
                sub = rel_path.split("/", 1)[1]
                path = f"backend/app/ai/providers/{sub}.py"
            elif rel_path == "__init__":
                path = "backend/app/ai/planner/__init__.py"
            else:
                path = f"backend/app/ai/planner/{rel_path}.py"
            writer.write(path, source, force=force)
            files.append(path)

        # Examples embedded into the generated examples module
        examples_src = MODULE_SOURCES["examples"]
        examples_src += "\n\nset_examples(" + repr(pdef.examples) + ")\n"
        writer.write("backend/app/ai/planner/examples.py", examples_src,
                     force=force)

        # app/ai/__init__.py
        ai_init = "backend/app/ai/__init__.py"
        writer.write(ai_init, _build_ai_package_init(pdef), force=force)
        files.append(ai_init)

        # Tests
        test_init = "tests/ai/__init__.py"
        writer.write(test_init, '"""AutoFlow AI - AI planner tests."""\n',
                     force=force)
        files.append(test_init)
        test_file = "tests/ai/test_ai_planner.py"
        writer.write(test_file, _build_tests(pdef), force=force)
        files.append(test_file)

        # Docs
        doc_file = "docs/ai_planner.md"
        writer.write(doc_file, _build_docs(pdef), force=force)
        files.append(doc_file)

        return files


_AI_TEST_TEMPLATE = '''"""AutoFlow AI - AI Planner tests (generated from metadata).

Hermetic tests: no network, no API keys. The pipeline is exercised with an
injected deterministic connector catalog; the LLM-dependent stages fall back
to heuristics (provider=None).
"""

import pytest

from app.ai.planner.ambiguity import AmbiguityDetector
from app.ai.planner.capability_matcher import CapabilityMatcher
from app.ai.planner.clarification import ClarificationEngine
from app.ai.planner.confidence import ConfidenceScorer
from app.ai.planner.connector_selector import ConnectorSelector
from app.ai.planner.constraint_solver import ConstraintSolver
from app.ai.planner.cost_estimator import CostEstimator
from app.ai.planner.entity_extractor import EntityExtractor
from app.ai.planner.exceptions import (
    CapabilityMatchError, GraphError, PlanValidationError,
    ProviderNotConfiguredError,
)
from app.ai.planner.graph_builder import WorkflowGraphBuilder
from app.ai.planner.intent import IntentAnalyzer
from app.ai.planner.latency_estimator import LatencyEstimator
from app.ai.planner.memory import PlannerMemory
from app.ai.planner.metrics import PlannerMetrics
from app.ai.planner.models import PlanRequest, PlanStep
from app.ai.planner.normalizer import PromptNormalizer, normalize_text
from app.ai.planner.optimizer import PlanOptimizer
from app.ai.planner.pipeline import PlanningPipeline
from app.ai.planner.task_extractor import TaskExtractor
from app.ai.planner.validator import PlanValidator
from app.ai.planner.workflow_builder import WorkflowBuilder
from app.ai.planner.planner import AIPlanner


CATALOG = {
    "slack": {
        "name": "slack", "version": "1.0.0",
        "authentication": {"type": "oauth2", "credential_fields": ["token"]},
        "actions": ["send_message", "list_messages", "create_channel"],
        "triggers": ["message_received"],
        "capabilities": {"actions": True, "triggers": True},
    },
    "gmail": {
        "name": "gmail", "version": "1.0.0",
        "authentication": {"type": "oauth2"},
        "actions": ["send_email", "list_emails", "search_emails"],
        "triggers": ["email_received"],
        "capabilities": {"actions": True},
    },
    "notion": {
        "name": "notion", "version": "1.0.0",
        "authentication": {"type": "api_key"},
        "actions": ["create_page", "update_page", "search_pages"],
        "triggers": [],
        "capabilities": {"actions": True},
    },
    "google_drive": {
        "name": "google_drive", "version": "1.0.0",
        "authentication": {"type": "oauth2"},
        "actions": ["upload_file", "download_file", "list_files"],
        "triggers": [],
        "capabilities": {"actions": True},
    },
}


def make_pipeline(provider=None):
    return PlanningPipeline(catalog=CATALOG, provider=provider, max_steps=20)


# --- Normalizer ------------------------------------------------------------

def test_normalize_text():
    assert normalize_text("  Hello,   WORLD!  ") == "hello, world"


def test_normalizer_structure():
    n = PromptNormalizer().normalize("Please send a message to slack")
    assert n.word_count > 0
    assert "slack" in n.text
    assert n.signature


# --- Intent ----------------------------------------------------------------

def test_intent_automate():
    r = IntentAnalyzer().classify("automate a workflow when a new email arrives")
    assert r["name"] == "automate"


def test_intent_notify():
    r = IntentAnalyzer().classify("notify me on discord about new orders")
    assert r["name"] in ("notify", "automate")


def test_intent_unknown():
    r = IntentAnalyzer().classify("zzz qqq wwww")
    assert r["name"] == "unknown"


# --- Entity extraction -----------------------------------------------------

def test_entity_extractor_connectors():
    ex = EntityExtractor(known_connectors=["slack", "gmail"])
    e = ex.extract("send to slack and gmail", ["slack", "gmail"])
    assert "slack" in e["connectors"]
    assert "gmail" in e["connectors"]


def test_entity_extractor_emails():
    ex = EntityExtractor()
    e = ex.extract("email finance@acme.com")
    assert "finance@acme.com" in e["emails"]


# --- Task extraction -------------------------------------------------------

def test_task_extractor_send():
    t = TaskExtractor().extract("send a message to slack")
    assert any(x["action"] == "send_message" for x in t)


def test_task_extractor_empty():
    assert TaskExtractor().extract("hello") == []


# --- Connector discovery ---------------------------------------------------

def test_connector_selector_discover():
    sel = ConnectorSelector(catalog=CATALOG)
    found = sel.discover({"connectors": ["slack"]}, "slack")
    assert found and found[0]["connector"] == "slack"


def test_connector_selector_none_raises():
    sel = ConnectorSelector(catalog=CATALOG)
    with pytest.raises(Exception):
        sel.select({"connectors": []}, "no connector here")


# --- Capability matching ---------------------------------------------------

def test_capability_matcher_exact():
    m = CapabilityMatcher(catalog=CATALOG)
    best = m.best({"action": "send_message", "target": "send a message"},
                  "slack")
    assert best is not None and best["action"] == "send_message"


def test_capability_matcher_missing_raises():
    m = CapabilityMatcher(catalog=CATALOG)
    with pytest.raises(CapabilityMatchError):
        m.require({"action": "fly_to_moon", "target": "x"}, "slack")


# --- Constraint solver -----------------------------------------------------

def test_constraint_solver_step_limit():
    s = ConstraintSolver()
    assert s.check_step_limit(5) == []
    assert s.check_step_limit(999)


def test_constraint_solver_missing_parameters():
    s = ConstraintSolver()
    missing = s.missing_parameters(
        {"to": {"required": True}, "subject": {"required": False}},
        {"subject": "hi"},
    )
    assert "to" in missing


def test_constraint_solver_dependencies():
    s = ConstraintSolver()
    resolved = s.resolve_dependencies([{}, {"depends_on": [0]}])
    assert resolved[1]["depends_on"] == ["1"]


# --- Graph builder ---------------------------------------------------------

def test_graph_builder_linear():
    steps = [PlanStep(id="a"), PlanStep(id="b", depends_on=["a"])]
    g = WorkflowGraphBuilder().build(steps)
    assert set(g["nodes"]) == {"a", "b"}
    assert g["topological_order"][0] == "a"


def test_graph_builder_cycle_raises():
    steps = [PlanStep(id="a", depends_on=["b"]),
             PlanStep(id="b", depends_on=["a"])]
    with pytest.raises(GraphError):
        WorkflowGraphBuilder().build(steps)


# --- Workflow builder ------------------------------------------------------

def test_workflow_builder_builds_steps():
    plan = WorkflowBuilder(name="Test").build(
        [{"id": "1", "connector": "slack", "action": "send_message",
          "depends_on": []}],
        {"1": {"action": "send_message"}},
        {"type": "webhook"},
    )
    assert len(plan.steps) == 1
    assert plan.steps[0].connector == "slack"


# --- Validator -------------------------------------------------------------

def test_validator_unknown_connector_raises():
    plan = WorkflowBuilder(name="Bad").build(
        [{"id": "1", "connector": "nope", "action": "run"}],
        {"1": {"action": "run"}},
        {"type": "webhook"},
    )
    with pytest.raises(PlanValidationError):
        PlanValidator(catalog=CATALOG).validate(plan)


def test_validator_ok():
    plan = WorkflowBuilder(name="OK").build(
        [{"id": "1", "connector": "slack", "action": "send_message"}],
        {"1": {"action": "send_message"}},
        {"type": "webhook"},
    )
    result = PlanValidator(catalog=CATALOG).validate(plan)
    assert result["valid"] is True


# --- Optimizer -------------------------------------------------------------

def test_optimizer_merges_redundant():
    plan = WorkflowBuilder(name="Opt").build(
        [{"id": "1", "connector": "slack", "action": "send_message"},
         {"id": "2", "connector": "slack", "action": "send_message"}],
        {"1": {"action": "send_message"}, "2": {"action": "send_message"}},
    )
    PlanOptimizer().optimize(plan)
    assert len(plan.steps) == 1
    assert "merge_redundant_nodes" in plan.metadata["optimizer"]["rules"]


# --- Ambiguity + clarification ---------------------------------------------

def test_ambiguity_missing_trigger():
    issues = AmbiguityDetector().detect(
        {"connectors": ["slack"]}, [], [], None, CATALOG)
    assert any(i["category"] == "trigger" for i in issues)


def test_clarification_engine():
    issues = [{"category": "connector", "message": "which one?",
               "options": ["slack", "gmail"]}]
    qs = ClarificationEngine().to_questions(issues)
    assert qs[0].category == "connector"
    assert "[Connector]" in ClarificationEngine().format(qs)[0]


# --- Estimators + confidence -----------------------------------------------

def test_cost_estimator():
    steps = [PlanStep(id="1", connector="slack", action="send_message")]
    est = CostEstimator().estimate(steps, {"type": "webhook"})
    assert est["total"] > 0


def test_latency_estimator():
    steps = [PlanStep(id="1", connector="slack", action="send_message"),
             PlanStep(id="2", connector="gmail", action="send_email",
                      depends_on=["1"])]
    est = LatencyEstimator().estimate(steps, None)
    assert est["total_ms"] > 0


def test_confidence_scorer():
    c = ConfidenceScorer()
    assert c.score(intent_confidence=0.9, capability_scores=[1.0]) > 0.6
    assert c.bucket(0.1) == "low"


# --- Memory + metrics ------------------------------------------------------

def test_planner_memory_ttl():
    m = PlannerMemory(ttl=0)
    m.set("k", "v", ttl=0)
    assert m.get("k") is None


def test_planner_metrics():
    pm = PlannerMetrics()
    pm.record(12.0, confidence=0.8, model="test")
    snap = pm.snapshot()
    assert snap["count"] == 1
    assert snap["model_usage"]["test"] == 1


# --- Pipeline end-to-end (deterministic) -----------------------------------

def test_pipeline_end_to_end():
    pipe = make_pipeline(provider=None)
    result = pipe.plan(PlanRequest(
        prompt="when a new email arrives, send a message to slack",
        organization_id="org-1",
        session_memory={"credentials": {"slack": "x"}},
    ))
    assert result.plan is not None
    assert len(result.plan.steps) >= 1
    assert result.reasoning


def test_pipeline_clarification():
    pipe = make_pipeline(provider=None)
    result = pipe.plan(PlanRequest(prompt="create a report"))
    assert result.plan is not None
    assert result.plan.clarification_required is True


def test_pipeline_stages_registered():
    pipe = make_pipeline()
    names = pipe.stage_names()
    assert "normalize" in names and "optimize" in names


# --- AIPlanner facade ------------------------------------------------------

def test_ai_planner_facade():
    planner = AIPlanner(provider=None, catalog=CATALOG, use_cache=False)
    result = planner.plan(
        "when a new email arrives, send a message to slack",
        organization_id="org-1",
        session_memory={"credentials": {"slack": "x"}},
    )
    assert result.plan is not None


def test_ai_planner_clarify():
    planner = AIPlanner(provider=None, catalog=CATALOG, use_cache=False)
    questions = planner.clarify("send a report")
    assert isinstance(questions, list)


def test_ai_planner_metrics():
    planner = AIPlanner(provider=None, catalog=CATALOG, use_cache=False)
    planner.plan("when a new email arrives, send a message to slack",
                 session_memory={"credentials": {"slack": "x"}})
    assert planner.metrics()["count"] >= 1


# --- Providers -------------------------------------------------------------

def test_provider_factory_unconfigured_raises():
    from app.ai.providers.factory import provider_factory
    with pytest.raises(ProviderNotConfiguredError):
        provider_factory("openai")  # no OPENAI_API_KEY in test env


def test_provider_names_registered():
    from app.ai.providers.factory import provider_names
    names = provider_names()
    assert "openai" in names
    assert "anthropic" in names
    assert "ollama" in names
    assert "vllm" in names


def test_plan_to_runtime_definition():
    pipe = make_pipeline()
    result = pipe.plan(PlanRequest(
        prompt="when a new email arrives, send a message to slack",
        session_memory={"credentials": {"slack": "x"}}))
    runtime = result.plan.to_runtime_definition()
    assert "nodes" in runtime and "edges" in runtime
    assert runtime["nodes"]
'''
