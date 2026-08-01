"""AutoFlow AI - Connector events (generated from metadata).

Publishes connector lifecycle, action, and trigger events to the
platform event bus (app.events) when available. Import-safe: the event
bus is imported defensively so the framework works without it.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConnectorEvents:
    """Publishes connector events to the platform bus."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._publisher = None
        if enabled:
            try:
                from app.events.publisher import Publisher
                self._publisher = Publisher()
            except Exception as exc:  # noqa: BLE001 - bus optional
                logger.warning("app.events unavailable: %s", exc)
                self._publisher = None

    def _emit(self, event_type: str, payload: Dict[str, Any],
              entity_id: Optional[str] = None,
              entity_type: str = "Connector",
              organization_id: Optional[str] = None,
              correlation_id: str = "") -> None:
        """Fire-and-forget publish on the running event loop."""
        if self._publisher is None or not self.enabled:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # no running loop: skip (tests/sync callers)
        try:
            coro = self._publisher.emit(
                event_type, dict(payload),
                entity_id=entity_id,
                entity_type=entity_type,
                organization_id=organization_id,
                correlation_id=correlation_id,
            )
            asyncio.ensure_future(coro)
        except Exception as exc:  # noqa: BLE001 - never break the flow
            logger.warning("failed to emit %s: %s", event_type, exc)

    def connected(self, connector: str, version: str,
                  instance_id: str, organization_id: str = "") -> None:
        self._emit("connector.connected", {
            "connector": connector,
            "version": version,
            "instance_id": instance_id,
        }, entity_id=instance_id, organization_id=organization_id)

    def disconnected(self, connector: str, instance_id: str,
                     organization_id: str = "") -> None:
        self._emit("connector.disconnected", {
            "connector": connector,
            "instance_id": instance_id,
        }, entity_id=instance_id, organization_id=organization_id)

    def error(self, connector: str, error: str, action: str = "",
              instance_id: str = "", organization_id: str = "") -> None:
        self._emit("connector.error", {
            "connector": connector,
            "error": error,
            "action": action,
            "instance_id": instance_id,
        }, entity_id=instance_id or None, organization_id=organization_id)

    def action_executed(self, connector: str, action: str, ok: bool,
                        duration_ms: float, organization_id: str = "") -> None:
        self._emit("connector.action_executed", {
            "connector": connector,
            "action": action,
            "ok": ok,
            "duration_ms": duration_ms,
        }, organization_id=organization_id)

    def trigger_fired(self, connector: str, trigger: str,
                      event_count: int, organization_id: str = "") -> None:
        self._emit("connector.trigger_fired", {
            "connector": connector,
            "trigger": trigger,
            "event_count": event_count,
        }, organization_id=organization_id)

    def reset(self) -> None:
        """Drop the publisher (used in tests)."""
        self._publisher = None
