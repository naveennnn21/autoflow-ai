"""AutoFlow AI - Connector registry (generated from metadata).

Registers connector classes, supports lazy loading from the generated
``connectors`` package, version selection, and capability filtering.
"""

import logging
import threading
from typing import Callable, Dict, List, Optional, Tuple, Type

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ConnectorNotFoundError, DuplicateConnectorError,
)

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """Thread-safe registry of connector classes."""

    def __init__(self) -> None:
        self._classes: Dict[str, List[Type[BaseConnector]]] = {}
        self._lock = threading.RLock()

    def register(self, connector_cls: Type[BaseConnector],
                 replace: bool = False) -> None:
        """Register a connector class under its name+version."""
        name = connector_cls.name or connector_cls.__name__
        version = getattr(connector_cls, "version", "1.0.0")
        with self._lock:
            versions = self._classes.setdefault(name, [])
            for existing in versions:
                if existing.version == version:
                    if not replace:
                        raise DuplicateConnectorError(name, version)
                    versions.remove(existing)
                    break
            versions.append(connector_cls)
            versions.sort(key=lambda c: _version_key(c.version), reverse=True)

    def unregister(self, name: str, version: Optional[str] = None) -> bool:
        with self._lock:
            versions = self._classes.get(name)
            if not versions:
                return False
            if version is None:
                self._classes.pop(name, None)
                return True
            before = len(versions)
            versions[:] = [c for c in versions if c.version != version]
            if not versions:
                self._classes.pop(name, None)
            return len(versions) != before

    def get(self, name: str, version: Optional[str] = None) -> Type[BaseConnector]:
        """Return a registered connector class (latest version by default)."""
        with self._lock:
            versions = list(self._classes.get(name, []))
        if not versions:
            raise ConnectorNotFoundError(name, version)
        if version is not None:
            for cls in versions:
                if cls.version == version:
                    return cls
            raise ConnectorNotFoundError(name, version)
        return versions[0]

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._classes

    def names(self) -> List[str]:
        with self._lock:
            return sorted(self._classes.keys())

    def versions(self, name: str) -> List[str]:
        with self._lock:
            return [c.version for c in self._classes.get(name, [])]

    def by_capability(self, capability: str) -> List[Type[BaseConnector]]:
        """Return latest-version connector classes advertising a capability."""
        found = []
        with self._lock:
            for versions in self._classes.values():
                latest = versions[0]  # sorted newest first on register
                caps = getattr(latest, "metadata", {}).get("capabilities", {})
                if caps.get(capability):
                    found.append(latest)
        return found

    def all(self) -> List[Type[BaseConnector]]:
        with self._lock:
            return [v[0] for v in self._classes.values()]

    def count(self) -> int:
        with self._lock:
            return len(self._classes)

    def clear(self) -> None:
        with self._lock:
            self._classes.clear()


def _version_key(version: str) -> Tuple[int, int, int]:
    parts = version.split(".")
    nums: List[int] = []
    for p in parts[:3]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])
