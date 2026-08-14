"""AutoFlow AI - Default LLM provider resolution + usage tracking.

Hand-written (NOT generated) helper that connects the planner router to the
existing ``app.ai.providers`` abstraction:

- ``resolve_default_provider()`` picks the first provider with credentials.
  Credentials are read from the existing configuration system
  (``app.core.config.Settings``, which covers both real environment
  variables and a ``backend/.env`` file) and only fall back to the
  generated ``provider_factory.create_default()`` (plain environment
  variables) for anything not modelled by Settings.
- ``wrap_provider_usage()`` wraps a provider instance so the router can
  tell whether the LLM was *actually used* for a plan. This keeps the
  "REAL_LLM vs DETERMINISTIC_FALLBACK" distinction honest: a configured
  provider whose calls all fail must never be reported as an LLM plan.
- ``effective_mode()`` maps tracker state to a public mode label.

No API key is ever printed, logged, stored, or returned by this module.
"""

import logging
from typing import Any, Optional, Tuple

from app.ai.planner.exceptions import ProviderNotConfiguredError

logger = logging.getLogger(__name__)

# Settings-backed providers, in preference order (metadata default: openai).
_SETTINGS_PROVIDERS: Tuple[Tuple[str, str], ...] = (
    ("openai", "openai_api_key"),
    ("anthropic", "anthropic_api_key"),
    ("gemini", "gemini_api_key"),
    ("openrouter", "openrouter_api_key"),
)

_MODE_DETERMINISTIC = "deterministic"
_MODE_REAL_LLM = "real_llm"
_MODE_FALLBACK = "deterministic_fallback"


class ProviderUsage:
    """Tracks how many LLM calls were attempted/succeeded on a provider.

    ``complete``/``acomplete`` are wrapped with counting decorators, so the
    planner pipeline's existing LLM-assisted stages are observed without
    touching any generated module.
    """

    def __init__(self, provider: Optional[Any]) -> None:
        self.provider = provider
        self.calls = 0
        self.successes = 0

    def wrap(self) -> Any:
        """Return the provider with counting wrappers installed."""
        if self.provider is None:
            return None
        try:
            original = self.provider.complete

            def counting_complete(prompt: str, system: str = "",
                                  max_tokens: int = 1024,
                                  temperature: float = 0.2,
                                  json_mode: bool = False) -> str:
                self.calls += 1
                result = original(prompt, system=system,
                                  max_tokens=max_tokens,
                                  temperature=temperature,
                                  json_mode=json_mode)
                self.successes += 1
                return result

            self.provider.complete = counting_complete  # type: ignore[method-assign]
        except Exception as exc:  # noqa: BLE001 - never break planning
            logger.debug("provider usage wrapping unavailable: %s", exc)
        return self.provider

    @property
    def used(self) -> bool:
        """True when at least one provider call succeeded."""
        return self.successes > 0


def resolve_default_provider(model: str = "",
                             timeout_seconds: int = 30) -> Optional[Any]:
    """Return the first provider with explicit credentials, or None.

    The default provider always requires credentials, so a machine without
    any API key runs in deterministic mode - a no-key local provider such
    as ollama is never silently picked as the default. (Local providers
    remain selectable explicitly via ``POST /planner/plan`` with the
    ``provider`` field.)

    Credential sources, in order:
      1. ``app.core.config.Settings`` - real environment variables and/or
         a ``backend/.env`` file (openai/anthropic/gemini/openrouter).
      2. Plain process environment variables for the same four providers.
    """
    try:
        import os

        from app.core.config import settings
        from app.ai.providers.factory import provider_factory

        candidates = [
            (name, str(getattr(settings, settings_field, "") or ""))
            for name, settings_field in _SETTINGS_PROVIDERS
        ]
        # Plain env fallback for keys pydantic-settings did not model.
        for name, settings_field in _SETTINGS_PROVIDERS:
            candidates.append((name, os.environ.get(settings_field.upper(), "")))

        seen: set = set()
        for name, api_key in candidates:
            if name in seen or not api_key:
                continue
            seen.add(name)
            try:
                provider = provider_factory(
                    name, api_key=api_key, model=_pick_model(name, model),
                )
                provider.timeout_seconds = timeout_seconds
                return provider
            except Exception as exc:  # noqa: BLE001 - try next provider
                logger.debug("provider '%s' init failed: %s", name, exc)
        return None
    except Exception as exc:  # noqa: BLE001 - never break startup
        logger.warning("default provider resolution failed: %s", exc)
        return None


def create_wrapped_default(model: str = "",
                           timeout_seconds: int = 30
                           ) -> Tuple[Optional[Any], ProviderUsage]:
    """Resolve the default provider and wrap it for usage tracking."""
    usage = ProviderUsage(None)
    provider = resolve_default_provider(model=model,
                                        timeout_seconds=timeout_seconds)
    usage.provider = provider
    return usage.wrap(), usage


def effective_mode(usage: ProviderUsage, provider_configured: bool) -> str:
    """Static mode label for a provider's cumulative usage.

    - ``real_llm``: a provider was configured and at least one call worked.
    - ``deterministic_fallback``: a provider was configured but every LLM
      call failed (or none was attempted) - the plan is heuristic.
    - ``deterministic``: no provider is configured at all.
    """
    if not provider_configured:
        return _MODE_DETERMINISTIC
    return _MODE_REAL_LLM if usage.used else _MODE_FALLBACK


def per_request_mode(usage: ProviderUsage, calls_before: int,
                     successes_before: int,
                     provider_configured: bool) -> str:
    """Mode label for the plan produced by THIS request, from deltas.

    Uses counters captured before the request so a later request is never
    mislabelled ``real_llm`` because an *earlier* request succeeded.

    - ``real_llm``: this request made at least one successful LLM call.
    - ``deterministic_fallback``: this request attempted LLM calls that all
      failed, or a provider is configured but no call was attempted (e.g.
      the plan was served from cache) - the plan is heuristic.
    - ``deterministic``: no provider is configured at all.
    """
    if not provider_configured:
        return _MODE_DETERMINISTIC
    if usage.successes > successes_before:
        return _MODE_REAL_LLM
    return _MODE_FALLBACK


def resolve_named_provider(name: str, model: str = "",
                           timeout_seconds: int = 30) -> Optional[Any]:
    """Resolve a specific provider by name using its configured credential.

    ``None`` when the provider is unknown or has no credential configured -
    the caller then falls back deterministically. Same credential sources as
    ``resolve_default_provider`` (Settings first, then plain env).
    """
    try:
        import os

        from app.core.config import settings
        from app.ai.providers.factory import provider_factory

        settings_field = dict(_SETTINGS_PROVIDERS).get(name)
        if not settings_field:
            return None
        api_key = str(getattr(settings, settings_field, "") or "")
        api_key = api_key or os.environ.get(settings_field.upper(), "")
        if not api_key:
            return None
        provider = provider_factory(
            name, api_key=api_key, model=_pick_model(name, model),
        )
        provider.timeout_seconds = timeout_seconds
        return provider
    except Exception as exc:  # noqa: BLE001 - never break planning
        logger.debug("provider '%s' resolve failed: %s", name, exc)
        return None


def _pick_model(provider_name: str, requested: str) -> str:
    """Return the requested model when the provider can use it."""
    if not requested:
        return ""
    from app.ai.providers.factory import _PROVIDER_CLASSES
    cls = _PROVIDER_CLASSES.get(provider_name)
    supported = getattr(cls, "supported_models", None) if cls else []
    if not supported or requested in supported:
        return requested
    return ""
