"""AutoFlow AI - OpenAI provider (generated from metadata)."""

import json
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError, ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

try:
    import openai as _openai
    _HAS_SDK = True
except Exception:  # pragma: no cover - optional SDK
    _openai = None
    _HAS_SDK = False


try:
    import httpx as _httpx
    _HAS_HTTPX = True
except Exception:  # pragma: no cover
    _httpx = None
    _HAS_HTTPX = False


class OpenAIProvider(BaseLLMProvider):
    """OpenAI chat completions provider."""

    name = "openai"
    env_key = "OPENAI_API_KEY"
    default_model = "gpt-4o-mini"
    capabilities = ["chat", "json_mode", "function_calling"]
    streaming = True
    cost_per_1k_input = 0.00015
    cost_per_1k_output = 0.0006

    def __init__(self, api_key=None, model="", base_url="",
                 timeout_seconds=30):
        super().__init__(api_key=api_key, model=model,
                         base_url=base_url or "https://api.openai.com/v1",
                         timeout_seconds=timeout_seconds)

    def complete(self, prompt, system="", max_tokens=1024,
                 temperature=0.2, json_mode=False):
        key = self.resolve_api_key()
        if _HAS_SDK:
            try:
                client = _openai.OpenAI(api_key=key, base_url=self.base_url or None)
                kwargs = {}
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=self._messages(system, prompt),
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs,
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception as exc:
                if _HAS_HTTPX and self._retryable(exc):
                    return self._via_httpx(key, prompt, system, max_tokens,
                                           temperature, json_mode)
                raise ProviderError(f"openai: {exc}", provider=self.name) from exc
        if _HAS_HTTPX:
            return self._via_httpx(key, prompt, system, max_tokens,
                                   temperature, json_mode)
        raise ProviderNotConfiguredError(provider=self.name)

    def _via_httpx(self, key, prompt, system, max_tokens, temperature, json_mode):
        payload = {
            "model": self.model,
            "messages": self._messages(system, prompt),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = _httpx.post(
            self.base_url + "/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data["choices"][0]["message"]["content"] or "").strip()

    @staticmethod
    def _retryable(exc) -> bool:
        return True
