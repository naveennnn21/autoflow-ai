"""AutoFlow AI - Connector discovery/selection (stage 5, generated from metadata).

Discovers candidate connectors through the Connector Registry
(``app.connectors.registry.ConnectorRegistry``) and selects the best
connector for each extracted entity/task. Works standalone with the
metadata-derived connector catalog when the registry is unavailable.
"""

from typing import Dict, List, Optional

from app.ai.planner.exceptions import ConnectorDiscoveryError

try:  # pragmatic: registry lives in the connectors package
    from app.connectors.registry import ConnectorRegistry
    _HAS_REGISTRY = True
    _REGISTRY = ConnectorRegistry()
    for _cls in _REGISTRY.all():
        _REGISTRY.register(_cls)
except Exception:  # pragma: no cover - registry optional
    _HAS_REGISTRY = False
    _REGISTRY = None

# Static catalog fallback: module_name -> capabilities of known connectors.
_FALLBACK_CATALOG: Dict[str, Dict] = {}


def _load_fallback_catalog() -> Dict[str, Dict]:
    """Build a static catalog from the connectors package metadata."""
    catalog: Dict[str, Dict] = {}
    try:
        from app.connectors.loader import ConnectorLoader
        found = ConnectorLoader().discover()
        for cname, cdef in found.items():
            meta = getattr(cdef, "metadata", {}) or {}
            entry = {
                "name": cname,
                "version": meta.get("version", "1.0.0"),
                "authentication": meta.get("authentication") or meta.get("auth", {}),
                "actions": list((meta.get("actions") or {}).keys()),
                "triggers": list((meta.get("triggers") or {}).keys()),
                "capabilities": meta.get("capabilities", {}) or {},
            }
            catalog[cname] = entry
            # Index by module slug too so planner lookups by module name work.
            slug = meta.get("module_name") or str(cname).lower().replace(" ", "_")
            if slug and slug != cname and slug not in catalog:
                catalog[slug] = entry
    except Exception:
        pass
    return catalog


def connector_catalog() -> Dict[str, Dict]:
    """Return the live connector catalog (registry or static fallback)."""
    global _FALLBACK_CATALOG
    if not _FALLBACK_CATALOG:
        _FALLBACK_CATALOG = _load_fallback_catalog()
    return _FALLBACK_CATALOG


class ConnectorSelector:
    """Selects connector(s) for extracted entities and tasks."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None) -> None:
        self.catalog = catalog if catalog is not None else connector_catalog()

    def discover(self, entities: Optional[Dict] = None,
                 text: str = "") -> List[Dict]:
        """Return candidate connectors matching entities or text keywords."""
        entities = entities or {}
        lowered = text.lower()
        candidates: List[Dict] = []

        named = entities.get("connectors") or []
        for name in named:
            info = self.catalog.get(name)
            if info:
                candidates.append({
                    "connector": name,
                    **info,
                    "matched_by": "entity",
                    "score": 1.0,
                })

        # Fuzzy keyword match for connectors not explicitly named.
        if not candidates and lowered:
            for name, info in self.catalog.items():
                keywords = [name, name.replace("_", " ")]
                if any(kw in lowered for kw in keywords):
                    candidates.append({
                        "connector": name,
                        **info,
                        "matched_by": "keyword",
                        "score": 0.9,
                    })

        # Match objects to connectors when no connector was named.
        if not candidates:
            for obj in entities.get("objects") or []:
                for name in ("notion", "airtable", "google_drive", "gmail",
                             "slack", "github", "jira", "stripe", "shopify"):
                    if obj in ("page", "database") and name == "notion":
                        candidates.append({"connector": name, "score": 0.7,
                                           "matched_by": "object"})
                    elif obj in ("file",) and name == "google_drive":
                        candidates.append({"connector": name, "score": 0.7,
                                           "matched_by": "object"})
                    elif obj in ("message",) and name == "slack":
                        candidates.append({"connector": name, "score": 0.7,
                                           "matched_by": "object"})

        # De-duplicate by connector name keeping highest score.
        seen: Dict[str, Dict] = {}
        for c in candidates:
            cur = seen.get(c["connector"])
            if cur is None or c.get("score", 0) > cur.get("score", 0):
                seen[c["connector"]] = c
        return sorted(seen.values(), key=lambda c: -c.get("score", 0))

    def select(self, entities: Optional[Dict] = None,
               text: str = "") -> Dict:
        """Select the single best connector (or raise)."""
        candidates = self.discover(entities, text)
        if not candidates:
            raise ConnectorDiscoveryError(
                f"No connector found for prompt: {text[:80]}", stage="connectors")
        return candidates[0]
