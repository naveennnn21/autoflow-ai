"""AutoFlow AI - Intent analyzer (stage 2, generated from metadata).

Classifies the user prompt into a fixed intent taxonomy. Uses the LLM
provider when available; falls back to deterministic keyword heuristics
so planning still works without any external provider configured.

Intent taxonomy (from metadata/ai/reasoning.yaml):
  automate, notify, sync, query, transform, approve, unknown
"""

from typing import Dict, List, Optional

from app.ai.planner.exceptions import IntentError

INTENT_TAXONOMY = [
    "automate",
    "notify",
    "sync",
    "query",
    "transform",
    "approve",
    "unknown",
]

# Deterministic keyword heuristics: intent -> trigger keywords.
_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "automate": [
        "when", "whenever", "if", "then", "automate", "auto", "trigger",
        "on", "after", "every", "each time", "workflow", "flow",
    ],
    "notify": [
        "notify", "notify me", "alert", "message", "send", "email", "slack",
        "discord", "post", "ping", "tell me", "inform", "remind",
    ],
    "sync": [
        "sync", "synchronize", "backup", "copy", "mirror", "export to",
        "import from", "move", "duplicate",
    ],
    "query": [
        "query", "search", "find", "look up", "fetch", "get", "list",
        "retrieve", "show me", "what", "how many",
    ],
    "transform": [
        "transform", "convert", "format", "summarize", "translate",
        "parse", "extract", "clean", "normalize", "aggregate",
    ],
    "approve": [
        "approve", "approval", "review", "sign off", "verify before",
        "require approval",
    ],
}

# Per-intent confidence weights used by the heuristic classifier.
_INTENT_WEIGHTS: Dict[str, float] = {
    "automate": 0.90,
    "notify": 0.85,
    "sync": 0.85,
    "query": 0.80,
    "transform": 0.85,
    "approve": 0.90,
}


class IntentAnalyzer:
    """Deterministic intent classifier with optional LLM refinement."""

    def __init__(self, provider: Optional[object] = None) -> None:
        self.provider = provider

    def classify(self, text: str, keywords: Optional[List[str]] = None) -> Dict:
        """Classify intent. Returns {name, confidence, reasons}."""
        kws = keywords or []
        scores: Dict[str, float] = {}
        reasons: Dict[str, List[str]] = {}
        lowered = text.lower()

        for intent, words in _INTENT_KEYWORDS.items():
            score = 0.0
            matched: List[str] = []
            for word in words:
                if word in lowered or any(word in kw for kw in kws):
                    score += 1.0
                    matched.append(word)
            if matched:
                scores[intent] = score
                reasons[intent] = matched

        if not scores:
            return {
                "name": "unknown",
                "confidence": 0.3,
                "reasons": ["no intent keywords matched"],
            }

        best = max(scores, key=lambda k: (scores[k], _INTENT_WEIGHTS.get(k, 0)))
        # Normalize confidence between 0.5 and the weight ceiling.
        raw = scores[best] / (scores[best] + 1.0)
        confidence = min(0.98, max(0.5, raw * _INTENT_WEIGHTS.get(best, 0.9)))
        return {
            "name": best,
            "confidence": round(confidence, 3),
            "reasons": reasons.get(best, []),
            "candidates": sorted(scores, key=lambda k: -scores[k])[:3],
        }

    def refine_with_llm(self, text: str) -> Dict:
        """Optional LLM refinement; falls back to heuristics on failure."""
        if self.provider is None:
            return self.classify(text)
        try:
            system = (
                "You classify user intent for a workflow automation platform. "
                f"Reply with exactly one word from: {', '.join(INTENT_TAXONOMY)}."
            )
            raw = self.provider.complete(text, system=system, max_tokens=8)
            name = (raw or "").strip().lower().split()[0]
            if name in INTENT_TAXONOMY:
                return {
                    "name": name,
                    "confidence": 0.9,
                    "reasons": ["llm_classification"],
                    "candidates": [name],
                }
        except Exception:
            pass
        return self.classify(text)
