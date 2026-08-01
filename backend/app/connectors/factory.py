"""AutoFlow AI - Connector factory (generated from metadata).

Creates connector instances by name, version, or capability using the
registry. Instances are constructed with injected auth, transport,
metrics, and observability so the framework stays provider-independent.
"""

from typing import Any, Dict, Optional, Type

from app.connectors.base import BaseConnector
from app.connectors.exceptions import ConnectorNotFoundError
from app.connectors.registry import ConnectorRegistry


class ConnectorFactory:
    """Builds connector instances from registered classes."""

    def __init__(self, registry: Optional[ConnectorRegistry] = None,
                 auth_factory: Any = None,
                 transport: Any = None,
                 metrics: Any = None,
                 tracer: Any = None,
                 logger_factory: Any = None) -> None:
        self.registry = registry or ConnectorRegistry()
        self.auth_factory = auth_factory
        self.transport = transport
        self.metrics = metrics
        self.tracer = tracer
        self.logger_factory = logger_factory

    def create(self, name: str, version: Optional[str] = None,
               config: Optional[dict] = None,
               credentials: Optional[dict] = None,
               organization_id: str = "") -> BaseConnector:
        """Create a connector instance by name (latest version default)."""
        cls = self.registry.get(name, version)
        return self._instantiate(cls, config, credentials, organization_id)

    def create_by_version(self, name: str, version: str,
                          config: Optional[dict] = None,
                          credentials: Optional[dict] = None,
                          organization_id: str = "") -> BaseConnector:
        """Create a connector instance pinned to a version."""
        return self.create(name, version=version, config=config,
                           credentials=credentials,
                           organization_id=organization_id)

    def create_by_capability(self, capability: str,
                             config: Optional[dict] = None,
                             credentials: Optional[dict] = None,
                             organization_id: str = "") -> list:
        """Create instances for every connector advertising a capability."""
        instances = []
        for cls in self.registry.by_capability(capability):
            instances.append(self._instantiate(
                cls, config, credentials, organization_id))
        return instances

    def _instantiate(self, cls: Type[BaseConnector],
                     config: Optional[dict],
                     credentials: Optional[dict],
                     organization_id: str) -> BaseConnector:
        kwargs: Dict[str, Any] = {}
        if self.auth_factory is not None:
            try:
                kwargs["auth"] = self.auth_factory.build(
                    cls.metadata.get("authentication", {}) or
                    cls.metadata.get("auth", {}),
                    credentials or {},)
            except Exception:  # noqa: BLE001 - auth is optional
                pass
        if self.transport is not None:
            kwargs["transport"] = self.transport
        if self.metrics is not None:
            kwargs["metrics"] = self.metrics
        if self.tracer is not None:
            kwargs["tracer"] = self.tracer
        if self.logger_factory is not None:
            try:
                kwargs["logger_obj"] = self.logger_factory.logger(
                    connector=cls.name, tenant=organization_id)
            except Exception:  # noqa: BLE001
                pass
        return cls(config=config, credentials=credentials, **kwargs)
