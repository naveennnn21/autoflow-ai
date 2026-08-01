"""AutoFlow AI - Cost estimator (generated from metadata).

Estimates per-step and total execution cost from connector metadata
rate/cost hints and provider token pricing. Deterministic.
"""

from typing import Any, Dict, List, Optional

DEFAULT_ACTION_COST = 0.0001
DEFAULT_TRIGGER_COST = 0.00005


class CostEstimator:
    """Estimates workflow execution cost in USD."""

    def __init__(self, action_cost: float = DEFAULT_ACTION_COST,
                 trigger_cost: float = DEFAULT_TRIGGER_COST,
                 provider_costs: Optional[Dict[str, Dict]] = None) -> None:
        self.action_cost = action_cost
        self.trigger_cost = trigger_cost
        self.provider_costs = provider_costs or {}

    def step_cost(self, connector: str, action: str, provider: str = "") -> float:
        """Estimated cost of a single action call."""
        # Provider token costs dominate only for LLM-ish actions.
        if provider and provider in self.provider_costs:
            info = self.provider_costs[provider]
            input_price = float(info.get("cost_per_1k_input", 0.0))
            return round(input_price * 2.0 / 1000.0, 6) or self.action_cost
        return self.action_cost

    def estimate(self, steps: List[Any], trigger: Optional[Dict] = None,
                 provider: str = "") -> Dict[str, Any]:
        """Estimate total cost. Returns {total, breakdown}."""
        total = self.trigger_cost if trigger else 0.0
        breakdown = []
        for step in steps:
            cost = self.step_cost(
                getattr(step, "connector", ""),
                getattr(step, "action", ""),
                provider,
            )
            total += cost
            breakdown.append({
                "id": getattr(step, "id", ""),
                "cost": cost,
            })
        return {
            "total": round(total, 6),
            "currency": "usd",
            "breakdown": breakdown,
        }
