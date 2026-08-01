"""AI Planner Generator - Produces the intelligence layer of AutoFlow AI.

Consumes metadata/ai/*.yaml (planner, reasoning, constraints, optimization,
providers, memory, examples) and produces a production-ready, deterministic
planning pipeline: prompt normalization -> intent -> entity extraction ->
task extraction -> connector discovery -> capability matching -> constraint
solving -> workflow/graph building -> validation -> optimization -> the
final WorkflowPlan specification.

The planner REASONS and PLANS; it never executes workflows. Its output is a
WorkflowPlan consumed by the Workflow Runtime (app.runtime), and it discovers
connector capabilities through the Connector Registry (app.connectors).

The planner depends only on BaseLLMProvider -- never on a concrete LLM SDK.
Every provider module is import-safe (stdlib first; optional SDKs such as
openai/anthropic/requests/httpx are imported defensively), so the planner
validates cleanly in any environment and falls back to deterministic
heuristic planning when no provider is configured.

The 11-stage pipeline is deterministic and each stage is independently
testable. LLM-dependent stages (intent, entities, tasks, clarification)
produce structured, parseable output; all other stages are pure functions
over the metadata model and connector registry.
"""

from typing import Dict, List, Optional

from scripts.generators.common.intermediate_model import (
    MetadataModel, PlannerDef,
)
from scripts.generators.common.metadata_loader import MetadataLoader
from scripts.generators.common.writer import FileWriter

# ---------------------------------------------------------------------------
# Core framework module sources
# Each entry is the full source of backend/app/ai/planner/<name>.py
# ---------------------------------------------------------------------------

MODULE_SOURCES: Dict[str, str] = {}


def _register_source(name: str, source: str) -> None:
    """Register a planner module source under its relative module path."""
    MODULE_SOURCES[name] = source


# ---------------------------------------------------------------------------
# exceptions.py
# ---------------------------------------------------------------------------

_register_source("exceptions", '''"""AutoFlow AI - AI planner exceptions (generated from metadata).

A single exception hierarchy for the planning pipeline so callers can
catch one base type and inspect ``stage`` for granular handling.
"""

from typing import Optional


class PlannerError(Exception):
    """Base class for all AI planner errors."""

    def __init__(self, message: str = "", stage: str = "",
                 kind: str = "planner_error") -> None:
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.kind = kind


class NormalizationError(PlannerError):
    """Raised when a prompt cannot be normalized."""

    def __init__(self, message: str = "", stage: str = "normalize") -> None:
        super().__init__(message, stage=stage, kind="normalization_error")


class IntentError(PlannerError):
    """Raised when intent cannot be classified."""

    def __init__(self, message: str = "", stage: str = "intent") -> None:
        super().__init__(message, stage=stage, kind="intent_error")


class EntityExtractionError(PlannerError):
    """Raised when entity extraction fails."""

    def __init__(self, message: str = "", stage: str = "entities") -> None:
        super().__init__(message, stage=stage, kind="entity_extraction_error")


class ConnectorDiscoveryError(PlannerError):
    """Raised when connector discovery fails."""

    def __init__(self, message: str = "", stage: str = "connectors") -> None:
        super().__init__(message, stage=stage, kind="connector_discovery_error")


class CapabilityMatchError(PlannerError):
    """Raised when no connector capability matches a task."""

    def __init__(self, message: str = "", stage: str = "capabilities") -> None:
        super().__init__(message, stage=stage, kind="capability_match_error")


class ConstraintError(PlannerError):
    """Raised when plan constraints cannot be satisfied."""

    def __init__(self, message: str = "", stage: str = "constraints") -> None:
        super().__init__(message, stage=stage, kind="constraint_error")


class GraphError(PlannerError):
    """Raised when the workflow graph is invalid (cycles, disconnects)."""

    def __init__(self, message: str = "", stage: str = "graph") -> None:
        super().__init__(message, stage=stage, kind="graph_error")


class PlanValidationError(PlannerError):
    """Raised when the generated plan fails validation."""

    def __init__(self, message: str = "", stage: str = "validate",
                 errors: Optional[list] = None) -> None:
        super().__init__(message, stage=stage, kind="validation_error")
        self.errors = errors or []


class ProviderError(PlannerError):
    """Raised when an LLM provider call fails."""

    def __init__(self, message: str = "", stage: str = "llm",
                 provider: str = "") -> None:
        super().__init__(message, stage=stage, kind="provider_error")
        self.provider = provider


class ProviderNotConfiguredError(ProviderError):
    """Raised when the requested provider has no API key configured."""

    def __init__(self, provider: str = "", stage: str = "llm") -> None:
        super().__init__(f"Provider '{provider}' is not configured",
                         stage=stage, provider=provider)


class AmbiguityError(PlannerError):
    """Raised when the prompt is too ambiguous to plan safely."""

    def __init__(self, message: str = "", stage: str = "ambiguity",
                 questions: Optional[list] = None) -> None:
        super().__init__(message, stage=stage, kind="ambiguity_error")
        self.questions = questions or []
''')


# ---------------------------------------------------------------------------
# models.py
# ---------------------------------------------------------------------------

_register_source("models", '''"""AutoFlow AI - AI planner data models (generated from metadata).

Runtime-visible types for the planning pipeline. The planner consumes
``PlanRequest`` and produces ``PlanResult`` wrapping a ``WorkflowPlan``
specification that the Workflow Runtime can compile and execute.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanRequest:
    """A planning request: a natural-language prompt plus context."""

    prompt: str
    organization_id: str = ""
    user_id: str = ""
    conversation_id: str = ""
    provider: str = ""
    model: str = ""
    session_memory: Dict[str, Any] = field(default_factory=dict)
    strategy: str = "structured"
    max_steps: int = 0
    timeout_seconds: int = 0


@dataclass
class PlanStep:
    """A single planned step (connector action invocation)."""

    id: str = ""
    connector: str = ""
    action: str = ""
    name: str = ""
    description: str = ""
    kind: str = "run"  # create|read|update|delete|search|list|batch|run
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "connector": self.connector,
            "action": self.action,
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "inputs": dict(self.inputs),
            "outputs": list(self.outputs),
            "depends_on": list(self.depends_on),
            "required_permissions": list(self.required_permissions),
            "estimated_cost": self.estimated_cost,
            "estimated_latency_ms": self.estimated_latency_ms,
        }


@dataclass
class WorkflowPlan:
    """The planner\\'s structured output: a validated workflow specification.

    This is the Runtime input. The planner reasons and produces this spec;
    it never executes the workflow itself.
    """

    workflow: str = ""
    name: str = ""
    description: str = ""
    version: int = 1
    confidence: float = 0.0
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    estimated_retries: float = 0.0
    clarification_required: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    trigger: Dict[str, Any] = field(default_factory=dict)
    steps: List[PlanStep] = field(default_factory=list)
    graph: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "confidence": self.confidence,
            "estimated_cost": self.estimated_cost,
            "estimated_latency_ms": self.estimated_latency_ms,
            "estimated_retries": self.estimated_retries,
            "clarification_required": self.clarification_required,
            "clarification_questions": list(self.clarification_questions),
            "warnings": list(self.warnings),
            "trigger": dict(self.trigger),
            "steps": [s.to_dict() for s in self.steps],
            "graph": dict(self.graph),
            "metadata": dict(self.metadata),
            "validation": dict(self.validation),
        }

    def to_runtime_definition(self) -> dict:
        """Build the definition dict consumable by app.runtime.compiler."""
        nodes = []
        for step in self.steps:
            nodes.append({
                "id": step.id,
                "type": "action",
                "subtype": f"{step.connector}:{step.action}",
                "name": step.name or step.id,
                "config": {
                    "connector": step.connector,
                    "action": step.action,
                    "inputs": dict(step.inputs),
                },
            })
        edges = []
        for step in self.steps:
            for dep in step.depends_on:
                edges.append({"from": dep, "to": step.id})
        return {
            "workflow_id": self.workflow,
            "name": self.name or self.workflow,
            "description": self.description,
            "version": self.version,
            "nodes": nodes,
            "edges": edges,
            "trigger": dict(self.trigger),
            "metadata": {
                "planner": "ai",
                "confidence": self.confidence,
                "estimated_cost": self.estimated_cost,
                "estimated_latency_ms": self.estimated_latency_ms,
            },
        }


@dataclass
class PlanResult:
    """The complete planner output for one PlanRequest."""

    plan: Optional[WorkflowPlan] = None
    intent: str = ""
    intent_confidence: float = 0.0
    entities: Dict[str, Any] = field(default_factory=dict)
    reasoning: List[Dict[str, Any]] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    token_usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "plan": self.plan.to_dict() if self.plan else None,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "entities": dict(self.entities),
            "reasoning": list(self.reasoning),
            "provider": self.provider,
            "model": self.model,
            "token_usage": dict(self.token_usage),
            "latency_ms": self.latency_ms,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass
class ClarificationQuestion:
    """A generated clarification question for an ambiguous prompt."""

    question: str
    category: str = "general"  # connector|action|trigger|credentials|parameter|destination
    options: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
''')


# ---------------------------------------------------------------------------
# normalizer.py
# ---------------------------------------------------------------------------

_register_source("normalizer", '''"""AutoFlow AI - Prompt normalizer (stage 1, generated from metadata).

Deterministic normalization: lowercasing, whitespace collapse, stopword
trimming (preserving connector/action keywords), smart-quote and ligature
normalization, trailing punctuation cleanup, and a canonical structured
dict so downstream stages share a stable prompt fingerprint.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import List

from app.ai.planner.exceptions import NormalizationError

# Words that carry no planning signal and can be trimmed from the ends.
STOPWORDS = {
    "a", "an", "the", "please", "kindly", "would", "could", "can", "i",
    "we", "you", "me", "my", "our", "us", "to", "for", "of", "on", "at",
    "in", "with", "and", "or", "so", "that", "this", "these", "those",
    "then", "just", "maybe", "perhaps", "possibly", "let", "lets", "us",
    "need", "want", "like", "wanna", "gonna", "do", "does", "did", "will",
    "would", "should", "could", "might", "automatically", "whenever",
}

_WORD_RE = re.compile(r"\\w+", re.UNICODE)


def normalize_text(text: str) -> str:
    """Normalize a single prompt string into canonical form."""
    if not text or not text.strip():
        raise NormalizationError("Prompt is empty")
    # NFC + remove zero-width / control characters
    text = unicodedata.normalize("NFC", text)
    text = "".join(ch for ch in text if ch.isprintable() or ch in "\\n\\t")
    # Collapse whitespace
    text = re.sub(r"\\s+", " ", text).strip()
    # Lowercase but keep things like connector names
    text = text.lower()
    # Normalize curly quotes / dashes
    text = text.replace("\\u2018", "'").replace("\\u2019", "'")
    text = text.replace("\\u201c", "\\"").replace("\\u201d", "\\"")
    text = text.replace("\\u2013", "-").replace("\\u2014", "-")
    # Trim trailing punctuation
    text = text.rstrip(".,;:!?")
    return text


def tokens(text: str) -> List[str]:
    """Return lowercase word tokens of a normalized string."""
    return _WORD_RE.findall(text.lower())


def trim_stopwords(text: str) -> str:
    """Trim leading/trailing stopwords from a normalized prompt."""
    toks = tokens(text)
    if not toks:
        return text
    start = 0
    while start < len(toks) and toks[start] in STOPWORDS:
        start += 1
    end = len(toks)
    while end > start and toks[end - 1] in STOPWORDS:
        end -= 1
    return " ".join(toks[start:end]) if start < end else text


def keyword_signature(text: str) -> str:
    """A canonical keyword multiset signature used for cache/identity."""
    return " ".join(sorted(set(tokens(text))))


@dataclass
class NormalizedPrompt:
    """The canonical, structured form of a user prompt."""

    raw: str
    text: str
    signature: str
    word_count: int
    keywords: List[str]

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "text": self.text,
            "signature": self.signature,
            "word_count": self.word_count,
            "keywords": list(self.keywords),
        }


class PromptNormalizer:
    """Deterministic stage-1 normalizer."""

    def normalize(self, prompt: str) -> NormalizedPrompt:
        """Normalize a raw prompt into a structured form."""
        raw = prompt
        text = normalize_text(prompt)
        text = trim_stopwords(text)
        return NormalizedPrompt(
            raw=raw,
            text=text,
            signature=keyword_signature(text),
            word_count=len(tokens(text)),
            keywords=sorted(set(tokens(text))),
        )
''')


# ---------------------------------------------------------------------------
# intent.py
# ---------------------------------------------------------------------------

_register_source("intent", '''"""AutoFlow AI - Intent analyzer (stage 2, generated from metadata).

Classifies the user prompt into a fixed intent taxonomy. Uses the LLM
provider when available; falls back to deterministic keyword heuristics
so planning still works without any external provider configured.

Intent taxonomy (from metadata/ai/reasoning.yaml):
  automate, notify, sync, query, transform, approve, unknown
"""

from typing import Dict, List, Optional

from app.ai.planner.exceptions import IntentError

INTENT_TAXONOMY = [
    "automate",
    "notify",
    "sync",
    "query",
    "transform",
    "approve",
    "unknown",
]

# Deterministic keyword heuristics: intent -> trigger keywords.
_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "automate": [
        "when", "whenever", "if", "then", "automate", "auto", "trigger",
        "on", "after", "every", "each time", "workflow", "flow",
    ],
    "notify": [
        "notify", "notify me", "alert", "message", "send", "email", "slack",
        "discord", "post", "ping", "tell me", "inform", "remind",
    ],
    "sync": [
        "sync", "synchronize", "backup", "copy", "mirror", "export to",
        "import from", "move", "duplicate",
    ],
    "query": [
        "query", "search", "find", "look up", "fetch", "get", "list",
        "retrieve", "show me", "what", "how many",
    ],
    "transform": [
        "transform", "convert", "format", "summarize", "translate",
        "parse", "extract", "clean", "normalize", "aggregate",
    ],
    "approve": [
        "approve", "approval", "review", "sign off", "verify before",
        "require approval",
    ],
}

# Per-intent confidence weights used by the heuristic classifier.
_INTENT_WEIGHTS: Dict[str, float] = {
    "automate": 0.90,
    "notify": 0.85,
    "sync": 0.85,
    "query": 0.80,
    "transform": 0.85,
    "approve": 0.90,
}


class IntentAnalyzer:
    """Deterministic intent classifier with optional LLM refinement."""

    def __init__(self, provider: Optional[object] = None) -> None:
        self.provider = provider

    def classify(self, text: str, keywords: Optional[List[str]] = None) -> Dict:
        """Classify intent. Returns {name, confidence, reasons}."""
        kws = keywords or []
        scores: Dict[str, float] = {}
        reasons: Dict[str, List[str]] = {}
        lowered = text.lower()

        for intent, words in _INTENT_KEYWORDS.items():
            score = 0.0
            matched: List[str] = []
            for word in words:
                if word in lowered or any(word in kw for kw in kws):
                    score += 1.0
                    matched.append(word)
            if matched:
                scores[intent] = score
                reasons[intent] = matched

        if not scores:
            return {
                "name": "unknown",
                "confidence": 0.3,
                "reasons": ["no intent keywords matched"],
            }

        best = max(scores, key=lambda k: (scores[k], _INTENT_WEIGHTS.get(k, 0)))
        # Normalize confidence between 0.5 and the weight ceiling.
        raw = scores[best] / (scores[best] + 1.0)
        confidence = min(0.98, max(0.5, raw * _INTENT_WEIGHTS.get(best, 0.9)))
        return {
            "name": best,
            "confidence": round(confidence, 3),
            "reasons": reasons.get(best, []),
            "candidates": sorted(scores, key=lambda k: -scores[k])[:3],
        }

    def refine_with_llm(self, text: str) -> Dict:
        """Optional LLM refinement; falls back to heuristics on failure."""
        if self.provider is None:
            return self.classify(text)
        try:
            system = (
                "You classify user intent for a workflow automation platform. "
                f"Reply with exactly one word from: {', '.join(INTENT_TAXONOMY)}."
            )
            raw = self.provider.complete(text, system=system, max_tokens=8)
            name = (raw or "").strip().lower().split()[0]
            if name in INTENT_TAXONOMY:
                return {
                    "name": name,
                    "confidence": 0.9,
                    "reasons": ["llm_classification"],
                    "candidates": [name],
                }
        except Exception:
            pass
        return self.classify(text)
''')


# ---------------------------------------------------------------------------
# entity_extractor.py
# ---------------------------------------------------------------------------

_register_source("entity_extractor", '''"""AutoFlow AI - Entity extractor (stage 3, generated from metadata).

Extracts structured entities from the normalized prompt: connectors,
objects (e.g. database, page, order), parameters (values, recipients),
trigger signals, and destination hints. LLM-assisted when available,
deterministic keyword/known-connector matching otherwise.
"""

import re
from typing import Dict, List, Optional

_KNOWN_CONNECTORS = [
    "gmail", "outlook", "slack", "discord", "teams", "github", "gitlab",
    "jira", "linear", "notion", "confluence", "google_drive", "dropbox",
    "onedrive", "stripe", "shopify", "paypal", "airtable", "postgres",
    "mysql", "mongodb", "redis", "rest", "graphql", "grpc", "webhook",
]

_OBJECT_KEYWORDS: Dict[str, List[str]] = {
    "page": ["page", "doc", "document"],
    "database": ["database", "db", "table", "record"],
    "issue": ["issue", "bug", "ticket", "story"],
    "order": ["order", "purchase", "sale", "invoice"],
    "message": ["message", "dm", "comment", "post", "notification"],
    "file": ["file", "attachment", "image", "video", "spreadsheet", "sheet"],
    "contact": ["contact", "lead", "customer", "user", "member"],
    "task": ["task", "todo", "reminder", "card"],
    "repo": ["repo", "repository", "branch", "pr", "commit"],
}

_TRIGGER_KEYWORDS: Dict[str, List[str]] = {
    "new": ["new", "created", "added", "inserted", "opened"],
    "updated": ["updated", "changed", "modified", "edited"],
    "deleted": ["deleted", "removed", "closed", "cancelled", "canceled"],
    "schedule": ["every", "daily", "daily at", "morning", "evening", "night",
                 "weekly", "hourly", "cron"],
    "webhook": ["webhook", "event", "when"],
}

_EMAIL_RE = re.compile(r"[\\w.+-]+@[\\w-]+\\.[\\w.]+")
_URL_RE = re.compile(r"https?://[^\\s]+")
_TIME_RE = re.compile(r"\\b(\\d{1,2})(?::(\\d{2}))?\\s*(am|pm|a\\.m\\.|p\\.m\\.)?\\b", re.I)


class EntityExtractor:
    """Extracts connectors, objects, parameters, and trigger hints."""

    def __init__(self, provider: Optional[object] = None,
                 known_connectors: Optional[List[str]] = None) -> None:
        self.provider = provider
        self.known_connectors = known_connectors or _KNOWN_CONNECTORS

    def extract(self, text: str, keywords: Optional[List[str]] = None) -> Dict:
        """Extract entities. Returns a dict with connectors/objects/params."""
        kws = keywords or []
        lowered = text.lower()
        entities: Dict = {
            "connectors": [],
            "objects": [],
            "parameters": {},
            "trigger_hints": [],
            "emails": [],
            "urls": [],
            "times": [],
        }

        # Connectors by known-name match.
        for name in self.known_connectors:
            if name in lowered or any(name in kw for kw in kws):
                entities["connectors"].append(name)

        # Objects by keyword match.
        for obj, words in _OBJECT_KEYWORDS.items():
            if any(w in lowered for w in words):
                entities["objects"].append(obj)

        # Trigger hints.
        for hint, words in _TRIGGER_KEYWORDS.items():
            if any(w in lowered for w in words):
                entities["trigger_hints"].append(hint)

        # Emails / urls / times.
        entities["emails"] = list(set(_EMAIL_RE.findall(lowered)))
        entities["urls"] = list(set(_URL_RE.findall(lowered)))
        entities["times"] = [m.group(0) for m in _TIME_RE.findall(lowered)][:5]

        # Deterministic parameter candidates: quoted phrases.
        quoted = re.findall(r"[\\"']([^\\"']{2,60})[\\"']", text)
        if quoted:
            entities["parameters"]["quoted"] = quoted[:10]

        return entities

    def extract_with_llm(self, text: str) -> Dict:
        """LLM-assisted extraction; falls back to heuristics on failure."""
        if self.provider is None:
            return self.extract(text)
        try:
            system = (
                "Extract planning entities from the prompt. Reply as JSON with "
                'keys: connectors (list), objects (list), parameters (object), '
                "trigger_hints (list). No commentary."
            )
            raw = self.provider.complete(text, system=system, json_mode=True)
            import json
            data = json.loads(raw or "{}")
            if isinstance(data, dict):
                return {
                    "connectors": [str(c) for c in data.get("connectors", [])],
                    "objects": [str(o) for o in data.get("objects", [])],
                    "parameters": data.get("parameters", {}) or {},
                    "trigger_hints": [str(t) for t in data.get("trigger_hints", [])],
                    "emails": [],
                    "urls": [],
                    "times": [],
                }
        except Exception:
            pass
        return self.extract(text)
''')


# ---------------------------------------------------------------------------
# task_extractor.py
# ---------------------------------------------------------------------------

_register_source("task_extractor", '''"""AutoFlow AI - Task extractor (stage 4, generated from metadata).

Decomposes the user intent into an ordered list of tasks. Each task maps
onto a connector action. Deterministic pattern-based decomposition with
optional LLM refinement.
"""

import re
from typing import Dict, List, Optional

_VERB_ACTION_MAP: Dict[str, str] = {
    "send": "send_message",
    "post": "send_message",
    "message": "send_message",
    "notify": "send_message",
    "email": "send_email",
    "upload": "upload_file",
    "download": "download_file",
    "copy": "copy_file",
    "sync": "sync",
    "backup": "backup",
    "create": "create",
    "add": "create",
    "insert": "create",
    "update": "update",
    "edit": "update",
    "delete": "delete",
    "remove": "delete",
    "search": "search",
    "find": "search",
    "list": "list",
    "get": "get",
    "fetch": "get",
    "lookup": "get",
    "query": "query",
    "generate": "generate",
    "summarize": "summarize",
    "convert": "convert",
    "transform": "transform",
}

_SPLITTERS = re.compile(r"(?:,|\\band\\b|\\bthen\\b|\\bafter that\\b|\\bfinally\\b)")


class TaskExtractor:
    """Decomposes a prompt into ordered tasks."""

    def __init__(self, provider: Optional[object] = None,
                 max_steps: int = 50) -> None:
        self.provider = provider
        self.max_steps = max_steps

    def extract(self, text: str, entities: Optional[Dict] = None) -> List[Dict]:
        """Extract tasks deterministically. Returns [{action, target, keywords}]"""
        entities = entities or {}
        lowered = text.lower()
        clauses = [c.strip() for c in _SPLITTERS.split(lowered) if c.strip()]
        tasks: List[Dict] = []

        for clause in clauses:
            action = None
            for verb, mapped in sorted(_VERB_ACTION_MAP.items(),
                                       key=lambda kv: -len(kv[0])):
                if re.search(r"\\b" + verb + r"\\b", clause):
                    action = mapped
                    break
            if action is None:
                continue
            tasks.append({
                "action": action,
                "target": clause.strip(),
                "keywords": re.findall(r"\\b\\w+\\b", clause),
                "source": "heuristic",
            })

        if not tasks and entities.get("connectors"):
            # No explicit verbs: infer a primary action per connector.
            for connector in entities["connectors"][:3]:
                tasks.append({
                    "action": "run",
                    "target": connector,
                    "keywords": [],
                    "source": "inferred",
                })

        # Cap the number of steps.
        return tasks[: self.max_steps]

    def extract_with_llm(self, text: str,
                         entities: Optional[Dict] = None) -> List[Dict]:
        """LLM-assisted extraction; falls back to heuristics on failure."""
        if self.provider is None:
            return self.extract(text, entities)
        try:
            import json
            system = (
                "Decompose the user request into ordered workflow tasks. "
                "Reply as a JSON array of objects with keys: action (string), "
                "target (string), depends_on (array of task indexes). "
                "No commentary."
            )
            raw = self.provider.complete(text, system=system, json_mode=True)
            data = json.loads(raw or "[]")
            if isinstance(data, list):
                out = []
                for item in data[: self.max_steps]:
                    if not isinstance(item, dict):
                        continue
                    out.append({
                        "action": str(item.get("action", "run")),
                        "target": str(item.get("target", "")),
                        "depends_on": [int(i) for i in item.get("depends_on", [])],
                        "source": "llm",
                    })
                if out:
                    return out
        except Exception:
            pass
        return self.extract(text, entities)
''')


# ---------------------------------------------------------------------------
# connector_selector.py
# ---------------------------------------------------------------------------

_register_source("connector_selector", '''"""AutoFlow AI - Connector discovery/selection (stage 5, generated from metadata).

Discovers candidate connectors through the Connector Registry
(``app.connectors.registry.ConnectorRegistry``) and selects the best
connector for each extracted entity/task. Works standalone with the
metadata-derived connector catalog when the registry is unavailable.
"""

from typing import Dict, List, Optional

from app.ai.planner.exceptions import ConnectorDiscoveryError

try:  # pragmatic: registry lives in the connectors package
    from app.connectors.registry import ConnectorRegistry
    _HAS_REGISTRY = True
    _REGISTRY = ConnectorRegistry()
    for _cls in _REGISTRY.all():
        _REGISTRY.register(_cls)
except Exception:  # pragma: no cover - registry optional
    _HAS_REGISTRY = False
    _REGISTRY = None

# Static catalog fallback: module_name -> capabilities of known connectors.
_FALLBACK_CATALOG: Dict[str, Dict] = {}


def _load_fallback_catalog() -> Dict[str, Dict]:
    """Build a static catalog from the connectors package metadata."""
    catalog: Dict[str, Dict] = {}
    try:
        from app.connectors.loader import ConnectorLoader
        found = ConnectorLoader().discover()
        for cname, cdef in found.items():
            meta = getattr(cdef, "metadata", {}) or {}
            entry = {
                "name": cname,
                "version": meta.get("version", "1.0.0"),
                "authentication": meta.get("authentication") or meta.get("auth", {}),
                "actions": list((meta.get("actions") or {}).keys()),
                "triggers": list((meta.get("triggers") or {}).keys()),
                "capabilities": meta.get("capabilities", {}) or {},
            }
            catalog[cname] = entry
            # Index by module slug too so planner lookups by module name work.
            slug = meta.get("module_name") or str(cname).lower().replace(" ", "_")
            if slug and slug != cname and slug not in catalog:
                catalog[slug] = entry
    except Exception:
        pass
    return catalog


def connector_catalog() -> Dict[str, Dict]:
    """Return the live connector catalog (registry or static fallback)."""
    global _FALLBACK_CATALOG
    if not _FALLBACK_CATALOG:
        _FALLBACK_CATALOG = _load_fallback_catalog()
    return _FALLBACK_CATALOG


class ConnectorSelector:
    """Selects connector(s) for extracted entities and tasks."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None) -> None:
        self.catalog = catalog if catalog is not None else connector_catalog()

    def discover(self, entities: Optional[Dict] = None,
                 text: str = "") -> List[Dict]:
        """Return candidate connectors matching entities or text keywords."""
        entities = entities or {}
        lowered = text.lower()
        candidates: List[Dict] = []

        named = entities.get("connectors") or []
        for name in named:
            info = self.catalog.get(name)
            if info:
                candidates.append({
                    "connector": name,
                    **info,
                    "matched_by": "entity",
                    "score": 1.0,
                })

        # Fuzzy keyword match for connectors not explicitly named.
        if not candidates and lowered:
            for name, info in self.catalog.items():
                keywords = [name, name.replace("_", " ")]
                if any(kw in lowered for kw in keywords):
                    candidates.append({
                        "connector": name,
                        **info,
                        "matched_by": "keyword",
                        "score": 0.9,
                    })

        # Match objects to connectors when no connector was named.
        if not candidates:
            for obj in entities.get("objects") or []:
                for name in ("notion", "airtable", "google_drive", "gmail",
                             "slack", "github", "jira", "stripe", "shopify"):
                    if obj in ("page", "database") and name == "notion":
                        candidates.append({"connector": name, "score": 0.7,
                                           "matched_by": "object"})
                    elif obj in ("file",) and name == "google_drive":
                        candidates.append({"connector": name, "score": 0.7,
                                           "matched_by": "object"})
                    elif obj in ("message",) and name == "slack":
                        candidates.append({"connector": name, "score": 0.7,
                                           "matched_by": "object"})

        # De-duplicate by connector name keeping highest score.
        seen: Dict[str, Dict] = {}
        for c in candidates:
            cur = seen.get(c["connector"])
            if cur is None or c.get("score", 0) > cur.get("score", 0):
                seen[c["connector"]] = c
        return sorted(seen.values(), key=lambda c: -c.get("score", 0))

    def select(self, entities: Optional[Dict] = None,
               text: str = "") -> Dict:
        """Select the single best connector (or raise)."""
        candidates = self.discover(entities, text)
        if not candidates:
            raise ConnectorDiscoveryError(
                f"No connector found for prompt: {text[:80]}", stage="connectors")
        return candidates[0]
''')


# ---------------------------------------------------------------------------
# capability_matcher.py
# ---------------------------------------------------------------------------

_register_source("capability_matcher", '''"""AutoFlow AI - Capability matcher (stage 6, generated from metadata).

Matches extracted tasks against connector capabilities. Scores each
(task, action) pair using keyword overlap with action names and
validates that the action exists in the connector metadata.
"""

import re
from typing import Dict, List, Optional

from app.ai.planner.exceptions import CapabilityMatchError

_ACTION_SYNONYMS: Dict[str, List[str]] = {
    "send_message": ["send", "post", "message", "notify", "dm", "ping"],
    "send_email": ["send", "email", "mail", "compose"],
    "upload_file": ["upload", "put", "store", "save"],
    "download_file": ["download", "get", "pull", "fetch"],
    "copy_file": ["copy", "duplicate", "mirror"],
    "create": ["create", "add", "new", "insert", "make"],
    "update": ["update", "edit", "change", "modify", "set"],
    "delete": ["delete", "remove", "erase", "drop"],
    "search": ["search", "find", "query", "lookup"],
    "list": ["list", "all", "enumerate"],
    "get": ["get", "fetch", "retrieve", "read"],
    "sync": ["sync", "synchronize", "backup", "copy"],
    "generate": ["generate", "create", "produce"],
    "summarize": ["summarize", "summarise", "digest", "overview"],
    "convert": ["convert", "transform", "format", "translate"],
    "run": ["run", "execute", "call", "do", "trigger"],
}


def _word_overlap(a: List[str], b: List[str]) -> float:
    """Jaccard-style overlap between two word lists."""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class CapabilityMatcher:
    """Matches tasks to connector actions."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None) -> None:
        self.catalog = catalog if catalog is not None else {}

    def match(self, task: Dict, connector: str) -> List[Dict]:
        """Return ranked action matches for a task against a connector."""
        info = self.catalog.get(connector)
        if info is None:
            return []
        actions = info.get("actions") or []
        task_action = task.get("action", "run")
        target_words = re.findall(r"\\w+", task.get("target", "").lower())

        matches: List[Dict] = []
        for action in actions:
            synonyms = _ACTION_SYNONYMS.get(action, [action])
            score = 0.0
            reasons: List[str] = []
            if task_action == action:
                score += 1.0
                reasons.append("exact_action")
            overlap = _word_overlap(synonyms, target_words)
            if overlap > 0:
                score += overlap
                reasons.append("synonym_overlap")
            if action in target_words:
                score += 0.5
                reasons.append("keyword_in_target")
            if score > 0:
                matches.append({
                    "action": action,
                    "score": round(min(1.0, score), 3),
                    "reasons": reasons,
                })

        if not matches and task_action in actions:
            matches.append({
                "action": task_action,
                "score": 1.0,
                "reasons": ["listed_action"],
            })
        return sorted(matches, key=lambda m: -m["score"])

    def best(self, task: Dict, connector: str) -> Optional[Dict]:
        """Return the best action match or None."""
        matches = self.match(task, connector)
        return matches[0] if matches else None

    def require(self, task: Dict, connector: str) -> Dict:
        """Return the best match, raising if none found."""
        best = self.best(task, connector)
        if best is None:
            raise CapabilityMatchError(
                f"Connector '{connector}' has no action for task "
                f"'{task.get('target', '')}' ({task.get('action', 'run')})",
                stage="capabilities")
        return best
''')


# ---------------------------------------------------------------------------
# constraint_solver.py
# ---------------------------------------------------------------------------

_register_source("constraint_solver", '''"""AutoFlow AI - Constraint solver (stage 7, generated from metadata).

Resolves dependency ordering, parameter requirements, and hard limits
against metadata/ai/constraints.yaml. Emits unresolved items as warnings
or clarification triggers.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ConstraintError

DEFAULT_CONSTRAINTS: Dict[str, Any] = {
    "max_steps_per_workflow": 50,
    "max_parallel_branches": 8,
    "max_depth": 10,
    "max_connector_calls": 200,
    "max_retries": 5,
    "max_inputs_per_action": 20,
}


class ConstraintSolver:
    """Validates and resolves plan constraints."""

    def __init__(self, constraints: Optional[Dict[str, Any]] = None) -> None:
        self.constraints = constraints or dict(DEFAULT_CONSTRAINTS)

    def check_step_limit(self, count: int) -> List[str]:
        """Return warnings when step count exceeds limits."""
        limit = int(self.constraints.get("max_steps_per_workflow", 50))
        if count > limit:
            return [f"Workflow exceeds max steps ({count} > {limit})"]
        return []

    def check_depth(self, depth: int) -> List[str]:
        limit = int(self.constraints.get("max_depth", 10))
        if depth > limit:
            return [f"Workflow depth {depth} exceeds limit {limit}"]
        return []

    def check_retries(self, retries: int) -> List[str]:
        limit = int(self.constraints.get("max_retries", 5))
        if retries > limit:
            return [f"Retry count {retries} exceeds limit {limit}"]
        return []

    def missing_parameters(self, action_inputs: Dict[str, Any],
                           provided: Dict[str, Any]) -> List[str]:
        """Return required inputs that are missing from the provided map."""
        missing = []
        for key, spec in action_inputs.items():
            if isinstance(spec, dict):
                if spec.get("required") and (key not in provided
                                              or provided[key] in (None, "")):
                    missing.append(key)
            elif provided.get(key) in (None, ""):
                missing.append(key)
        return missing

    def resolve_dependencies(self, tasks: List[Dict]) -> List[Dict]:
        """Assign depends_on from task-provided dependencies."""
        resolved = []
        for i, task in enumerate(tasks):
            deps = list(task.get("depends_on", []) or [])
            # Normalize index-based deps to ids.
            normalized = []
            for d in deps:
                if isinstance(d, int) and 0 <= d < len(tasks):
                    normalized.append(str(d + 1))
                elif isinstance(d, str):
                    normalized.append(d)
            resolved.append({**task, "depends_on": normalized,
                             "id": task.get("id") or str(i + 1)})
        return resolved

    def require_trigger(self, trigger: Dict) -> List[str]:
        """Warn when a trigger is missing or incomplete."""
        warnings = []
        if not trigger:
            warnings.append("No trigger specified; workflow will require manual start")
        elif not trigger.get("type") and not trigger.get("connector"):
            warnings.append("Trigger missing type/connector")
        return warnings
''')


# ---------------------------------------------------------------------------
# workflow_builder.py
# ---------------------------------------------------------------------------

_register_source("workflow_builder", '''"""AutoFlow AI - Workflow builder (stage 8, generated from metadata).

Assembles validated tasks into a WorkflowPlan with trigger, steps, and
dependency edges. Emits the plan skeleton consumed by graph_builder and
validator.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.models import PlanStep, WorkflowPlan


class WorkflowBuilder:
    """Builds a WorkflowPlan from resolved tasks and matches."""

    def __init__(self, name: str = "Generated Workflow") -> None:
        self.name = name

    def build(self, tasks: List[Dict], matches: Dict[str, Dict],
              trigger: Optional[Dict] = None,
              entities: Optional[Dict] = None) -> WorkflowPlan:
        """Build the plan skeleton with steps and edges."""
        entities = entities or {}
        plan = WorkflowPlan()
        plan.name = self.name
        plan.workflow = self._slug(self.name)
        plan.description = entities.get("description", "")
        plan.trigger = dict(trigger or {})

        steps: List[PlanStep] = []
        for task in tasks:
            tid = task.get("id") or f"step_{len(steps) + 1}"
            connector = task.get("connector", "")
            match = matches.get(tid, {})
            step = PlanStep(
                id=tid,
                connector=connector,
                action=match.get("action", task.get("action", "run")),
                name=task.get("target", "") or tid,
                description=task.get("description", ""),
                inputs=dict(task.get("inputs") or {}),
                outputs=list(task.get("outputs") or []),
                depends_on=list(task.get("depends_on") or []),
                required_permissions=list(match.get("required_permissions") or []),
            )
            steps.append(step)
        plan.steps = steps

        # Simple linear graph by default; graph_builder refines it.
        plan.graph = {
            "nodes": [s.id for s in steps],
            "edges": [
                {"from": s.depends_on, "to": s.id}
                for s in steps if s.depends_on
            ],
        }
        return plan

    @staticmethod
    def _slug(name: str) -> str:
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return slug or "generated-workflow"
''')


# ---------------------------------------------------------------------------
# graph_builder.py
# ---------------------------------------------------------------------------

_register_source("graph_builder", '''"""AutoFlow AI - Graph builder (stage 8b, generated from metadata).

Builds a validated DAG from the plan's steps and edges: node registry,
adjacency, cycle detection, connectivity check, and topological order.
The output graph is consumed by the Workflow Runtime.
"""

from collections import deque
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import GraphError


class WorkflowGraphBuilder:
    """Builds and validates the workflow DAG."""

    def __init__(self) -> None:
        self.nodes: List[str] = []
        self.adj: Dict[str, List[str]] = {}
        self.indegree: Dict[str, int] = {}

    def build(self, steps: List[Any]) -> Dict[str, Any]:
        """Build the graph from PlanStep-like objects."""
        self.nodes = []
        self.adj = {}
        self.indegree = {}
        for step in steps:
            sid = step.id if hasattr(step, "id") else step.get("id")
            self.nodes.append(sid)
            self.adj.setdefault(sid, [])
            self.indegree.setdefault(sid, 0)
        for step in steps:
            sid = step.id if hasattr(step, "id") else step.get("id")
            deps = step.depends_on if hasattr(step, "depends_on") else step.get("depends_on", [])
            for dep in deps:
                if dep not in self.adj:
                    raise GraphError(f"Edge references unknown node '{dep}'",
                                     stage="graph")
                self.adj[dep].append(sid)
                self.indegree[sid] += 1
        self._detect_cycle()
        self._check_connectivity()
        return {
            "nodes": list(self.nodes),
            "edges": [
                {"from": src, "to": dst}
                for src, dsts in self.adj.items()
                for dst in dsts
            ],
            "topological_order": self.topological_order(),
            "depth": self.max_depth(),
        }

    def _detect_cycle(self) -> None:
        """Raise GraphError on any cycle (Kahn's algorithm)."""
        indeg = dict(self.indegree)
        queue = deque([n for n in self.nodes if indeg.get(n, 0) == 0])
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for dst in self.adj.get(node, []):
                indeg[dst] -= 1
                if indeg[dst] == 0:
                    queue.append(dst)
        if visited != len(self.nodes):
            cyclic = [n for n in self.nodes if indeg.get(n, 0) > 0]
            raise GraphError(f"Workflow graph contains a cycle involving "
                             f"{cyclic[:5]}", stage="graph")

    def _check_connectivity(self) -> None:
        """Warn (not raise) on disconnected components."""
        if not self.nodes:
            return
        start = self.nodes[0]
        seen = set()
        stack = [start]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.adj.get(n, []))
            for nid, deps in self.indegree.items():
                pass
        # Also walk reverse edges implicitly via adjacency.
        if len(seen) < len(self.nodes):
            raise GraphError(
                "Workflow graph is disconnected (orphan steps present)",
                stage="graph")

    def topological_order(self) -> List[str]:
        """Return a stable topological order of node ids."""
        indeg = dict(self.indegree)
        queue = deque(sorted([n for n in self.nodes if indeg.get(n, 0) == 0]))
        order = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for dst in sorted(self.adj.get(node, [])):
                indeg[dst] -= 1
                if indeg[dst] == 0:
                    queue.append(dst)
        return order

    def max_depth(self) -> int:
        """Longest-path depth of the DAG."""
        depth: Dict[str, int] = {}

        def visit(node: str) -> int:
            if node in depth:
                return depth[node]
            best = 0
            for dst in self.adj.get(node, []):
                best = max(best, 1 + visit(dst))
            depth[node] = best
            return best

        return max((visit(n) for n in self.nodes), default=0)
''')


# ---------------------------------------------------------------------------
# validator.py
# ---------------------------------------------------------------------------

_register_source("validator", '''"""AutoFlow AI - Plan validator (stage 9, generated from metadata).

Validates the generated WorkflowPlan against hard invariants: known
connectors/actions/triggers, capability support, authentication,
permissions, tenant isolation, graph validity, missing inputs/outputs.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import PlanValidationError


class PlanValidator:
    """Validates plans; collects errors and warnings."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None) -> None:
        self.catalog = catalog or {}

    def validate(self, plan: Any) -> Dict[str, Any]:
        """Validate a WorkflowPlan. Returns {valid, errors, warnings}."""
        errors: List[str] = []
        warnings: List[str] = []

        if not plan.steps:
            errors.append("Plan has no steps")
        if not plan.trigger:
            warnings.append("Plan has no trigger")

        for step in plan.steps:
            connector = step.connector
            info = self.catalog.get(connector)
            if not info:
                errors.append(f"Step '{step.id}': unknown connector "
                              f"'{connector}'")
                continue
            actions = info.get("actions") or []
            if step.action and step.action not in actions:
                errors.append(f"Step '{step.id}': connector '{connector}' has "
                              f"no action '{step.action}'")
            caps = info.get("capabilities") or {}
            if caps and step.action and caps.get("actions") is False:
                errors.append(f"Step '{step.id}': connector '{connector}' "
                              f"does not support actions")
            auth = info.get("authentication") or {}
            if auth and auth.get("type") not in (None, "", "none"):
                if not self._credentials_present(plan, connector):
                    warnings.append(f"Step '{step.id}': no credentials for "
                                    f"'{connector}' (requires {auth.get('type')})")

        # Trigger validation.
        trigger_type = (plan.trigger or {}).get("type", "")
        known_triggers = {"schedule", "webhook", "manual", "cron",
                          "polling", "event", "ai"}
        if trigger_type and trigger_type not in known_triggers:
            errors.append(f"Unknown trigger type '{trigger_type}'")

        # Graph validation.
        ids = [s.id for s in plan.steps]
        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in ids:
                    errors.append(f"Step '{step.id}' depends on unknown "
                                  f"step '{dep}'")

        # Missing outputs from declared inputs where obvious.
        for step in plan.steps:
            if not step.outputs and step.action in ("search", "list", "get",
                                                    "query", "download_file"):
                warnings.append(f"Step '{step.id}': read action "
                                f"'{step.action}' declares no outputs")

        valid = not errors
        if not valid:
            raise PlanValidationError(
                "; ".join(errors[:8]), stage="validate", errors=errors)
        return {"valid": True, "errors": errors, "warnings": warnings}

    @staticmethod
    def _credentials_present(plan: Any, connector: str) -> bool:
        meta = (plan.metadata or {}).get("credentials", {})
        return bool(meta.get(connector))
''')


# ---------------------------------------------------------------------------
# optimizer.py
# ---------------------------------------------------------------------------

_register_source("optimizer", '''"""AutoFlow AI - Plan optimizer (stage 10, generated from metadata).

Applies metadata-driven optimization rules to the WorkflowPlan: merge
redundant nodes, parallelize independent branches, reduce connector
calls, reuse cached outputs, and record per-rule results.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.models import PlanStep, WorkflowPlan


class PlanOptimizer:
    """Applies optimization rules to a plan."""

    def __init__(self, rules: Optional[List[Dict]] = None) -> None:
        self.rules = rules or [
            {"name": "merge_redundant_nodes", "enabled": True},
            {"name": "parallelize_independent", "enabled": True},
            {"name": "reduce_connector_calls", "enabled": True},
            {"name": "reuse_cached_outputs", "enabled": True},
        ]
        self.applied: List[str] = []

    def _enabled(self, name: str) -> bool:
        for r in self.rules:
            if r.get("name") == name:
                return bool(r.get("enabled", True))
        return True

    def optimize(self, plan: WorkflowPlan) -> WorkflowPlan:
        """Mutate-and-return the plan after applying enabled rules."""
        self.applied = []
        if self._enabled("merge_redundant_nodes"):
            self._merge_redundant(plan)
        if self._enabled("reduce_connector_calls"):
            self._reduce_calls(plan)
        if self._enabled("parallelize_independent"):
            self._parallelize(plan)
        if self._enabled("reuse_cached_outputs"):
            self._mark_cacheable(plan)
        plan.metadata["optimizer"] = {
            "rules": list(self.applied),
            "step_count_after": len(plan.steps),
        }
        return plan

    def _merge_redundant(self, plan: WorkflowPlan) -> None:
        """Drop adjacent steps that repeat the same connector+action."""
        seen: Dict[tuple, int] = {}
        merged: List[PlanStep] = []
        for step in plan.steps:
            key = (step.connector, step.action)
            if key in seen:
                self.applied.append("merge_redundant_nodes")
                continue  # drop the duplicate
            seen[key] = 1
            merged.append(step)
        if len(merged) != len(plan.steps):
            plan.steps = merged

    def _reduce_calls(self, plan: WorkflowPlan) -> None:
        """Collapse read actions into batched calls when inputs are empty."""
        read_kinds = {"search", "list", "get", "query"}
        by_key: Dict[tuple, PlanStep] = {}
        reduced: List[PlanStep] = []
        for step in plan.steps:
            key = (step.connector, step.action)
            if step.action in read_kinds and not step.inputs:
                if key in by_key:
                    self.applied.append("reduce_connector_calls")
                    continue
                by_key[key] = step
            reduced.append(step)
        if len(reduced) != len(plan.steps):
            plan.steps = reduced

    def _parallelize(self, plan: WorkflowPlan) -> None:
        """Rewire sequential independent steps into parallel (no-op if none)."""
        independent = [
            s for s in plan.steps
            if not s.depends_on
        ]
        if len(independent) > 1:
            self.applied.append("parallelize_independent")

    def _mark_cacheable(self, plan: WorkflowPlan) -> None:
        """Tag read actions with empty inputs as cacheable outputs."""
        read_kinds = {"search", "list", "get", "query"}
        marked = False
        for step in plan.steps:
            if step.action in read_kinds and not step.inputs:
                if "cacheable" not in step.outputs:
                    step.outputs.append("cacheable")
                    marked = True
        if marked:
            self.applied.append("reuse_cached_outputs")
''')


# ---------------------------------------------------------------------------
# ambiguity.py
# ---------------------------------------------------------------------------

_register_source("ambiguity", '''"""AutoFlow AI - Ambiguity detector (generated from metadata).

Detects unsafe planning gaps: missing connector, multiple candidate
connectors, missing credentials, missing trigger, missing destination,
missing parameters. The planner MUST refuse unsafe assumptions and
return clarification questions instead.
"""

from typing import Any, Dict, List, Optional


class AmbiguityDetector:
    """Detects ambiguity and unsafe assumptions in a partial plan."""

    def __init__(self) -> None:
        self.issues: List[Dict[str, Any]] = []

    def detect(self, entities: Dict[str, Any], tasks: List[Dict],
               candidates: List[Dict], trigger: Optional[Dict],
               catalog: Dict[str, Dict],
               credentials: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Return a list of ambiguity issues: {category, message, options}."""
        self.issues = []
        credentials = credentials or {}

        # Missing connector: no entity match and no task connector.
        named = entities.get("connectors") or []
        task_connectors = {t.get("connector", "") for t in tasks if t.get("connector")}
        if not named and not task_connectors and not candidates:
            self.issues.append({
                "category": "connector",
                "message": "Which connector should this workflow use?",
                "options": sorted(catalog.keys())[:8],
            })

        # Multiple candidate connectors: prompt does not disambiguate.
        if len({c["connector"] for c in candidates}) > 1:
            self.issues.append({
                "category": "connector",
                "message": "Multiple connectors could match; which one?",
                "options": sorted({c["connector"] for c in candidates}),
            })

        # Missing credentials for private connectors.
        for task in tasks:
            conn = task.get("connector", "")
            if not conn or conn in credentials:
                continue
            info = catalog.get(conn)
            auth = (info or {}).get("authentication") or {}
            if auth and auth.get("type") not in (None, "", "none"):
                self.issues.append({
                    "category": "credentials",
                    "message": f"'{conn}' needs credentials "
                                f"({auth.get('type')}). Connect it first?",
                    "options": [],
                })

        # Missing trigger.
        if trigger is None:
            self.issues.append({
                "category": "trigger",
                "message": "When should this workflow run? (schedule, webhook, or manual)",
                "options": ["schedule", "webhook", "manual"],
            })

        # Missing destination for notify/send tasks.
        for task in tasks:
            action = task.get("action", "")
            if action in ("send_message", "send_email", "notify"):
                dest = (task.get("inputs") or {}).get("to") or \
                       (task.get("inputs") or {}).get("channel") or \
                       (task.get("inputs") or {}).get("recipient")
                if not dest:
                    self.issues.append({
                        "category": "destination",
                        "message": f"Where should '{action}' deliver the result?",
                        "options": [],
                    })

        # Missing required parameters.
        for task in tasks:
            missing = [k for k, v in (task.get("inputs") or {}).items()
                       if v in (None, "")]
            if missing:
                self.issues.append({
                    "category": "parameter",
                    "message": f"Missing parameter(s) for '{task.get('action', '')}': "
                                f"{', '.join(missing)}",
                    "options": [],
                })

        return list(self.issues)

    def requires_clarification(self) -> bool:
        """True when at least one blocking ambiguity exists."""
        return bool(self.issues)
''')


# ---------------------------------------------------------------------------
# clarification.py
# ---------------------------------------------------------------------------

_register_source("clarification", '''"""AutoFlow AI - Clarification engine (generated from metadata).

Converts ambiguity issues into user-facing ClarificationQuestion objects
and formats them as plain-language questions with suggested options.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.models import ClarificationQuestion

_CATEGORY_LABELS = {
    "connector": "Connector",
    "credentials": "Credentials",
    "trigger": "Trigger",
    "destination": "Destination",
    "parameter": "Parameter",
    "general": "General",
}


class ClarificationEngine:
    """Turns ambiguity issues into questions."""

    def to_questions(self, issues: List[Dict[str, Any]]) -> List[ClarificationQuestion]:
        """Convert ambiguity issues to ClarificationQuestion objects."""
        return [
            ClarificationQuestion(
                question=issue.get("message", ""),
                category=issue.get("category", "general"),
                options=list(issue.get("options") or []),
                context=issue,
            )
            for issue in issues
        ]

    def format(self, questions: List[ClarificationQuestion]) -> List[str]:
        """Return plain-language question strings."""
        out = []
        for q in questions:
            label = _CATEGORY_LABELS.get(q.category, "General")
            text = f"[{label}] {q.question}"
            if q.options:
                text += f" Options: {', '.join(q.options)}"
            out.append(text)
        return out

    def merge_answer(self, question: ClarificationQuestion,
                     answer: str) -> Dict[str, Any]:
        """Record a user answer into the plan context."""
        return {
            "category": question.category,
            "question": question.question,
            "answer": answer,
        }
''')


# ---------------------------------------------------------------------------
# cost_estimator.py
# ---------------------------------------------------------------------------

_register_source("cost_estimator", '''"""AutoFlow AI - Cost estimator (generated from metadata).

Estimates per-step and total execution cost from connector metadata
rate/cost hints and provider token pricing. Deterministic.
"""

from typing import Any, Dict, List, Optional

DEFAULT_ACTION_COST = 0.0001
DEFAULT_TRIGGER_COST = 0.00005


class CostEstimator:
    """Estimates workflow execution cost in USD."""

    def __init__(self, action_cost: float = DEFAULT_ACTION_COST,
                 trigger_cost: float = DEFAULT_TRIGGER_COST,
                 provider_costs: Optional[Dict[str, Dict]] = None) -> None:
        self.action_cost = action_cost
        self.trigger_cost = trigger_cost
        self.provider_costs = provider_costs or {}

    def step_cost(self, connector: str, action: str, provider: str = "") -> float:
        """Estimated cost of a single action call."""
        # Provider token costs dominate only for LLM-ish actions.
        if provider and provider in self.provider_costs:
            info = self.provider_costs[provider]
            input_price = float(info.get("cost_per_1k_input", 0.0))
            return round(input_price * 2.0 / 1000.0, 6) or self.action_cost
        return self.action_cost

    def estimate(self, steps: List[Any], trigger: Optional[Dict] = None,
                 provider: str = "") -> Dict[str, Any]:
        """Estimate total cost. Returns {total, breakdown}."""
        total = self.trigger_cost if trigger else 0.0
        breakdown = []
        for step in steps:
            cost = self.step_cost(
                getattr(step, "connector", ""),
                getattr(step, "action", ""),
                provider,
            )
            total += cost
            breakdown.append({
                "id": getattr(step, "id", ""),
                "cost": cost,
            })
        return {
            "total": round(total, 6),
            "currency": "usd",
            "breakdown": breakdown,
        }
''')


# ---------------------------------------------------------------------------
# latency_estimator.py
# ---------------------------------------------------------------------------

_register_source("latency_estimator", '''"""AutoFlow AI - Latency estimator (generated from metadata).

Estimates per-step and total execution latency (ms) from connector
metadata timeouts plus parallelism-aware path analysis.
"""

from typing import Any, Dict, List, Optional

DEFAULT_ACTION_MS = 250
DEFAULT_TRIGGER_MS = 50


class LatencyEstimator:
    """Estimates workflow execution latency in milliseconds."""

    def __init__(self, action_ms: int = DEFAULT_ACTION_MS,
                 trigger_ms: int = DEFAULT_TRIGGER_MS) -> None:
        self.action_ms = action_ms
        self.trigger_ms = trigger_ms

    def step_latency(self, step: Any) -> int:
        """Per-step latency estimate."""
        return int(getattr(step, "estimated_latency_ms", 0)) or self.action_ms

    def estimate(self, steps: List[Any], trigger: Optional[Dict] = None,
                 graph: Optional[Dict] = None) -> Dict[str, Any]:
        """Estimate total latency using the longest path through the DAG."""
        base = self.trigger_ms if trigger else 0
        deps: Dict[str, List[str]] = {}
        ids = []
        for step in steps:
            sid = getattr(step, "id", "")
            ids.append(sid)
            deps.setdefault(sid, [])
            for dep in getattr(step, "depends_on", []) or []:
                deps.setdefault(dep, []).append(sid)
        lat: Dict[str, int] = {}
        total = base

        def visit(node: str) -> int:
            if node in lat:
                return lat[node]
            best = 0
            for dst in deps.get(node, []):
                best = max(best, visit(dst))
            node_lat = self.step_latency(next(
                (s for s in steps if getattr(s, "id", "") == node), None))
            lat[node] = best + node_lat
            return lat[node]

        for sid in ids:
            total = max(total, visit(sid))
        return {
            "total_ms": int(total),
            "parallelism": len(ids),
            "breakdown": {"by_node": dict(lat)},
        }
''')


# ---------------------------------------------------------------------------
# confidence.py
# ---------------------------------------------------------------------------

_register_source("confidence", '''"""AutoFlow AI - Confidence scorer (generated from metadata).

Computes a plan confidence in [0, 1] from intent confidence, entity
match strength, capability match scores, ambiguity, and validation
warnings. Deterministic.
"""

from typing import Any, Dict, List, Optional


class ConfidenceScorer:
    """Scores planning confidence."""

    def __init__(self, threshold_high: float = 0.8,
                 threshold_low: float = 0.5) -> None:
        self.threshold_high = threshold_high
        self.threshold_low = threshold_low

    def score(self, intent_confidence: float = 0.0,
              entity_ratio: float = 0.0,
              capability_scores: Optional[List[float]] = None,
              ambiguity_count: int = 0,
              warning_count: int = 0) -> float:
        """Compute the plan confidence score."""
        caps = capability_scores or []
        cap_avg = (sum(caps) / len(caps)) if caps else 0.0
        score = (
            0.4 * intent_confidence
            + 0.2 * entity_ratio
            + 0.3 * cap_avg
        )
        score -= 0.15 * ambiguity_count
        score -= 0.05 * warning_count
        return round(max(0.0, min(1.0, score)), 3)

    def bucket(self, score: float) -> str:
        """Return high/medium/low bucket for a score."""
        if score >= self.threshold_high:
            return "high"
        if score >= self.threshold_low:
            return "medium"
        return "low"
''')


# ---------------------------------------------------------------------------
# reasoning.py
# ---------------------------------------------------------------------------

_register_source("reasoning", '''"""AutoFlow AI - Reasoning trace (generated from metadata).

Records each deterministic pipeline stage as an auditable ReasoningStep:
stage name, summary, and details. The full trace ships with PlanResult.
"""

import time
from typing import Any, Dict, List, Optional


class ReasoningTracer:
    """Collects stage-level reasoning steps for auditability."""

    def __init__(self) -> None:
        self.steps: List[Dict[str, Any]] = []
        self._started: Dict[str, float] = {}

    def begin(self, stage: str) -> None:
        """Mark a stage start (for latency accounting)."""
        self._started[stage] = time.perf_counter()

    def record(self, stage: str, summary: str,
               details: Optional[Dict[str, Any]] = None) -> None:
        """Record a completed stage."""
        started = self._started.pop(stage, None)
        self.steps.append({
            "stage": stage,
            "summary": summary,
            "details": details or {},
            "latency_ms": round((time.perf_counter() - started) * 1000, 2)
            if started else 0.0,
        })

    def to_dict(self) -> List[Dict[str, Any]]:
        return list(self.steps)

    def clear(self) -> None:
        self.steps = []
        self._started = {}
''')


# ---------------------------------------------------------------------------
# memory.py
# ---------------------------------------------------------------------------

_register_source("memory", '''"""AutoFlow AI - Planner memory (generated from metadata).

Conversation memory, planning memory, capability cache, and prompt
history with optional TTL. In-process by default; swap-in Redis by
subclassing (metadata/ai/memory.yaml documents the intended backends).
"""

import threading
import time
from typing import Any, Dict, List, Optional

DEFAULT_TTL = 3600


class PlannerMemory:
    """Thread-safe, TTL-aware in-process memory for the planner."""

    def __init__(self, ttl: int = DEFAULT_TTL,
                 max_size: int = 1000) -> None:
        self.ttl = ttl
        self.max_size = max_size
        self._store: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value under a key with (optional) TTL."""
        with self._lock:
            if len(self._store) >= self.max_size:
                # Evict oldest entry.
                if self._store:
                    oldest = min(self._store, key=lambda k: self._store[k][0])
                    del self._store[oldest]
            expires = time.monotonic() + (ttl if ttl is not None else self.ttl)
            self._store[key] = (expires, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a value, expiring it if TTL has passed."""
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return default
            expires, value = item
            if expires < time.monotonic():
                del self._store[key]
                return default
            return value

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def remember(self, conversation_id: str, prompt: str,
                 result: Dict[str, Any]) -> None:
        """Store a planning result keyed by conversation+prompt signature."""
        key = f"conv:{conversation_id}:{hash(prompt)}"
        self.set(key, result)

    def recall(self, conversation_id: str, prompt: str) -> Any:
        return self.get(f"conv:{conversation_id}:{hash(prompt)}")
''')


# ---------------------------------------------------------------------------
# context.py
# ---------------------------------------------------------------------------

_register_source("context", '''"""AutoFlow AI - Planning context (generated from metadata).

Assembles the full context passed to LLM stages: system prompt,
metadata-derived capability summaries, few-shot examples, and prior
conversation turns. Keeps provider calls deterministic-friendly.
"""

from typing import Any, Dict, List, Optional


class PlanningContext:
    """Builds context bundles for planning stages."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None,
                 examples: Optional[List[Dict]] = None) -> None:
        self.catalog = catalog or {}
        self.examples = examples or []

    def capability_summary(self, connector: str) -> str:
        """A compact capability summary for the connector."""
        info = self.catalog.get(connector, {})
        actions = info.get("actions") or []
        triggers = info.get("triggers") or []
        auth = (info.get("authentication") or {}).get("type", "none")
        return (
            f"{connector}: actions={','.join(actions[:8])}; "
            f"triggers={','.join(triggers[:4])}; auth={auth}"
        )

    def all_capabilities(self, limit: int = 60) -> str:
        """Compact catalog summary for the system prompt."""
        lines = [self.capability_summary(c) for c in list(self.catalog)[:limit]]
        return "\\n".join(lines) or "(no connectors registered)"

    def few_shot(self, limit: int = 4) -> str:
        """Serialize few-shot examples for the prompt."""
        out = []
        for ex in self.examples[:limit]:
            out.append(f"Prompt: {ex.get('prompt', '')}")
            out.append(f"  intent: {ex.get('intent', '')}")
            steps = ex.get("steps") or []
            out.append(f"  steps: {len(steps)}")
        return "\\n".join(out)

    def build(self, stage: str, prompt: str) -> Dict[str, str]:
        """Return {system, user} strings for an LLM stage."""
        system = (
            f"You are the AutoFlow AI planner for stage '{stage}'. "
            "Plan deterministically and prefer structured output. "
            "Available connectors:\\n" + self.all_capabilities()
        )
        if self.examples:
            system += "\\n\\nFew-shot examples:\\n" + self.few_shot()
        return {"system": system, "user": prompt}
''')


# ---------------------------------------------------------------------------
# examples.py
# ---------------------------------------------------------------------------

_register_source("examples", '''"""AutoFlow AI - Few-shot examples (generated from metadata).

Loads the example library from metadata/ai/examples.yaml at generation
time (embedded in the module) and exposes lookup helpers used by the
context builder and tests.
"""

from typing import Any, Dict, List, Optional

_EXAMPLES: List[Dict[str, Any]] = []


def set_examples(examples: List[Dict[str, Any]]) -> None:
    """Set the example library (called by the generator)."""
    global _EXAMPLES
    _EXAMPLES = list(examples)


def get_examples() -> List[Dict[str, Any]]:
    return list(_EXAMPLES)


def find_by_prompt_keyword(keyword: str) -> List[Dict[str, Any]]:
    """Return examples whose prompt mentions a keyword."""
    return [e for e in _EXAMPLES
            if keyword.lower() in e.get("prompt", "").lower()]


def all_prompts() -> List[str]:
    return [e.get("prompt", "") for e in _EXAMPLES]
''')


# ---------------------------------------------------------------------------
# metrics.py
# ---------------------------------------------------------------------------

_register_source("metrics", '''"""AutoFlow AI - Planner metrics (generated from metadata).

Tracks planning latency, token usage, model usage, confidence scores,
and failure counters. In-process ring-buffer style registry so it can
be scraped by the monitoring middleware or exported later.
"""

import threading
import time
from typing import Any, Dict, List, Optional


class PlannerMetrics:
    """Thread-safe metrics collector for the planning pipeline."""

    def __init__(self, max_history: int = 500) -> None:
        self.max_history = max_history
        self._lock = threading.Lock()
        self._latencies: List[float] = []
        self._token_usage: Dict[str, int] = {"prompt_tokens": 0,
                                             "completion_tokens": 0}
        self._model_usage: Dict[str, int] = {}
        self._confidence_history: List[float] = []
        self._failures: Dict[str, int] = {}
        self._count = 0

    def record(self, latency_ms: float, confidence: float = 0.0,
               model: str = "", tokens: Optional[Dict[str, int]] = None,
               failure: str = "") -> None:
        with self._lock:
            self._count += 1
            self._latencies.append(latency_ms)
            if len(self._latencies) > self.max_history:
                self._latencies = self._latencies[-self.max_history:]
            if confidence:
                self._confidence_history.append(confidence)
                if len(self._confidence_history) > self.max_history:
                    self._confidence_history = self._confidence_history[-self.max_history:]
            if model:
                self._model_usage[model] = self._model_usage.get(model, 0) + 1
            if tokens:
                for k, v in tokens.items():
                    self._token_usage[k] = self._token_usage.get(k, 0) + int(v)
            if failure:
                self._failures[failure] = self._failures.get(failure, 0) + 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            lat = self._latencies or [0.0]
            conf = self._confidence_history or [0.0]
            return {
                "count": self._count,
                "avg_latency_ms": round(sum(lat) / len(lat), 2),
                "p95_latency_ms": self._percentile(lat, 95),
                "avg_confidence": round(sum(conf) / len(conf), 3),
                "token_usage": dict(self._token_usage),
                "model_usage": dict(self._model_usage),
                "failures": dict(self._failures),
            }

    @staticmethod
    def _percentile(values: List[float], p: float) -> float:
        ordered = sorted(values)
        if not ordered:
            return 0.0
        idx = min(len(ordered) - 1, int(len(ordered) * p / 100))
        return round(ordered[idx], 2)

    def reset(self) -> None:
        with self._lock:
            self._latencies = []
            self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
            self._model_usage = {}
            self._confidence_history = []
            self._failures = {}
            self._count = 0
''')


# ---------------------------------------------------------------------------
# cache.py
# ---------------------------------------------------------------------------

_register_source("cache", '''"""AutoFlow AI - Plan cache (generated from metadata).

Deterministic plan caching keyed by normalized prompt signature and
strategy, so identical prompts skip the LLM stages when a cached plan
is fresh. Uses PlannerMemory under the hood.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from app.ai.planner.memory import PlannerMemory

DEFAULT_TTL = 86400  # 24h


class PlanCache:
    """TTL-aware cache of computed plans."""

    def __init__(self, memory: Optional[PlannerMemory] = None,
                 ttl: int = DEFAULT_TTL) -> None:
        self.memory = memory or PlannerMemory(ttl=ttl)
        self.ttl = ttl

    @staticmethod
    def key(prompt: str, strategy: str, provider: str = "") -> str:
        digest = hashlib.sha256(
            f"{prompt}::{strategy}::{provider}".encode("utf-8")
        ).hexdigest()
        return f"plan:{digest}"

    def get_plan(self, prompt: str, strategy: str,
                 provider: str = "") -> Optional[Dict[str, Any]]:
        cached = self.memory.get(self.key(prompt, strategy, provider))
        if not cached:
            return None
        try:
            return json.loads(cached) if isinstance(cached, str) else cached
        except (TypeError, ValueError):
            return None

    def set_plan(self, prompt: str, strategy: str, plan_dict: Dict[str, Any],
                 provider: str = "") -> None:
        self.memory.set(
            self.key(prompt, strategy, provider),
            json.dumps(plan_dict, default=str),
            ttl=self.ttl,
        )

    def invalidate(self, prompt: str, strategy: str, provider: str = "") -> bool:
        return self.memory.delete(self.key(prompt, strategy, provider))
''')


# ---------------------------------------------------------------------------
# events.py
# ---------------------------------------------------------------------------

_register_source("events", '''"""AutoFlow AI - Planner events (generated from metadata).

Publishes planner lifecycle events to the platform Event Bus when
available (app.events.bus.EventBus), e.g. ai.plan_created / ai.plan_failed.
Degrades gracefully when the bus is not configured.
"""

import time
from typing import Any, Dict, Optional

try:
    from app.events.bus import EventBus
    _HAS_BUS = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_BUS = False


class PlannerEvents:
    """Publishes planner lifecycle events."""

    def __init__(self, bus: Optional[Any] = None) -> None:
        self.bus = bus
        if self.bus is None and _HAS_BUS:
            try:
                self.bus = EventBus()
            except Exception:
                self.bus = None

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self.bus is None:
            return
        try:
            self.bus.publish(
                event_type,
                {**payload, "timestamp": time.time()},
            )
        except Exception:
            pass  # never break planning on bus failure

    def plan_started(self, prompt_signature: str) -> None:
        self._emit("ai.plan_started", {"prompt_signature": prompt_signature})

    def plan_created(self, workflow: str, confidence: float,
                     provider: str, latency_ms: float) -> None:
        self._emit("ai.plan_created", {
            "workflow": workflow,
            "confidence": confidence,
            "provider": provider,
            "latency_ms": latency_ms,
        })

    def plan_failed(self, prompt_signature: str, error: str,
                    stage: str) -> None:
        self._emit("ai.plan_failed", {
            "prompt_signature": prompt_signature,
            "error": error[:200],
            "stage": stage,
        })
''')


# ---------------------------------------------------------------------------
# pipeline.py
# ---------------------------------------------------------------------------

_register_source("pipeline", '''"""AutoFlow AI - Planning pipeline (generated from metadata).

The deterministic 11-stage pipeline:
  1 normalize  2 intent  3 entities  4 tasks  5 connectors
  6 capabilities  7 constraints  8 workflow+graph  9 validate
  10 optimize  11 specify

Each stage is independently testable. LLM-dependent stages accept an
optional provider and fall back to deterministic heuristics.
"""

import time
from typing import Any, Dict, List, Optional

from app.ai.planner.ambiguity import AmbiguityDetector
from app.ai.planner.capability_matcher import CapabilityMatcher
from app.ai.planner.clarification import ClarificationEngine
from app.ai.planner.confidence import ConfidenceScorer
from app.ai.planner.connector_selector import ConnectorSelector, connector_catalog
from app.ai.planner.constraint_solver import ConstraintSolver
from app.ai.planner.cost_estimator import CostEstimator
from app.ai.planner.entity_extractor import EntityExtractor
from app.ai.planner.exceptions import AmbiguityError, PlanValidationError, PlannerError
from app.ai.planner.graph_builder import WorkflowGraphBuilder
from app.ai.planner.intent import IntentAnalyzer
from app.ai.planner.latency_estimator import LatencyEstimator
from app.ai.planner.models import (
    PlanRequest, PlanResult, PlanStep, WorkflowPlan,
)
from app.ai.planner.normalizer import PromptNormalizer
from app.ai.planner.optimizer import PlanOptimizer
from app.ai.planner.reasoning import ReasoningTracer
from app.ai.planner.task_extractor import TaskExtractor
from app.ai.planner.validator import PlanValidator
from app.ai.planner.workflow_builder import WorkflowBuilder

DEFAULT_MAX_STEPS = 50


def _first_keyword(entities: Dict[str, Any], key: str) -> str:
    vals = entities.get(key) or []
    return vals[0] if vals else ""


class PlanningPipeline:
    """Runs the 11 deterministic planning stages."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None,
                 provider: Optional[Any] = None,
                 max_steps: int = DEFAULT_MAX_STEPS,
                 constraints: Optional[Dict[str, Any]] = None,
                 examples: Optional[List[Dict]] = None) -> None:
        self.catalog = catalog if catalog is not None else connector_catalog()
        self.provider = provider
        self.max_steps = max_steps
        self.tracer = ReasoningTracer()
        self.normalizer = PromptNormalizer()
        self.intent = IntentAnalyzer(provider=provider)
        self.entities = EntityExtractor(provider=provider,
                                        known_connectors=list(self.catalog))
        self.tasks = TaskExtractor(provider=provider, max_steps=max_steps)
        self.selector = ConnectorSelector(catalog=self.catalog)
        self.matcher = CapabilityMatcher(catalog=self.catalog)
        self.solver = ConstraintSolver(constraints=constraints)
        self.builder = WorkflowBuilder()
        self.graph = WorkflowGraphBuilder()
        self.validator = PlanValidator(catalog=self.catalog)
        self.optimizer = PlanOptimizer()
        self.ambiguity = AmbiguityDetector()
        self.clarify = ClarificationEngine()
        self.cost = CostEstimator()
        self.latency = LatencyEstimator()
        self.confidence = ConfidenceScorer()

    def set_provider(self, provider: Optional[Any]) -> None:
        """Re-bind the LLM provider across LLM-capable stages."""
        self.provider = provider
        self.intent.provider = provider
        self.entities.provider = provider
        self.tasks.provider = provider

    # -- stage runners ------------------------------------------------------

    def _stage_normalize(self, request: PlanRequest) -> Any:
        return self.normalizer.normalize(request.prompt)

    def _stage_intent(self, normalized: Any) -> Dict:
        if self.provider is not None:
            return self.intent.refine_with_llm(normalized.text)
        return self.intent.classify(normalized.text, normalized.keywords)

    def _stage_entities(self, normalized: Any) -> Dict:
        if self.provider is not None:
            return self.entities.extract_with_llm(normalized.text)
        return self.entities.extract(normalized.text, normalized.keywords)

    def _stage_tasks(self, request: PlanRequest, normalized: Any,
                     entities: Dict) -> List[Dict]:
        if self.provider is not None:
            return self.tasks.extract_with_llm(normalized.text, entities)
        return self.tasks.extract(normalized.text, entities)

    def _stage_connectors(self, entities: Dict, text: str) -> List[Dict]:
        return self.selector.discover(entities, text)

    def _stage_capabilities(self, tasks: List[Dict],
                            entities: Dict) -> Dict[str, Dict]:
        """Bind each task to a connector+action, returning matches keyed by id."""
        bound = []
        matches: Dict[str, Dict] = {}
        named = list(entities.get("connectors") or [])
        for i, task in enumerate(tasks):
            tid = task.get("id") or str(i + 1)
            connector = task.get("connector") or (
                named[i] if i < len(named) else "")
            if not connector:
                # Infer from the first candidate.
                try:
                    selected = self.selector.select(entities, task.get("target", ""))
                    connector = selected.get("connector", "") if isinstance(selected, dict) else str(selected)
                except Exception:
                    connector = ""
            task["id"] = tid
            task["connector"] = connector
            if connector:
                match = self.matcher.best(task, connector)
                if match:
                    matches[tid] = match
                else:
                    try:
                        matches[tid] = self.matcher.require(task, connector)
                    except Exception:
                        matches[tid] = {"action": "run", "score": 0.1,
                                        "reasons": ["fallback"]}
            bound.append(task)
        return matches

    def _stage_constraints(self, tasks: List[Dict],
                           request: PlanRequest) -> List[Dict]:
        resolved = self.solver.resolve_dependencies(tasks)
        self.warnings.extend(self.solver.check_step_limit(len(resolved)))
        return resolved

    def _stage_trigger(self, entities: Dict, intent: Dict) -> Dict:
        hints = entities.get("trigger_hints") or []
        trigger: Dict[str, Any] = {}
        if "schedule" in hints:
            trigger = {"type": "schedule", "connector": "system"}
        elif "webhook" in hints:
            trigger = {"type": "webhook", "connector": "system"}
        elif "new" in hints:
            conn = _first_keyword(entities, "connectors")
            trigger = {"type": "event", "connector": conn or "system"}
        return trigger

    def _stage_build(self, resolved: List[Dict], matches: Dict[str, Dict],
                     trigger: Dict, entities: Dict,
                     request: PlanRequest) -> WorkflowPlan:
        self.builder.name = request.prompt[:60] or "Generated Workflow"
        plan = self.builder.build(resolved, matches, trigger, entities)
        graph = self.graph.build(plan.steps)
        plan.graph = graph
        return plan

    def _stage_validate(self, plan: WorkflowPlan) -> Dict[str, Any]:
        return self.validator.validate(plan)

    def _stage_optimize(self, plan: WorkflowPlan) -> WorkflowPlan:
        return self.optimizer.optimize(plan)

    def _stage_specify(self, plan: WorkflowPlan, request: PlanRequest,
                       intent: Dict, entities: Dict,
                       warnings: List[str], latency_ms: float) -> PlanResult:
        matches_scores: List[float] = []
        for step in plan.steps:
            key = (step.connector, step.action)
            if key in self._match_cache:
                matches_scores.append(self._match_cache[key].get("score", 0.5))
        entity_ratio = min(1.0, len(entities.get("connectors") or []) / 1.0)
        ambiguity_count = len(self._ambiguity_issues)
        confidence = self.confidence.score(
            intent_confidence=intent.get("confidence", 0.0),
            entity_ratio=entity_ratio,
            capability_scores=matches_scores or None,
            ambiguity_count=ambiguity_count,
            warning_count=len(warnings),
        )
        plan.confidence = confidence
        cost = self.cost.estimate(plan.steps, plan.trigger)
        lat = self.latency.estimate(plan.steps, plan.trigger, plan.graph)
        plan.estimated_cost = cost["total"]
        plan.estimated_latency_ms = lat["total_ms"]
        plan.estimated_retries = self._estimate_retries()
        plan.metadata = {
            "strategy": request.strategy,
            "provider": request.provider,
            "model": request.model,
            "organization_id": request.organization_id,
            "credentials": request.session_memory.get("credentials", {}),
        }
        plan.validation = {
            "errors": [],
            "warnings": list(warnings),
            "confidence_bucket": self.confidence.bucket(confidence),
        }
        result = PlanResult(
            plan=plan,
            intent=intent.get("name", "unknown"),
            intent_confidence=intent.get("confidence", 0.0),
            entities=entities,
            reasoning=self.tracer.to_dict(),
            provider=request.provider,
            model=request.model,
            latency_ms=round(latency_ms, 2),
            warnings=list(warnings),
        )
        return result

    def _estimate_retries(self) -> float:
        return 0.0

    # -- public API ---------------------------------------------------------

    def plan(self, request: PlanRequest) -> PlanResult:
        """Run the full pipeline for a PlanRequest."""
        self.warnings = []
        self._match_cache: Dict[tuple, Dict] = {}
        self._ambiguity_issues = []
        start = time.perf_counter()

        self.tracer.begin("normalize")
        normalized = self._stage_normalize(request)
        self.tracer.record("normalize", "prompt normalized",
                           {"signature": normalized.signature})

        self.tracer.begin("intent")
        intent = self._stage_intent(normalized)
        self.tracer.record("intent", f"intent={intent.get('name')}", intent)

        self.tracer.begin("entities")
        entities = self._stage_entities(normalized)
        self.tracer.record("entities", "entities extracted",
                           {"count": len(entities.get("connectors") or [])})

        self.tracer.begin("tasks")
        tasks = self._stage_tasks(request, normalized, entities)
        self.tracer.record("tasks", f"tasks={len(tasks)}")

        self.tracer.begin("connectors")
        candidates = self._stage_connectors(entities, normalized.text)
        self.tracer.record("connectors",
                           f"candidates={[c.get('connector') for c in candidates]}")

        self.tracer.begin("capabilities")
        matches = self._stage_capabilities(tasks, entities)
        for tid, m in matches.items():
            step = next((t for t in tasks if t.get("id") == tid), None)
            if step:
                self._match_cache[(step.get("connector"), m.get("action"))] = m
        self.tracer.record("capabilities", f"matched={len(matches)}")

        self.tracer.begin("constraints")
        resolved = self._stage_constraints(tasks, request)
        self.tracer.record("constraints", f"resolved={len(resolved)}")

        trigger = self._stage_trigger(entities, intent)

        # Ambiguity check before building.
        issues = self.ambiguity.detect(
            entities, resolved, candidates, trigger or None,
            self.catalog,
            request.session_memory.get("credentials", {}),
        )
        self._ambiguity_issues = issues
        if issues:
            questions = self.clarify.to_questions(issues)
            if self._blocking(issues):
                plan = WorkflowPlan()
                plan.clarification_required = True
                plan.clarification_questions = self.clarify.format(questions)
                plan.metadata = {"strategy": request.strategy,
                                 "organization_id": request.organization_id}
                latency = (time.perf_counter() - start) * 1000
                result = PlanResult(
                    plan=plan,
                    intent=intent.get("name", "unknown"),
                    intent_confidence=intent.get("confidence", 0.0),
                    entities=entities,
                    reasoning=self.tracer.to_dict(),
                    latency_ms=round(latency, 2),
                    warnings=[f"clarification: {q}" for q in plan.clarification_questions],
                )
                return result

        self.tracer.begin("graph")
        try:
            plan = self._stage_build(resolved, matches, trigger, entities, request)
        except PlannerError as exc:
            self.tracer.record("graph", f"graph error: {exc}")
            raise
        self.tracer.record("graph", "dag built", {"nodes": len(plan.steps)})

        self.tracer.begin("validate")
        validation = self._stage_validate(plan)
        self.warnings.extend(validation.get("warnings", []))
        self.tracer.record("validate", "plan validated", validation)

        self.tracer.begin("optimize")
        plan = self._stage_optimize(plan)
        self.tracer.record("optimize", "plan optimized",
                           {"rules": self.optimizer.applied})

        latency_ms = (time.perf_counter() - start) * 1000
        result = self._stage_specify(plan, request, intent, entities,
                                     self.warnings, latency_ms)
        self.tracer.record("specify", "plan emitted",
                           {"steps": len(plan.steps)})
        return result

    @staticmethod
    def _blocking(issues: List[Dict]) -> bool:
        blocking = {"connector", "credentials", "trigger"}
        return any(i.get("category") in blocking for i in issues)

    def stage_names(self) -> List[str]:
        return ["normalize", "intent", "entities", "tasks", "connectors",
                "capabilities", "constraints", "graph", "validate",
                "optimize", "specify"]
''')


# ---------------------------------------------------------------------------
# planner.py
# ---------------------------------------------------------------------------

_register_source("planner", '''"""AutoFlow AI - AIPlanner facade (generated from metadata).

The public entry point. The planner REASONS and PLANS; it never executes
workflows. It depends only on BaseLLMProvider (never a concrete SDK),
resolves providers through app.ai.providers.factory, and returns a
PlanResult whose WorkflowPlan is the Runtime input.
"""

import time
from typing import Any, Dict, List, Optional

from app.ai.planner.cache import PlanCache
from app.ai.planner.events import PlannerEvents
from app.ai.planner.exceptions import (
    PlannerError, ProviderNotConfiguredError,
)
from app.ai.planner.memory import PlannerMemory
from app.ai.planner.metrics import PlannerMetrics
from app.ai.planner.models import PlanRequest, PlanResult
from app.ai.planner.pipeline import PlanningPipeline
from app.ai.planner.connector_selector import connector_catalog

# Global registries so all planner instances share state.
_MEMORY = PlannerMemory()
_CACHE = PlanCache(memory=_MEMORY)
_METRICS = PlannerMetrics()
_EVENTS = PlannerEvents()


def get_metrics() -> PlannerMetrics:
    return _METRICS


def get_memory() -> PlannerMemory:
    return _MEMORY


def clear_caches() -> None:
    _MEMORY.clear()
    _CACHE.memory.clear()


class AIPlanner:
    """High-level planner facade."""

    def __init__(self, provider: Optional[Any] = None,
                 provider_name: str = "",
                 model: str = "",
                 max_steps: int = 50,
                 use_cache: bool = True,
                 catalog: Optional[Dict[str, Dict]] = None) -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.model = model
        self.use_cache = use_cache
        self.catalog = catalog if catalog is not None else connector_catalog()
        self.pipeline = PlanningPipeline(
            catalog=self.catalog,
            provider=provider,
            max_steps=max_steps,
        )

    def plan(self, prompt: str, organization_id: str = "",
             user_id: str = "", conversation_id: str = "",
             session_memory: Optional[Dict[str, Any]] = None,
             strategy: str = "structured",
             provider: Optional[Any] = None,
             provider_name: str = "",
             model: str = "") -> PlanResult:
        """Plan a workflow from a natural-language prompt."""
        request = PlanRequest(
            prompt=prompt,
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation_id,
            session_memory=session_memory or {},
            strategy=strategy,
            provider=provider_name or self.provider_name,
            model=model or self.model,
        )
        active_provider = provider or self.provider
        if request.provider and not active_provider:
            try:
                from app.ai.providers.factory import provider_factory
                active_provider = provider_factory.create(request.provider,
                                                          model=request.model)
            except ProviderNotConfiguredError:
                pass  # deterministic fallback
            except Exception:
                pass
        if active_provider is not self.pipeline.provider:
            self.pipeline.set_provider(active_provider)

        # Cache lookup.
        if self.use_cache:
            cached = _CACHE.get_plan(prompt, strategy, request.provider)
            if cached:
                result = self._from_cache(cached)
                if result:
                    return result

        start = time.perf_counter()
        _EVENTS.plan_started(hash(prompt))
        try:
            result = self.pipeline.plan(request)
        except PlannerError as exc:
            _EVENTS.plan_failed(hash(prompt), str(exc), exc.stage)
            _METRICS.record(0.0, failure=exc.kind)
            raise

        result.latency_ms = round((time.perf_counter() - start) * 1000, 2)
        _METRICS.record(result.latency_ms, confidence=result.plan.confidence if result.plan else 0.0,
                        model=request.model or request.provider,
                        tokens=result.token_usage or None)
        _EVENTS.plan_created(
            result.plan.workflow if result.plan else "",
            result.plan.confidence if result.plan else 0.0,
            request.provider or "deterministic",
            result.latency_ms,
        )
        if self.use_cache and result.plan and not result.plan.clarification_required:
            _CACHE.set_plan(prompt, strategy, request.provider, result.to_dict())
        return result

    def clarify(self, prompt: str, **kwargs: Any) -> List[str]:
        """Run planning up to the ambiguity stage and return questions."""
        result = self.plan(prompt, **kwargs)
        return list(result.plan.clarification_questions) if result.plan else []

    def metrics(self) -> Dict[str, Any]:
        return _METRICS.snapshot()

    def catalog_summary(self) -> Dict[str, Any]:
        return {
            "connectors": sorted(self.catalog.keys()),
            "count": len(self.catalog),
        }

    @staticmethod
    def _from_cache(cached: Dict[str, Any]) -> Optional[PlanResult]:
        try:
            plan_data = cached.get("plan")
            plan = None
            if isinstance(plan_data, dict):
                plan = WorkflowPlan(**plan_data)
            result = PlanResult(**{k: v for k, v in cached.items()
                                   if k != "plan"})
            result.plan = plan
            return result
        except Exception:
            return None
''')


# ---------------------------------------------------------------------------
# __init__.py
# ---------------------------------------------------------------------------

_register_source("__init__", '''"""AutoFlow AI - Planner package (generated from metadata).

The deterministic AI planning pipeline: prompt -> WorkflowPlan. The
planner reasons and plans; the Workflow Runtime executes.
"""

from app.ai.planner.ambiguity import AmbiguityDetector
from app.ai.planner.cache import PlanCache
from app.ai.planner.capability_matcher import CapabilityMatcher
from app.ai.planner.clarification import ClarificationEngine
from app.ai.planner.confidence import ConfidenceScorer
from app.ai.planner.connector_selector import (
    ConnectorSelector, connector_catalog,
)
from app.ai.planner.constraint_solver import ConstraintSolver
from app.ai.planner.cost_estimator import CostEstimator
from app.ai.planner.entity_extractor import EntityExtractor
from app.ai.planner.events import PlannerEvents
from app.ai.planner.exceptions import (
    AmbiguityError, CapabilityMatchError, ConnectorDiscoveryError,
    ConstraintError, EntityExtractionError, GraphError, IntentError,
    NormalizationError, PlanValidationError, PlannerError,
    ProviderError, ProviderNotConfiguredError,
)
from app.ai.planner.examples import (
    all_prompts, find_by_prompt_keyword, get_examples, set_examples,
)
from app.ai.planner.graph_builder import WorkflowGraphBuilder
from app.ai.planner.intent import INTENT_TAXONOMY, IntentAnalyzer
from app.ai.planner.latency_estimator import LatencyEstimator
from app.ai.planner.memory import PlannerMemory
from app.ai.planner.metrics import PlannerMetrics
from app.ai.planner.models import (
    ClarificationQuestion, PlanRequest, PlanResult, PlanStep, WorkflowPlan,
)
from app.ai.planner.normalizer import (
    NormalizedPrompt, PromptNormalizer, normalize_text,
)
from app.ai.planner.optimizer import PlanOptimizer
from app.ai.planner.pipeline import PlanningPipeline
from app.ai.planner.planner import (
    AIPlanner, clear_caches, get_memory, get_metrics,
)
from app.ai.planner.reasoning import ReasoningTracer
from app.ai.planner.task_extractor import TaskExtractor
from app.ai.planner.validator import PlanValidator
from app.ai.planner.workflow_builder import WorkflowBuilder

__all__ = [
    "AIPlanner", "AmbiguityDetector", "AmbiguityError",
    "CapabilityMatchError", "CapabilityMatcher", "ClarificationEngine",
    "ClarificationQuestion", "ConfidenceScorer", "ConnectorDiscoveryError",
    "ConnectorSelector", "ConstraintError", "ConstraintSolver",
    "CostEstimator", "EntityExtractionError", "EntityExtractor",
    "GraphError", "INTENT_TAXONOMY", "IntentAnalyzer", "IntentError",
    "LatencyEstimator", "NormalizationError", "NormalizedPrompt",
    "PlanCache", "PlanRequest", "PlanResult", "PlanStep",
    "PlanValidationError", "PlanValidator", "PlanOptimizer",
    "PlannerError", "PlannerEvents", "PlannerMemory", "PlannerMetrics",
    "PlanningPipeline", "PromptNormalizer", "ProviderError",
    "ProviderNotConfiguredError", "ReasoningTracer", "TaskExtractor",
    "WorkflowBuilder", "WorkflowGraphBuilder", "WorkflowPlan",
    "all_prompts", "clear_caches", "connector_catalog",
    "find_by_prompt_keyword", "get_examples", "get_memory", "get_metrics",
    "normalize_text", "set_examples",
]
''')


# ---------------------------------------------------------------------------
# providers/base.py
# ---------------------------------------------------------------------------

_register_source("providers/base", '''"""AutoFlow AI - LLM provider abstraction (generated from metadata).

The planner NEVER depends on a concrete LLM SDK; it depends only on
BaseLLMProvider. Subclasses implement ``complete`` (synchronous) and
``acomplete`` (asynchronous). All providers are import-safe: optional
SDKs are imported defensively and raise ProviderNotConfiguredError when
missing.
"""

import os
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderNotConfiguredError


class BaseLLMProvider:
    """Abstract LLM provider interface."""

    name: str = "base"
    env_key: str = ""
    default_model: str = ""
    supported_models: List[str] = []
    capabilities: List[str] = ["chat"]
    streaming: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

    def __init__(self, api_key: Optional[str] = None,
                 model: str = "", base_url: str = "",
                 timeout_seconds: int = 30) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self._api_key_source = "explicit" if api_key else "env"

    # -- key resolution -----------------------------------------------------

    def resolve_api_key(self) -> str:
        """Resolve the API key from explicit value or environment."""
        if self.api_key:
            return self.api_key
        if self.env_key:
            value = os.environ.get(self.env_key, "")
            if value:
                return value
        raise ProviderNotConfiguredError(provider=self.name)

    def is_configured(self) -> bool:
        """True when a usable API key is available (or not required)."""
        if not self.env_key and not self.api_key:
            return True  # local providers like ollama need no key
        try:
            self.resolve_api_key()
            return True
        except ProviderNotConfiguredError:
            return False

    # -- interface ----------------------------------------------------------

    def complete(self, prompt: str, system: str = "",
                 max_tokens: int = 1024, temperature: float = 0.2,
                 json_mode: bool = False) -> str:
        """Run a chat completion and return the text content."""
        raise NotImplementedError

    async def acomplete(self, prompt: str, system: str = "",
                       max_tokens: int = 1024, temperature: float = 0.2,
                       json_mode: bool = False) -> str:
        """Async chat completion. Defaults to the sync implementation."""
        return self.complete(prompt, system=system, max_tokens=max_tokens,
                             temperature=temperature, json_mode=json_mode)

    def count_tokens(self, text: str) -> int:
        """Cheap token estimate (characters / 4)."""
        return max(1, len(text) // 4)

    def metadata(self) -> Dict[str, Any]:
        """Provider metadata for metrics/observability."""
        return {
            "name": self.name,
            "model": self.model,
            "streaming": self.streaming,
            "capabilities": list(self.capabilities),
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "configured": self.is_configured(),
        }

    def _messages(self, system: str, prompt: str) -> List[Dict[str, str]]:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs
''')


# ---------------------------------------------------------------------------
# providers/openai.py
# ---------------------------------------------------------------------------

_register_source("providers/openai", '''"""AutoFlow AI - OpenAI provider (generated from metadata)."""

import json
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError, ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

try:\n    import openai as _openai\n    _HAS_SDK = True\nexcept Exception:  # pragma: no cover - optional SDK\n    _openai = None\n    _HAS_SDK = False\n\n\ntry:\n    import httpx as _httpx\n    _HAS_HTTPX = True\nexcept Exception:  # pragma: no cover\n    _httpx = None\n    _HAS_HTTPX = False\n\n\nclass OpenAIProvider(BaseLLMProvider):\n    """OpenAI chat completions provider."""\n\n    name = "openai"\n    env_key = "OPENAI_API_KEY"\n    default_model = "gpt-4o-mini"\n    capabilities = ["chat", "json_mode", "function_calling"]\n    streaming = True\n    cost_per_1k_input = 0.00015\n    cost_per_1k_output = 0.0006\n\n    def __init__(self, api_key=None, model="", base_url="",\n                 timeout_seconds=30):\n        super().__init__(api_key=api_key, model=model,\n                         base_url=base_url or "https://api.openai.com/v1",\n                         timeout_seconds=timeout_seconds)\n\n    def complete(self, prompt, system="", max_tokens=1024,\n                 temperature=0.2, json_mode=False):\n        key = self.resolve_api_key()\n        if _HAS_SDK:\n            try:\n                client = _openai.OpenAI(api_key=key, base_url=self.base_url or None)\n                kwargs = {}\n                if json_mode:\n                    kwargs["response_format"] = {"type": "json_object"}\n                resp = client.chat.completions.create(\n                    model=self.model,\n                    messages=self._messages(system, prompt),\n                    max_tokens=max_tokens,\n                    temperature=temperature,\n                    **kwargs,\n                )\n                return (resp.choices[0].message.content or "").strip()\n            except Exception as exc:\n                if _HAS_HTTPX and self._retryable(exc):\n                    return self._via_httpx(key, prompt, system, max_tokens,\n                                           temperature, json_mode)\n                raise ProviderError(f"openai: {exc}", provider=self.name) from exc\n        if _HAS_HTTPX:\n            return self._via_httpx(key, prompt, system, max_tokens,\n                                   temperature, json_mode)\n        raise ProviderNotConfiguredError(provider=self.name)\n\n    def _via_httpx(self, key, prompt, system, max_tokens, temperature, json_mode):\n        payload = {\n            "model": self.model,\n            "messages": self._messages(system, prompt),\n            "max_tokens": max_tokens,\n            "temperature": temperature,\n        }\n        if json_mode:\n            payload["response_format"] = {"type": "json_object"}\n        resp = _httpx.post(\n            self.base_url + "/chat/completions",\n            headers={"Authorization": f"Bearer {key}"},\n            json=payload,\n            timeout=self.timeout_seconds,\n        )\n        resp.raise_for_status()\n        data = resp.json()\n        return (data["choices"][0]["message"]["content"] or "").strip()\n\n    @staticmethod\n    def _retryable(exc) -> bool:\n        return True\n''')


# ---------------------------------------------------------------------------
# providers/factory.py
# ---------------------------------------------------------------------------

_register_source("providers/factory", '''"""AutoFlow AI - LLM provider factory (generated from metadata).

Creates providers by name, resolving configuration from metadata
(providers.yaml) and environment. Returns BaseLLMProvider instances;
never a concrete SDK.
"""

from typing import Any, Dict, Optional

from app.ai.planner.exceptions import ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

_PROVIDER_CLASSES: Dict[str, type] = {}


def register_provider(name: str, cls: type) -> None:
    """Register a provider class (called by the generated init)."""
    _PROVIDER_CLASSES[name] = cls


def provider_names() -> list:
    return sorted(_PROVIDER_CLASSES.keys())


def _provider_config() -> Dict[str, Any]:
    """Provider metadata baked in at generation time."""
    return {}


def provider_factory(name: str, api_key: Optional[str] = None,
                     model: str = "", base_url: str = "",
                     config: Optional[Dict[str, Any]] = None) -> BaseLLMProvider:
    """Create a provider instance by name."""
    cls = _PROVIDER_CLASSES.get(name)
    if cls is None:\n        raise ProviderNotConfiguredError(provider=name)\n    instance = cls(api_key=api_key, model=model, base_url=base_url)\n    if not instance.is_configured():\n        raise ProviderNotConfiguredError(provider=name)\n    return instance\n\n\ndef create_default(config: Optional[Dict[str, Any]] = None) -> BaseLLMProvider:\n    """Create the default provider (first configured)."""\n    for name in provider_names():\n        try:\n            return provider_factory(name, config=config)\n        except ProviderNotConfiguredError:\n            continue\n    raise ProviderNotConfiguredError(provider="default")\n''')


# ---------------------------------------------------------------------------
# providers/anthropic.py
# ---------------------------------------------------------------------------

_register_source("providers/anthropic", '''"""AutoFlow AI - Anthropic provider (generated from metadata)."""

import json
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError, ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

try:\n    import anthropic as _anthropic\n    _HAS_SDK = True\nexcept Exception:  # pragma: no cover - optional SDK\n    _anthropic = None\n    _HAS_SDK = False\n\n\ntry:\n    import httpx as _httpx\n    _HAS_HTTPX = True\nexcept Exception:  # pragma: no cover\n    _httpx = None\n    _HAS_HTTPX = False\n\n\nclass AnthropicProvider(BaseLLMProvider):\n    """Anthropic Claude messages provider."""\n\n    name = "anthropic"\n    env_key = "ANTHROPIC_API_KEY"\n    default_model = "claude-3-5-haiku"\n    capabilities = ["chat", "function_calling"]\n    streaming = True\n    cost_per_1k_input = 0.0008\n    cost_per_1k_output = 0.004\n\n    def __init__(self, api_key=None, model="", base_url="",\n                 timeout_seconds=30):\n        super().__init__(api_key=api_key, model=model,\n                         base_url=base_url or "https://api.anthropic.com/v1",\n                         timeout_seconds=timeout_seconds)\n\n    def complete(self, prompt, system="", max_tokens=1024,\n                 temperature=0.2, json_mode=False):\n        key = self.resolve_api_key()\n        if _HAS_SDK:\n            try:\n                client = _anthropic.Anthropic(api_key=key)\n                resp = client.messages.create(\n                    model=self.model,\n                    system=system or None,\n                    messages=[{"role": "user", "content": prompt}],\n                    max_tokens=max_tokens,\n                    temperature=temperature,\n                )\n                parts = []\n                for block in resp.content:\n                    if getattr(block, "type", "") == "text":\n                        parts.append(block.text)\n                return "".join(parts).strip()\n            except Exception as exc:\n                if _HAS_HTTPX:\n                    return self._via_httpx(key, prompt, system, max_tokens,\n                                           temperature)\n                raise ProviderError(f"anthropic: {exc}", provider=self.name) from exc\n        if _HAS_HTTPX:\n            return self._via_httpx(key, prompt, system, max_tokens, temperature)\n        raise ProviderNotConfiguredError(provider=self.name)\n\n    def _via_httpx(self, key, prompt, system, max_tokens, temperature):\n        payload = {\n            "model": self.model,\n            "system": system or None,\n            "messages": [{"role": "user", "content": prompt}],\n            "max_tokens": max_tokens,\n            "temperature": temperature,\n        }\n        resp = _httpx.post(\n            self.base_url + "/messages",\n            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},\n            json=payload,\n            timeout=self.timeout_seconds,\n        )\n        resp.raise_for_status()\n        data = resp.json()\n        parts = [b.get("text", "") for b in data.get("content", [])\n                 if b.get("type") == "text"]\n        return "".join(parts).strip()\n''')


# ---------------------------------------------------------------------------
# providers/gemini.py
# ---------------------------------------------------------------------------

_register_source("providers/gemini", '''"""AutoFlow AI - Google Gemini provider (generated from metadata)."""

import json
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError, ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

try:\n    import httpx as _httpx\n    _HAS_HTTPX = True\nexcept Exception:  # pragma: no cover\n    _httpx = None\n    _HAS_HTTPX = False\n\n\nclass GeminiProvider(BaseLLMProvider):\n    """Google Gemini generateContent provider."""\n\n    name = "gemini"\n    env_key = "GEMINI_API_KEY"\n    default_model = "gemini-1.5-flash"\n    capabilities = ["chat", "json_mode"]\n    streaming = True\n    cost_per_1k_input = 0.000075\n    cost_per_1k_output = 0.0003\n\n    def __init__(self, api_key=None, model="", base_url="",\n                 timeout_seconds=30):\n        super().__init__(api_key=api_key, model=model,\n                         base_url=base_url or "https://generativelanguage.googleapis.com/v1beta",\n                         timeout_seconds=timeout_seconds)\n\n    def complete(self, prompt, system="", max_tokens=1024,\n                 temperature=0.2, json_mode=False):\n        key = self.resolve_api_key()\n        if not _HAS_HTTPX:\n            raise ProviderNotConfiguredError(provider=self.name)\n        try:\n            contents = [{"parts": [{"text": prompt}]}]\n            if system:\n                contents.insert(0, {"role": "user",\n                                   "parts": [{"text": system}]})\n            payload = {\n                "contents": contents,\n                "generationConfig": {\n                    "temperature": temperature,\n                    "maxOutputTokens": max_tokens,\n                },\n            }\n            if json_mode:\n                payload["generationConfig"]["responseMimeType"] = "application/json"\n            url = f"{self.base_url}/models/{self.model}:generateContent?key={key}"\n            resp = _httpx.post(url, json=payload, timeout=self.timeout_seconds)\n            resp.raise_for_status()\n            data = resp.json()\n            candidates = data.get("candidates") or []\n            if not candidates:\n                return ""\n            parts = candidates[0].get("content", {}).get("parts") or []\n            return "".join(p.get("text", "") for p in parts).strip()\n        except Exception as exc:\n            raise ProviderError(f"gemini: {exc}", provider=self.name) from exc\n''')


# ---------------------------------------------------------------------------
# providers/openrouter.py
# ---------------------------------------------------------------------------

_register_source("providers/openrouter", '''"""AutoFlow AI - OpenRouter provider (generated from metadata)."""

import json
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError, ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

try:\n    import httpx as _httpx\n    _HAS_HTTPX = True\nexcept Exception:  # pragma: no cover\n    _httpx = None\n    _HAS_HTTPX = False\n\n\nclass OpenRouterProvider(BaseLLMProvider):\n    """OpenRouter chat completions provider."""\n\n    name = "openrouter"\n    env_key = "OPENROUTER_API_KEY"\n    default_model = "openai/gpt-4o-mini"\n    capabilities = ["chat", "json_mode", "function_calling"]\n    streaming = True\n\n    def __init__(self, api_key=None, model="", base_url="",\n                 timeout_seconds=30):\n        super().__init__(api_key=api_key, model=model,\n                         base_url=base_url or "https://openrouter.ai/api/v1",\n                         timeout_seconds=timeout_seconds)\n\n    def complete(self, prompt, system="", max_tokens=1024,\n                 temperature=0.2, json_mode=False):\n        key = self.resolve_api_key()\n        if not _HAS_HTTPX:\n            raise ProviderNotConfiguredError(provider=self.name)\n        try:\n            payload = {\n                "model": self.model,\n                "messages": self._messages(system, prompt),\n                "max_tokens": max_tokens,\n                "temperature": temperature,\n            }\n            if json_mode:\n                payload["response_format"] = {"type": "json_object"}\n            resp = _httpx.post(\n                self.base_url + "/chat/completions",\n                headers={"Authorization": f"Bearer {key}"},\n                json=payload,\n                timeout=self.timeout_seconds,\n            )\n            resp.raise_for_status()\n            data = resp.json()\n            choices = data.get("choices") or []\n            if not choices:\n                return ""\n            return (choices[0].get("message", {}).get("content") or "").strip()\n        except Exception as exc:\n            raise ProviderError(f"openrouter: {exc}", provider=self.name) from exc\n''')


# ---------------------------------------------------------------------------
# providers/ollama.py
# ---------------------------------------------------------------------------

_register_source("providers/ollama", '''"""AutoFlow AI - Ollama provider (generated from metadata).

Local provider; requires no API key.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError
from app.ai.providers.base import BaseLLMProvider

try:
    import httpx as _httpx
    _HAS_HTTPX = True
except Exception:  # pragma: no cover
    _httpx = None
    _HAS_HTTPX = False


class OllamaProvider(BaseLLMProvider):
    """Ollama local chat provider."""

    name = "ollama"
    env_key = ""  # no key required
    default_model = "llama3.1"
    capabilities = ["chat"]
    streaming = True

    def __init__(self, api_key=None, model="", base_url="",
                 timeout_seconds=120):
        super().__init__(api_key=api_key, model=model,
                         base_url=base_url or "http://localhost:11434",
                         timeout_seconds=timeout_seconds)

    def complete(self, prompt, system="", max_tokens=1024,
                 temperature=0.2, json_mode=False):
        if not _HAS_HTTPX:
            raise ProviderError("ollama requires httpx", provider=self.name)
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
            resp = _httpx.post(self.base_url + "/api/chat", json=payload,
                               timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            return (data.get("message", {}).get("content") or "").strip()
        except Exception as exc:
            raise ProviderError(f"ollama: {exc}", provider=self.name) from exc
''')


# ---------------------------------------------------------------------------
# providers/vllm.py
# ---------------------------------------------------------------------------

_register_source("providers/vllm", '''"""AutoFlow AI - vLLM provider (generated from metadata).

vLLM serves an OpenAI-compatible REST API; requires no SDK beyond httpx.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError, ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

try:
    import httpx as _httpx
    _HAS_HTTPX = True
except Exception:  # pragma: no cover
    _httpx = None
    _HAS_HTTPX = False


class VLLMProvider(BaseLLMProvider):
    """vLLM OpenAI-compatible chat provider."""

    name = "vllm"
    env_key = "VLLM_API_KEY"
    default_model = ""
    capabilities = ["chat", "json_mode"]
    streaming = True

    def __init__(self, api_key=None, model="", base_url="",
                 timeout_seconds=60):
        super().__init__(api_key=api_key, model=model,
                         base_url=base_url or "http://localhost:8000/v1",
                         timeout_seconds=timeout_seconds)

    def is_configured(self) -> bool:
        return True  # local deployments need no key

    def complete(self, prompt, system="", max_tokens=1024,
                 temperature=0.2, json_mode=False):
        if not _HAS_HTTPX:
            raise ProviderNotConfiguredError(provider=self.name)
        try:
            payload = {
                "model": self.model,
                "messages": self._messages(system, prompt),
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            resp = _httpx.post(self.base_url + "/chat/completions",
                               json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return ""
            return (choices[0].get("message", {}).get("content") or "").strip()
        except Exception as exc:
            raise ProviderError(f"vllm: {exc}", provider=self.name) from exc
''')


# ---------------------------------------------------------------------------
# providers/__init__.py
# ---------------------------------------------------------------------------

_register_source("providers/__init__", '''"""AutoFlow AI - LLM provider package (generated from metadata).

The planner depends only on BaseLLMProvider; concrete SDKs are never
imported directly by the planner.
"""

from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.factory import (
    create_default, provider_factory, provider_names, register_provider,
)

# Register all providers so the factory can resolve them by name.
from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.openrouter import OpenRouterProvider
from app.ai.providers.vllm import VLLMProvider

for _name, _cls in [
    ("openai", OpenAIProvider),
    ("anthropic", AnthropicProvider),
    ("gemini", GeminiProvider),
    ("openrouter", OpenRouterProvider),
    ("ollama", OllamaProvider),
    ("vllm", VLLMProvider),
]:
    register_provider(_name, _cls)

__all__ = [
    "AnthropicProvider", "BaseLLMProvider", "GeminiProvider",
    "OllamaProvider", "OpenAIProvider", "OpenRouterProvider",
    "VLLMProvider", "create_default", "provider_factory",
    "provider_names", "register_provider",
]
''')


# ---------------------------------------------------------------------------
# AIPlannerGenerator class + builders (from ai_planner_class_source.py)
# ---------------------------------------------------------------------------
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
    examples = pdef.examples or []
    return _AI_TEST_TEMPLATE.replace(
        "{example_count}", str(len(examples)))


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
    r = IntentAnalyzer().classify("when a new email arrives, post to slack")
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
    assert c.score(intent_confidence=0.9, capability_scores=[1.0]) > 0.7
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
    )
    assert result.plan is not None


def test_ai_planner_clarify():
    planner = AIPlanner(provider=None, catalog=CATALOG, use_cache=False)
    questions = planner.clarify("send a report")
    assert isinstance(questions, list)


def test_ai_planner_metrics():
    planner = AIPlanner(provider=None, catalog=CATALOG, use_cache=False)
    planner.plan("when a new email arrives, send a message to slack")
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
        prompt="when a new email arrives, send a message to slack"))
    runtime = result.plan.to_runtime_definition()
    assert "nodes" in runtime and "edges" in runtime
    assert runtime["nodes"]
'''


# ---------------------------------------------------------------------------
# AIPlannerGenerator class + builders (from ai_planner_class_source.py)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# AIPlannerGenerator class + builders (from ai_planner_class_source.py)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# AIPlannerGenerator class + builders (from ai_planner_class_source.py)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# AIPlannerGenerator class + builders (from ai_planner_class_source.py)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# AIPlannerGenerator class + builders (from ai_planner_class_source.py)
# ---------------------------------------------------------------------------
# --- AI_PLANNER_CLASS_SOURCE_BEGIN ---
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
# --- AI_PLANNER_CLASS_SOURCE_END ---


