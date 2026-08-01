"""AutoFlow AI - Anthropic provider (generated from metadata)."""

import json
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError, ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

try:
    import anthropic as _anthropic
    _HAS_SDK = True
except Exception:  # pragma: no cover - optional SDK
    _anthropic = None
    _HAS_SDK = False


try:
    import httpx as _httpx
    _HAS_HTTPX = True
except Exception:  # pragma: no cover
    _httpx = None
    _HAS_HTTPX = False


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude messages provider."""

    name = "anthropic"
    env_key = "ANTHROPIC_API_KEY"
    default_model = "claude-3-5-haiku"
    capabilities = ["chat", "function_calling"]
    streaming = True
    cost_per_1k_input = 0.0008
    cost_per_1k_output = 0.004

    def __init__(self, api_key=None, model="", base_url="",
                 timeout_seconds=30):
        super().__init__(api_key=api_key, model=model,
                         base_url=base_url or "https://api.anthropic.com/v1",
                         timeout_seconds=timeout_seconds)

    def complete(self, prompt, system="", max_tokens=1024,
                 temperature=0.2, json_mode=False):
        key = self.resolve_api_key()
        if _HAS_SDK:
            try:
                client = _anthropic.Anthropic(api_key=key)
                resp = client.messages.create(
                    model=self.model,
                    system=system or None,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                parts = []
                for block in resp.content:
                    if getattr(block, "type", "") == "text":
                        parts.append(block.text)
                return "".join(parts).strip()
            except Exception as exc:
                if _HAS_HTTPX:
                    return self._via_httpx(key, prompt, system, max_tokens,
                                           temperature)
                raise ProviderError(f"anthropic: {exc}", provider=self.name) from exc
        if _HAS_HTTPX:
            return self._via_httpx(key, prompt, system, max_tokens, temperature)
        raise ProviderNotConfiguredError(provider=self.name)

    def _via_httpx(self, key, prompt, system, max_tokens, temperature):
        payload = {
            "model": self.model,
            "system": system or None,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        resp = _httpx.post(
            self.base_url + "/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = [b.get("text", "") for b in data.get("content", [])
                 if b.get("type") == "text"]
        return "".join(parts).strip()
