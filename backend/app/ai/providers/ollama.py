"""AutoFlow AI - Ollama provider (generated from metadata).

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
