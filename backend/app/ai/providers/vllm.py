"""AutoFlow AI - vLLM provider (generated from metadata).

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
