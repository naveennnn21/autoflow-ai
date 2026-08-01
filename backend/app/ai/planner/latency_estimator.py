"""AutoFlow AI - Latency estimator (generated from metadata).

Estimates per-step and total execution latency (ms) from connector
metadata timeouts plus parallelism-aware path analysis.
"""

from typing import Any, Dict, List, Optional

DEFAULT_ACTION_MS = 250
DEFAULT_TRIGGER_MS = 50


class LatencyEstimator:
    """Estimates workflow execution latency in milliseconds."""

    def __init__(self, action_ms: int = DEFAULT_ACTION_MS,
                 trigger_ms: int = DEFAULT_TRIGGER_MS) -> None:
        self.action_ms = action_ms
        self.trigger_ms = trigger_ms

    def step_latency(self, step: Any) -> int:
        """Per-step latency estimate."""
        return int(getattr(step, "estimated_latency_ms", 0)) or self.action_ms

    def estimate(self, steps: List[Any], trigger: Optional[Dict] = None,
                 graph: Optional[Dict] = None) -> Dict[str, Any]:
        """Estimate total latency using the longest path through the DAG."""
        base = self.trigger_ms if trigger else 0
        deps: Dict[str, List[str]] = {}
        ids = []
        for step in steps:
            sid = getattr(step, "id", "")
            ids.append(sid)
            deps.setdefault(sid, [])
            for dep in getattr(step, "depends_on", []) or []:
                deps.setdefault(dep, []).append(sid)
        lat: Dict[str, int] = {}
        total = base

        def visit(node: str) -> int:
            if node in lat:
                return lat[node]
            best = 0
            for dst in deps.get(node, []):
                best = max(best, visit(dst))
            node_lat = self.step_latency(next(
                (s for s in steps if getattr(s, "id", "") == node), None))
            lat[node] = best + node_lat
            return lat[node]

        for sid in ids:
            total = max(total, visit(sid))
        return {
            "total_ms": int(total),
            "parallelism": len(ids),
            "breakdown": {"by_node": dict(lat)},
        }
