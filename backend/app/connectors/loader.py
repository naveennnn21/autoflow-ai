"""AutoFlow AI - Connector loader (generated from metadata).

Imports connector modules from the generated ``app.connectors.connectors``
package and registers their classes, supporting lazy loading.
"""

import importlib
import logging
import pkgutil
from typing import Dict, List, Optional, Type

from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class ConnectorLoader:
    """Discovers and imports connector classes."""

    PACKAGE = "app.connectors.connectors"

    def __init__(self, package: str = PACKAGE) -> None:
        self.package = package
        self._loaded: Dict[str, Type[BaseConnector]] = {}

    def load_module(self, module_name: str) -> List[Type[BaseConnector]]:
        """Import a connector module and return its connector classes."""
        fq = f"{self.package}.{module_name}"
        if fq in self._loaded and hasattr(self._loaded[fq], "name"):
            return [self._loaded[fq]]
        try:
            mod = importlib.import_module(fq)
        except Exception as exc:  # noqa: BLE001 - report and continue
            logger.warning("cannot import %s: %s", fq, exc)
            return []
        classes = [
            obj for obj in vars(mod).values()
            if isinstance(obj, type) and issubclass(obj, BaseConnector)
            and obj is not BaseConnector and getattr(obj, "name", "")
        ]
        for cls in classes:
            self._loaded[fq] = cls
        return classes

    def discover(self) -> Dict[str, Type[BaseConnector]]:
        """Import every module in the connectors package."""
        found: Dict[str, Type[BaseConnector]] = {}
        try:
            package = importlib.import_module(self.package)
        except Exception as exc:  # noqa: BLE001
            logger.warning("connectors package unavailable: %s", exc)
            return found
        for mod_info in pkgutil.iter_modules(package.__path__):
            for cls in self.load_module(mod_info.name):
                found[cls.name] = cls
        return found

    def loaded_names(self) -> List[str]:
        return sorted(self._loaded.keys())

    def clear(self) -> None:
        self._loaded.clear()
