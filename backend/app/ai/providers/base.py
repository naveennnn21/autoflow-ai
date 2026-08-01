"""AutoFlow AI - LLM provider abstraction (generated from metadata).

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
