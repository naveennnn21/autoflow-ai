"""AutoFlow AI - LLM provider factory (generated from metadata).

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
    if cls is None:
        raise ProviderNotConfiguredError(provider=name)
    instance = cls(api_key=api_key, model=model, base_url=base_url)
    if not instance.is_configured():
        raise ProviderNotConfiguredError(provider=name)
    return instance


def create_default(config: Optional[Dict[str, Any]] = None) -> BaseLLMProvider:
    """Create the default provider (first configured)."""
    for name in provider_names():
        try:
            return provider_factory(name, config=config)
        except ProviderNotConfiguredError:
            continue
    raise ProviderNotConfiguredError(provider="default")
