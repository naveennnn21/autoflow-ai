"""AutoFlow AI - Confidence scorer (generated from metadata).

Computes a plan confidence in [0, 1] from intent confidence, entity
match strength, capability match scores, ambiguity, and validation
warnings. Deterministic.
"""

from typing import Any, Dict, List, Optional


class ConfidenceScorer:
    """Scores planning confidence."""

    def __init__(self, threshold_high: float = 0.8,
                 threshold_low: float = 0.5) -> None:
        self.threshold_high = threshold_high
        self.threshold_low = threshold_low

    def score(self, intent_confidence: float = 0.0,
              entity_ratio: float = 0.0,
              capability_scores: Optional[List[float]] = None,
              ambiguity_count: int = 0,
              warning_count: int = 0) -> float:
        """Compute the plan confidence score."""
        caps = capability_scores or []
        cap_avg = (sum(caps) / len(caps)) if caps else 0.0
        score = (
            0.4 * intent_confidence
            + 0.2 * entity_ratio
            + 0.3 * cap_avg
        )
        score -= 0.15 * ambiguity_count
        score -= 0.05 * warning_count
        return round(max(0.0, min(1.0, score)), 3)

    def bucket(self, score: float) -> str:
        """Return high/medium/low bucket for a score."""
        if score >= self.threshold_high:
            return "high"
        if score >= self.threshold_low:
            return "medium"
        return "low"
