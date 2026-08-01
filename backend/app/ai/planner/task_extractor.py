"""AutoFlow AI - Task extractor (stage 4, generated from metadata).

Decomposes the user intent into an ordered list of tasks. Each task maps
onto a connector action. Deterministic pattern-based decomposition with
optional LLM refinement.
"""

import re
from typing import Dict, List, Optional

_VERB_ACTION_MAP: Dict[str, str] = {
    "send": "send_message",
    "post": "send_message",
    "message": "send_message",
    "notify": "send_message",
    "email": "send_email",
    "upload": "upload_file",
    "download": "download_file",
    "copy": "copy_file",
    "sync": "sync",
    "backup": "backup",
    "create": "create",
    "add": "create",
    "insert": "create",
    "update": "update",
    "edit": "update",
    "delete": "delete",
    "remove": "delete",
    "search": "search",
    "find": "search",
    "list": "list",
    "get": "get",
    "fetch": "get",
    "lookup": "get",
    "query": "query",
    "generate": "generate",
    "summarize": "summarize",
    "convert": "convert",
    "transform": "transform",
}

_SPLITTERS = re.compile(r"(?:,|\band\b|\bthen\b|\bafter that\b|\bfinally\b)")


class TaskExtractor:
    """Decomposes a prompt into ordered tasks."""

    def __init__(self, provider: Optional[object] = None,
                 max_steps: int = 50) -> None:
        self.provider = provider
        self.max_steps = max_steps

    def extract(self, text: str, entities: Optional[Dict] = None) -> List[Dict]:
        """Extract tasks deterministically. Returns [{action, target, keywords}]"""
        entities = entities or {}
        lowered = text.lower()
        clauses = [c.strip() for c in _SPLITTERS.split(lowered) if c.strip()]
        tasks: List[Dict] = []

        for clause in clauses:
            action = None
            for verb, mapped in sorted(_VERB_ACTION_MAP.items(),
                                       key=lambda kv: -len(kv[0])):
                if re.search(r"\b" + verb + r"\b", clause):
                    action = mapped
                    break
            if action is None:
                continue
            tasks.append({
                "action": action,
                "target": clause.strip(),
                "keywords": re.findall(r"\b\w+\b", clause),
                "source": "heuristic",
            })

        if not tasks and entities.get("connectors"):
            # No explicit verbs: infer a primary action per connector.
            for connector in entities["connectors"][:3]:
                tasks.append({
                    "action": "run",
                    "target": connector,
                    "keywords": [],
                    "source": "inferred",
                })

        # Cap the number of steps.
        return tasks[: self.max_steps]

    def extract_with_llm(self, text: str,
                         entities: Optional[Dict] = None) -> List[Dict]:
        """LLM-assisted extraction; falls back to heuristics on failure."""
        if self.provider is None:
            return self.extract(text, entities)
        try:
            import json
            system = (
                "Decompose the user request into ordered workflow tasks. "
                "Reply as a JSON array of objects with keys: action (string), "
                "target (string), depends_on (array of task indexes). "
                "No commentary."
            )
            raw = self.provider.complete(text, system=system, json_mode=True)
            data = json.loads(raw or "[]")
            if isinstance(data, list):
                out = []
                for item in data[: self.max_steps]:
                    if not isinstance(item, dict):
                        continue
                    out.append({
                        "action": str(item.get("action", "run")),
                        "target": str(item.get("target", "")),
                        "depends_on": [int(i) for i in item.get("depends_on", [])],
                        "source": "llm",
                    })
                if out:
                    return out
        except Exception:
            pass
        return self.extract(text, entities)
