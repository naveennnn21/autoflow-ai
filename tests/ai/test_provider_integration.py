"""AutoFlow AI - Phase 2.1: real LLM provider integration tests.

Hermetic tests: no network, no real API keys. A scriptable ``FakeLLMProvider``
double (tests only - never used in production) drives the existing planner
stages; the resolver/usage/mode helpers are exercised directly. The purpose
is to prove the wiring between the existing provider abstraction, the
planner pipeline, validation, and the Prompt Compiler - not to claim the
production provider works (that requires a live key, covered separately).
"""

import json

import pytest

from app.ai.planner.exceptions import (
    PlanValidationError,
    ProviderError,
    ProviderNotConfiguredError,
)
from app.ai.planner.planner import AIPlanner
from app.compiler.compiler import PromptCompiler

# Matches the catalog shape used across the planner test suite.
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
}


class FakeLLMProvider:
    """Deterministic provider double for tests (never used in production).

    Routes responses by the stage's system prompt so intent / entity /
    task stages each receive the structured output they expect. Callers may
    override with explicit ``responses`` (popped in call order), force an
    ``error`` on every call, or enable ``garbage_json`` to emit malformed
    structured output.
    """

    name = "fake"
    env_key = "FAKE_API_KEY"
    default_model = "fake-model"
    supported_models = ["fake-model"]

    def __init__(self, responses=None, error=None, model="",
                 garbage_json=False):
        self.model = model or self.default_model
        self.responses = list(responses or [])
        self.error = error
        self.garbage_json = garbage_json
        self.calls = 0

    def is_configured(self):
        return True

    def complete(self, prompt, system="", max_tokens=1024,
                 temperature=0.2, json_mode=False):
        self.calls += 1
        if self.error is not None:
            raise self.error
        if self.responses:
            return self.responses.pop(0)
        if json_mode and self.garbage_json:
            return "{{ this is not valid json"
        if "classify user intent" in system:
            return "automate"
        if "Extract planning entities" in system:
            return json.dumps({
                "connectors": ["slack"],
                "objects": ["message"],
                "parameters": {},
                "trigger_hints": ["webhook"],
            })
        if "Decompose the user request" in system:
            return json.dumps([
                {"action": "send_message", "target": "send a message to slack",
                 "depends_on": []},
            ])
        return "{}"


SLACK_PROMPT = "when a new email arrives, send a message to slack"
SLACK_MEMORY = {"credentials": {"slack": "x"}}
_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY",
         "GEMINI_API_KEY", "OPENROUTER_API_KEY")


def _clear_keys(monkeypatch):
    for key in _KEYS:
        monkeypatch.delenv(key, raising=False)


def _clear_settings_keys(monkeypatch):
    from app.core.config import settings
    for field in ("openai_api_key", "anthropic_api_key",
                  "gemini_api_key", "openrouter_api_key"):
        monkeypatch.setattr(settings, field, None)


# --- Provider factory ------------------------------------------------------

def test_provider_factory_openai_with_key():
    from app.ai.providers.factory import provider_factory
    provider = provider_factory("openai", api_key="sk-test")
    assert provider.name == "openai"
    assert provider.is_configured() is True


def test_provider_factory_missing_key_raises(monkeypatch):
    from app.ai.providers.factory import provider_factory
    _clear_keys(monkeypatch)
    _clear_settings_keys(monkeypatch)
    with pytest.raises(ProviderNotConfiguredError):
        provider_factory("openai")


# --- Default provider resolution ------------------------------------------

def test_resolver_no_keys_returns_none(monkeypatch):
    from app.ai.providers.resolver import (
        ProviderUsage, effective_mode, resolve_default_provider,
    )
    _clear_keys(monkeypatch)
    _clear_settings_keys(monkeypatch)
    assert resolve_default_provider() is None
    assert effective_mode(ProviderUsage(None), False) == "deterministic"


def test_resolver_settings_key_picks_openai_and_model(monkeypatch):
    from app.core.config import settings
    from app.ai.providers.resolver import resolve_default_provider
    _clear_keys(monkeypatch)
    _clear_settings_keys(monkeypatch)
    monkeypatch.setattr(settings, "openai_api_key", "sk-settings")
    provider = resolve_default_provider(model="gpt-4o")
    assert provider is not None
    assert provider.name == "openai"
    assert provider.model == "gpt-4o"


def test_resolver_prefers_openai_over_anthropic(monkeypatch):
    from app.core.config import settings
    from app.ai.providers.resolver import resolve_default_provider
    _clear_keys(monkeypatch)
    _clear_settings_keys(monkeypatch)
    monkeypatch.setattr(settings, "openai_api_key", "sk-openai")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-anthropic")
    provider = resolve_default_provider()
    assert provider is not None
    assert provider.name == "openai"


def test_resolver_never_picks_keyless_local_provider(monkeypatch):
    from app.ai.providers.factory import provider_names
    from app.ai.providers.resolver import resolve_default_provider
    assert "ollama" in provider_names()  # local provider is registered...
    _clear_keys(monkeypatch)
    _clear_settings_keys(monkeypatch)
    assert resolve_default_provider() is None  # ...but never silently chosen


def test_resolve_named_provider_with_key(monkeypatch):
    from app.core.config import settings
    from app.ai.providers.resolver import resolve_named_provider
    _clear_keys(monkeypatch)
    _clear_settings_keys(monkeypatch)
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-claude")
    provider = resolve_named_provider("anthropic", model="claude-3-5-sonnet")
    assert provider is not None
    assert provider.name == "anthropic"
    assert provider.model == "claude-3-5-sonnet"


def test_resolve_named_provider_without_key_returns_none(monkeypatch):
    from app.ai.providers.resolver import resolve_named_provider
    _clear_keys(monkeypatch)
    _clear_settings_keys(monkeypatch)
    assert resolve_named_provider("openai") is None
    assert resolve_named_provider("not_a_provider") is None


def test_per_request_mode_uses_deltas():
    from app.ai.providers.resolver import (
        ProviderUsage, per_request_mode,
    )
    # No provider configured -> deterministic regardless of usage.
    assert per_request_mode(ProviderUsage(None), 0, 0, False) == "deterministic"

    # This request succeeded -> real_llm even if an earlier request failed.
    usage = ProviderUsage(FakeLLMProvider())
    usage.calls = 5      # prior failed requests already counted...
    usage.successes = 0
    provider = usage.wrap()
    provider.complete("x", system="classify user intent", max_tokens=8)
    assert per_request_mode(usage, 5, 0, True) == "real_llm"

    # This request attempted calls but all failed -> fallback.
    usage2 = ProviderUsage(FakeLLMProvider(
        error=ProviderError("timeout", provider="fake")))
    provider2 = usage2.wrap()
    with pytest.raises(ProviderError):
        provider2.complete("x", system="classify user intent", max_tokens=8)
    assert per_request_mode(usage2, 0, 0, True) == "deterministic_fallback"

    # Configured provider but no call this request (e.g. cache hit).
    assert per_request_mode(usage, 6, 1, True) == "deterministic_fallback"


# --- Usage tracking + honest mode labels -----------------------------------

def test_usage_tracking_and_mode_labels():
    from app.ai.providers.resolver import (
        ProviderUsage, effective_mode,
    )
    ok = FakeLLMProvider()
    usage = ProviderUsage(ok)
    provider = usage.wrap()
    provider.complete("x", system="classify user intent", max_tokens=8)
    assert usage.calls == 1
    assert usage.successes == 1
    assert usage.used is True
    assert effective_mode(usage, True) == "real_llm"

    failing = FakeLLMProvider(
        error=ProviderError("upstream 500", provider="fake"))
    usage2 = ProviderUsage(failing)
    provider2 = usage2.wrap()
    with pytest.raises(ProviderError):
        provider2.complete("x", system="classify user intent", max_tokens=8)
    assert usage2.calls == 1
    assert usage2.successes == 0
    assert effective_mode(usage2, True) == "deterministic_fallback"

    assert effective_mode(ProviderUsage(None), False) == "deterministic"


# --- Planner with a real (fake) provider -----------------------------------

def test_planner_uses_llm_provider():
    fake = FakeLLMProvider()
    planner = AIPlanner(provider=fake, catalog=CATALOG, use_cache=False)
    result = planner.plan(SLACK_PROMPT, session_memory=SLACK_MEMORY)
    assert result.plan is not None
    assert not result.plan.clarification_required
    assert fake.calls >= 3  # intent + entities + tasks all hit the LLM


def test_planner_fallback_on_provider_error():
    fake = FakeLLMProvider(
        error=ProviderError("provider timeout", provider="fake"))
    planner = AIPlanner(provider=fake, catalog=CATALOG, use_cache=False)
    result = planner.plan(SLACK_PROMPT, session_memory=SLACK_MEMORY)
    assert result.plan is not None  # deterministic pipeline still plans
    assert fake.calls >= 1          # the provider was genuinely attempted


def test_planner_fallback_on_malformed_output():
    fake = FakeLLMProvider(garbage_json=True)
    planner = AIPlanner(provider=fake, catalog=CATALOG, use_cache=False)
    result = planner.plan(SLACK_PROMPT, session_memory=SLACK_MEMORY)
    assert result.plan is not None
    known = set(CATALOG)
    for step in result.plan.steps:
        assert step.connector in known  # nothing invalid reached the plan


def test_unknown_action_rejected_by_validator():
    # An action the Connector Registry does not expose must fail validation,
    # never reach the Compiler as an invented capability.
    fake = FakeLLMProvider(responses=[
        "automate",
        json.dumps({"connectors": ["slack"], "objects": ["message"],
                    "parameters": {}, "trigger_hints": ["webhook"]}),
        json.dumps([{"action": "fly_to_moon", "target": "launch",
                     "depends_on": []}]),
    ])
    planner = AIPlanner(provider=fake, catalog=CATALOG, use_cache=False)
    with pytest.raises(PlanValidationError):
        planner.plan(SLACK_PROMPT, session_memory=SLACK_MEMORY)


def test_invented_connector_never_reaches_compiler():
    fake = FakeLLMProvider(responses=[
        "automate",
        json.dumps({"connectors": ["nope_connector"], "objects": ["message"],
                    "parameters": {}, "trigger_hints": ["webhook"]}),
        json.dumps([{"action": "send_message", "target": "send it",
                     "depends_on": []}]),
    ])
    planner = AIPlanner(provider=fake, catalog=CATALOG, use_cache=False)
    rejected = False
    try:
        result = planner.plan(SLACK_PROMPT, session_memory={})
    except PlanValidationError:
        rejected = True
    if not rejected:
        # If the pipeline survived, every step must reference a real connector.
        assert result.plan is not None
        for step in result.plan.steps:
            assert step.connector in CATALOG


def test_ambiguous_prompt_with_provider_clarifies():
    fake = FakeLLMProvider(responses=[
        "automate",
        json.dumps({"connectors": [], "objects": [],
                    "parameters": {}, "trigger_hints": []}),
        json.dumps([]),
    ])
    planner = AIPlanner(provider=fake, catalog=CATALOG, use_cache=False)
    result = planner.plan("send a report", session_memory={})
    assert result.plan is not None
    assert result.plan.clarification_required is True


# --- Planner -> Compiler compatibility -------------------------------------

def test_llm_plan_compiles_to_spec():
    fake = FakeLLMProvider()
    planner = AIPlanner(provider=fake, catalog=CATALOG, use_cache=False)
    result = planner.plan(SLACK_PROMPT, session_memory=SLACK_MEMORY)
    compiler = PromptCompiler(connector_names=sorted(CATALOG))
    spec, report = compiler.compile_with_report(result.plan)
    assert not report.errors, report.errors
    spec_dict = spec.to_dict()
    assert spec_dict.get("nodes")


# --- Structured error mapping (no secrets) ---------------------------------

def test_router_error_payload_mapping():
    from app.api.v1.routers.planner import _error_payload
    payload = _error_payload(ProviderNotConfiguredError(provider="openai"))
    assert payload["code"] == "LLM_PROVIDER_NOT_CONFIGURED"
    assert payload["retryable"] is False

    payload = _error_payload(ProviderError("raw upstream: 401 ...",
                                           provider="openai"))
    assert payload["code"] == "LLM_PROVIDER_UNAVAILABLE"
    assert payload["retryable"] is True
    # Never leak raw provider text (may embed request internals).
    assert "401" not in payload["message"]
    assert "raw upstream" not in payload["message"]

    payload = _error_payload(PlanValidationError(
        "bad", errors=["connector nope is unknown"]))
    assert payload["code"] == "PLAN_VALIDATION_FAILED"
    assert payload["errors"] == ["connector nope is unknown"]
