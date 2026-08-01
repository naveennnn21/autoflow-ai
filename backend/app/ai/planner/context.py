"""AutoFlow AI - Planning context (generated from metadata).

Assembles the full context passed to LLM stages: system prompt,
metadata-derived capability summaries, few-shot examples, and prior
conversation turns. Keeps provider calls deterministic-friendly.
"""

from typing import Any, Dict, List, Optional


class PlanningContext:
    """Builds context bundles for planning stages."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None,
                 examples: Optional[List[Dict]] = None) -> None:
        self.catalog = catalog or {}
        self.examples = examples or []

    def capability_summary(self, connector: str) -> str:
        """A compact capability summary for the connector."""
        info = self.catalog.get(connector, {})
        actions = info.get("actions") or []
        triggers = info.get("triggers") or []
        auth = (info.get("authentication") or {}).get("type", "none")
        return (
            f"{connector}: actions={','.join(actions[:8])}; "
            f"triggers={','.join(triggers[:4])}; auth={auth}"
        )

    def all_capabilities(self, limit: int = 60) -> str:
        """Compact catalog summary for the system prompt."""
        lines = [self.capability_summary(c) for c in list(self.catalog)[:limit]]
        return "\n".join(lines) or "(no connectors registered)"

    def few_shot(self, limit: int = 4) -> str:
        """Serialize few-shot examples for the prompt."""
        out = []
        for ex in self.examples[:limit]:
            out.append(f"Prompt: {ex.get('prompt', '')}")
            out.append(f"  intent: {ex.get('intent', '')}")
            steps = ex.get("steps") or []
            out.append(f"  steps: {len(steps)}")
        return "\n".join(out)

    def build(self, stage: str, prompt: str) -> Dict[str, str]:
        """Return {system, user} strings for an LLM stage."""
        system = (
            f"You are the AutoFlow AI planner for stage '{stage}'. "
            "Plan deterministically and prefer structured output. "
            "Available connectors:\n" + self.all_capabilities()
        )
        if self.examples:
            system += "\n\nFew-shot examples:\n" + self.few_shot()
        return {"system": system, "user": prompt}
