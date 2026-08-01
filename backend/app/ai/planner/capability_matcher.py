"""AutoFlow AI - Capability matcher (stage 6, generated from metadata).

Matches extracted tasks against connector capabilities. Scores each
(task, action) pair using keyword overlap with action names and
validates that the action exists in the connector metadata.
"""

import re
from typing import Dict, List, Optional

from app.ai.planner.exceptions import CapabilityMatchError

_ACTION_SYNONYMS: Dict[str, List[str]] = {
    "send_message": ["send", "post", "message", "notify", "dm", "ping"],
    "send_email": ["send", "email", "mail", "compose"],
    "upload_file": ["upload", "put", "store", "save"],
    "download_file": ["download", "get", "pull", "fetch"],
    "copy_file": ["copy", "duplicate", "mirror"],
    "create": ["create", "add", "new", "insert", "make"],
    "update": ["update", "edit", "change", "modify", "set"],
    "delete": ["delete", "remove", "erase", "drop"],
    "search": ["search", "find", "query", "lookup"],
    "list": ["list", "all", "enumerate"],
    "get": ["get", "fetch", "retrieve", "read"],
    "sync": ["sync", "synchronize", "backup", "copy"],
    "generate": ["generate", "create", "produce"],
    "summarize": ["summarize", "summarise", "digest", "overview"],
    "convert": ["convert", "transform", "format", "translate"],
    "run": ["run", "execute", "call", "do", "trigger"],
}


def _word_overlap(a: List[str], b: List[str]) -> float:
    """Jaccard-style overlap between two word lists."""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class CapabilityMatcher:
    """Matches tasks to connector actions."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None) -> None:
        self.catalog = catalog if catalog is not None else {}

    def match(self, task: Dict, connector: str) -> List[Dict]:
        """Return ranked action matches for a task against a connector."""
        info = self.catalog.get(connector)
        if info is None:
            return []
        actions = info.get("actions") or []
        task_action = task.get("action", "run")
        target_words = re.findall(r"\w+", task.get("target", "").lower())

        matches: List[Dict] = []
        for action in actions:
            synonyms = _ACTION_SYNONYMS.get(action, [action])
            score = 0.0
            reasons: List[str] = []
            if task_action == action:
                score += 1.0
                reasons.append("exact_action")
            overlap = _word_overlap(synonyms, target_words)
            if overlap > 0:
                score += overlap
                reasons.append("synonym_overlap")
            if action in target_words:
                score += 0.5
                reasons.append("keyword_in_target")
            if score > 0:
                matches.append({
                    "action": action,
                    "score": round(min(1.0, score), 3),
                    "reasons": reasons,
                })

        if not matches and task_action in actions:
            matches.append({
                "action": task_action,
                "score": 1.0,
                "reasons": ["listed_action"],
            })
        return sorted(matches, key=lambda m: -m["score"])

    def best(self, task: Dict, connector: str) -> Optional[Dict]:
        """Return the best action match or None."""
        matches = self.match(task, connector)
        return matches[0] if matches else None

    def require(self, task: Dict, connector: str) -> Dict:
        """Return the best match, raising if none found."""
        best = self.best(task, connector)
        if best is None:
            raise CapabilityMatchError(
                f"Connector '{connector}' has no action for task "
                f"'{task.get('target', '')}' ({task.get('action', 'run')})",
                stage="capabilities")
        return best
