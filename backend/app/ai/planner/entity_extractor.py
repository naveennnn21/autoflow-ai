"""AutoFlow AI - Entity extractor (stage 3, generated from metadata).

Extracts structured entities from the normalized prompt: connectors,
objects (e.g. database, page, order), parameters (values, recipients),
trigger signals, and destination hints. LLM-assisted when available,
deterministic keyword/known-connector matching otherwise.
"""

import re
from typing import Dict, List, Optional

_KNOWN_CONNECTORS = [
    "gmail", "outlook", "slack", "discord", "teams", "github", "gitlab",
    "jira", "linear", "notion", "confluence", "google_drive", "dropbox",
    "onedrive", "stripe", "shopify", "paypal", "airtable", "postgres",
    "mysql", "mongodb", "redis", "rest", "graphql", "grpc", "webhook",
]

_OBJECT_KEYWORDS: Dict[str, List[str]] = {
    "page": ["page", "doc", "document"],
    "database": ["database", "db", "table", "record"],
    "issue": ["issue", "bug", "ticket", "story"],
    "order": ["order", "purchase", "sale", "invoice"],
    "message": ["message", "dm", "comment", "post", "notification"],
    "file": ["file", "attachment", "image", "video", "spreadsheet", "sheet"],
    "contact": ["contact", "lead", "customer", "user", "member"],
    "task": ["task", "todo", "reminder", "card"],
    "repo": ["repo", "repository", "branch", "pr", "commit"],
}

_TRIGGER_KEYWORDS: Dict[str, List[str]] = {
    "new": ["new", "created", "added", "inserted", "opened"],
    "updated": ["updated", "changed", "modified", "edited"],
    "deleted": ["deleted", "removed", "closed", "cancelled", "canceled"],
    "schedule": ["every", "daily", "daily at", "morning", "evening", "night",
                 "weekly", "hourly", "cron"],
    "webhook": ["webhook", "event", "when"],
}

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_URL_RE = re.compile(r"https?://[^\s]+")
_TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?\b", re.I)


class EntityExtractor:
    """Extracts connectors, objects, parameters, and trigger hints."""

    def __init__(self, provider: Optional[object] = None,
                 known_connectors: Optional[List[str]] = None) -> None:
        self.provider = provider
        self.known_connectors = known_connectors or _KNOWN_CONNECTORS

    def extract(self, text: str, keywords: Optional[List[str]] = None) -> Dict:
        """Extract entities. Returns a dict with connectors/objects/params."""
        kws = keywords or []
        lowered = text.lower()
        entities: Dict = {
            "connectors": [],
            "objects": [],
            "parameters": {},
            "trigger_hints": [],
            "emails": [],
            "urls": [],
            "times": [],
        }

        # Connectors by known-name match.
        for name in self.known_connectors:
            if name in lowered or any(name in kw for kw in kws):
                entities["connectors"].append(name)

        # Objects by keyword match.
        for obj, words in _OBJECT_KEYWORDS.items():
            if any(w in lowered for w in words):
                entities["objects"].append(obj)

        # Trigger hints.
        for hint, words in _TRIGGER_KEYWORDS.items():
            if any(w in lowered for w in words):
                entities["trigger_hints"].append(hint)

        # Emails / urls / times.
        entities["emails"] = list(set(_EMAIL_RE.findall(lowered)))
        entities["urls"] = list(set(_URL_RE.findall(lowered)))
        entities["times"] = [m.group(0) for m in _TIME_RE.findall(lowered)][:5]

        # Deterministic parameter candidates: quoted phrases.
        quoted = re.findall(r"[\"']([^\"']{2,60})[\"']", text)
        if quoted:
            entities["parameters"]["quoted"] = quoted[:10]

        return entities

    def extract_with_llm(self, text: str) -> Dict:
        """LLM-assisted extraction; falls back to heuristics on failure."""
        if self.provider is None:
            return self.extract(text)
        try:
            system = (
                "Extract planning entities from the prompt. Reply as JSON with "
                'keys: connectors (list), objects (list), parameters (object), '
                "trigger_hints (list). No commentary."
            )
            raw = self.provider.complete(text, system=system, json_mode=True)
            import json
            data = json.loads(raw or "{}")
            if isinstance(data, dict):
                return {
                    "connectors": [str(c) for c in data.get("connectors", [])],
                    "objects": [str(o) for o in data.get("objects", [])],
                    "parameters": data.get("parameters", {}) or {},
                    "trigger_hints": [str(t) for t in data.get("trigger_hints", [])],
                    "emails": [],
                    "urls": [],
                    "times": [],
                }
        except Exception:
            pass
        return self.extract(text)
