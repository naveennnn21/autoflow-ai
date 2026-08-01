"""AutoFlow AI - Google Gemini provider (generated from metadata)."""

import json
from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ProviderError, ProviderNotConfiguredError
from app.ai.providers.base import BaseLLMProvider

try:
    import httpx as _httpx
    _HAS_HTTPX = True
except Exception:  # pragma: no cover
    _httpx = None
    _HAS_HTTPX = False


class GeminiProvider(BaseLLMProvider):
    """Google Gemini generateContent provider."""

    name = "gemini"
    env_key = "GEMINI_API_KEY"
    default_model = "gemini-1.5-flash"
    capabilities = ["chat", "json_mode"]
    streaming = True
    cost_per_1k_input = 0.000075
    cost_per_1k_output = 0.0003

    def __init__(self, api_key=None, model="", base_url="",
                 timeout_seconds=30):
        super().__init__(api_key=api_key, model=model,
                         base_url=base_url or "https://generativelanguage.googleapis.com/v1beta",
                         timeout_seconds=timeout_seconds)

    def complete(self, prompt, system="", max_tokens=1024,
                 temperature=0.2, json_mode=False):
        key = self.resolve_api_key()
        if not _HAS_HTTPX:
            raise ProviderNotConfiguredError(provider=self.name)
        try:
            contents = [{"parts": [{"text": prompt}]}]
            if system:
                contents.insert(0, {"role": "user",
                                   "parts": [{"text": system}]})
            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }
            if json_mode:
                payload["generationConfig"]["responseMimeType"] = "application/json"
            url = f"{self.base_url}/models/{self.model}:generateContent?key={key}"
            resp = _httpx.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates") or []
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts") or []
            return "".join(p.get("text", "") for p in parts).strip()
        except Exception as exc:
            raise ProviderError(f"gemini: {exc}", provider=self.name) from exc
