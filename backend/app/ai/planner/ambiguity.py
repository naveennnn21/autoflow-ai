"""AutoFlow AI - Ambiguity detector (generated from metadata).

Detects unsafe planning gaps: missing connector, multiple candidate
connectors, missing credentials, missing trigger, missing destination,
missing parameters. The planner MUST refuse unsafe assumptions and
return clarification questions instead.
"""

from typing import Any, Dict, List, Optional


class AmbiguityDetector:
    """Detects ambiguity and unsafe assumptions in a partial plan."""

    def __init__(self) -> None:
        self.issues: List[Dict[str, Any]] = []

    def detect(self, entities: Dict[str, Any], tasks: List[Dict],
               candidates: List[Dict], trigger: Optional[Dict],
               catalog: Dict[str, Dict],
               credentials: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Return a list of ambiguity issues: {category, message, options}."""
        self.issues = []
        credentials = credentials or {}

        # Missing connector: no entity match and no task connector.
        named = entities.get("connectors") or []
        task_connectors = {t.get("connector", "") for t in tasks if t.get("connector")}
        if not named and not task_connectors and not candidates:
            self.issues.append({
                "category": "connector",
                "message": "Which connector should this workflow use?",
                "options": sorted(catalog.keys())[:8],
            })

        # Multiple candidate connectors: prompt does not disambiguate.
        if len({c["connector"] for c in candidates}) > 1:
            self.issues.append({
                "category": "connector",
                "message": "Multiple connectors could match; which one?",
                "options": sorted({c["connector"] for c in candidates}),
            })

        # Missing credentials for private connectors.
        for task in tasks:
            conn = task.get("connector", "")
            if not conn or conn in credentials:
                continue
            info = catalog.get(conn)
            auth = (info or {}).get("authentication") or {}
            if auth and auth.get("type") not in (None, "", "none"):
                self.issues.append({
                    "category": "credentials",
                    "message": f"'{conn}' needs credentials "
                                f"({auth.get('type')}). Connect it first?",
                    "options": [],
                })

        # Missing trigger.
        if trigger is None:
            self.issues.append({
                "category": "trigger",
                "message": "When should this workflow run? (schedule, webhook, or manual)",
                "options": ["schedule", "webhook", "manual"],
            })

        # Missing destination for notify/send tasks.
        for task in tasks:
            action = task.get("action", "")
            if action in ("send_message", "send_email", "notify"):
                dest = (task.get("inputs") or {}).get("to") or                        (task.get("inputs") or {}).get("channel") or                        (task.get("inputs") or {}).get("recipient")
                if not dest:
                    self.issues.append({
                        "category": "destination",
                        "message": f"Where should '{action}' deliver the result?",
                        "options": [],
                    })

        # Missing required parameters.
        for task in tasks:
            missing = [k for k, v in (task.get("inputs") or {}).items()
                       if v in (None, "")]
            if missing:
                self.issues.append({
                    "category": "parameter",
                    "message": f"Missing parameter(s) for '{task.get('action', '')}': "
                                f"{', '.join(missing)}",
                    "options": [],
                })

        return list(self.issues)

    def requires_clarification(self) -> bool:
        """True when at least one blocking ambiguity exists."""
        return bool(self.issues)
