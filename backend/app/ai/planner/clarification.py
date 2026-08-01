"""AutoFlow AI - Clarification engine (generated from metadata).

Converts ambiguity issues into user-facing ClarificationQuestion objects
and formats them as plain-language questions with suggested options.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.models import ClarificationQuestion

_CATEGORY_LABELS = {
    "connector": "Connector",
    "credentials": "Credentials",
    "trigger": "Trigger",
    "destination": "Destination",
    "parameter": "Parameter",
    "general": "General",
}


class ClarificationEngine:
    """Turns ambiguity issues into questions."""

    def to_questions(self, issues: List[Dict[str, Any]]) -> List[ClarificationQuestion]:
        """Convert ambiguity issues to ClarificationQuestion objects."""
        return [
            ClarificationQuestion(
                question=issue.get("message", ""),
                category=issue.get("category", "general"),
                options=list(issue.get("options") or []),
                context=issue,
            )
            for issue in issues
        ]

    def format(self, questions: List[ClarificationQuestion]) -> List[str]:
        """Return plain-language question strings."""
        out = []
        for q in questions:
            label = _CATEGORY_LABELS.get(q.category, "General")
            text = f"[{label}] {q.question}"
            if q.options:
                text += f" Options: {', '.join(q.options)}"
            out.append(text)
        return out

    def merge_answer(self, question: ClarificationQuestion,
                     answer: str) -> Dict[str, Any]:
        """Record a user answer into the plan context."""
        return {
            "category": question.category,
            "question": question.question,
            "answer": answer,
        }
