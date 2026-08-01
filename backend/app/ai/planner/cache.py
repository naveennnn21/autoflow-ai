"""AutoFlow AI - Plan cache (generated from metadata).

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
