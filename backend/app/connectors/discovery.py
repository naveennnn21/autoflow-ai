"""AutoFlow AI - Connector discovery (generated from metadata).

Exposes AI-planner-consumable metadata for every connector: actions
(with inputs/outputs), triggers, authentication, capabilities,
permissions, and example prompts.
"""

import json
from typing import Any, Dict, List, Optional

from app.connectors.registry import ConnectorRegistry


class ConnectorDiscovery:
    """Builds discovery payloads for the AI planner."""

    def __init__(self, registry: Optional[ConnectorRegistry] = None) -> None:
        self.registry = registry or ConnectorRegistry()

    def discover(self, name: str, version: str = "") -> dict:
        """Return the discovery metadata for a single connector."""
        cls = self.registry.get(name, version or None)
        meta = dict(cls.metadata)
        meta["name"] = cls.name
        meta["version"] = cls.version
        return self._normalize(meta)

    def discover_all(self) -> List[dict]:
        """Return discovery metadata for every registered connector."""
        return [self._normalize(dict(cls.metadata)) for cls in self.registry.all()]

    def actions(self, name: str) -> dict:
        cls = self.registry.get(name)
        actions = cls.metadata.get("actions", {})
        return {
            action: {
                "description": info.get("description", ""),
                "kind": info.get("kind", "run"),
                "inputs": info.get("inputs", {}),
                "outputs": info.get("outputs", {}),
                "required_permissions": info.get("required_permissions", []),
                "idempotent": info.get("idempotent", False),
                "long_running": info.get("long_running", False),
                "streaming": info.get("streaming", False),
            }
            for action, info in actions.items()
        }

    def triggers(self, name: str) -> dict:
        cls = self.registry.get(name)
        triggers = cls.metadata.get("triggers", {})
        return {
            trigger: {
                "description": info.get("description", ""),
                "kind": info.get("kind", "manual"),
                "webhook": info.get("webhook", False),
                "polling_interval_seconds": info.get(
                    "polling_interval_seconds", 60),
                "supported_events": info.get("supported_events", []),
            }
            for trigger, info in triggers.items()
        }

    def capabilities(self) -> Dict[str, List[str]]:
        """Map each capability flag to the connectors that support it."""
        result: Dict[str, List[str]] = {}
        for cls in self.registry.all():
            caps = cls.metadata.get("capabilities", {})
            for cap, enabled in caps.items():
                if enabled:
                    result.setdefault(cap, []).append(cls.name)
        return result

    def example_prompts(self, name: str) -> List[str]:
        cls = self.registry.get(name)
        docs = cls.metadata.get("documentation", {})
        prompt = docs.get("example_prompt", "")
        return [prompt] if prompt else []

    def to_json(self, name: str = "") -> str:
        payload: Any = self.discover(name) if name else self.discover_all()
        return json.dumps(payload, indent=2, default=str)

    @staticmethod
    def _normalize(meta: dict) -> dict:
        out = dict(meta)
        out.setdefault("name", "")
        out.setdefault("version", "1.0.0")
        out["module_name"] = meta.get("module_name") or str(meta.get("name", "")).lower()
        out["actions"] = {k: v for k, v in meta.get("actions", {}).items()}
        out["triggers"] = {k: v for k, v in meta.get("triggers", {}).items()}
        out["authentication"] = meta.get("authentication") or meta.get("auth", {})
        return out
