"""AutoFlow AI - Trigger scheduler (generated from metadata).

Schedules manual / cron / system triggers in a background thread pool
and dispatches produced events to registered handlers.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TriggerScheduler:
    """Runs scheduled connector triggers in background threads."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = {}
        self._jobs: List[threading.Thread] = []
        self._stop = threading.Event()
        self._lock = threading.RLock()

    def on_event(self, event_type: str, handler: Callable) -> None:
        """Register a handler for a produced event type."""
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def _dispatch(self, event: Any) -> None:
        handlers = list(self._handlers.get(event.event_type, []))
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - handlers must not kill the loop
                logger.warning("trigger handler failed for %s: %s",
                               event.event_type, exc)

    def schedule_cron(self, trigger: str, connector: Callable,
                      cron: str, handler: Callable,
                      interval_seconds: int = 60) -> None:
        """Run a trigger on a simple interval (cron string accepted)."""
        def _loop() -> None:
            while not self._stop.is_set():
                try:
                    events = connector().execute_trigger(trigger)
                    for event in events:
                        handler(event)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("scheduled trigger %s failed: %s", trigger, exc)
                time.sleep(interval_seconds)
        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        with self._lock:
            self._jobs.append(thread)

    def run_once(self, trigger: str, connector: Any,
                 handler: Callable) -> int:
        """Run a trigger once now; returns the event count."""
        try:
            events = connector.execute_trigger(trigger)
            for event in events:
                handler(event)
            return len(events)
        except Exception as exc:  # noqa: BLE001
            logger.warning("one-off trigger %s failed: %s", trigger, exc)
            return 0

    def stop(self) -> None:
        self._stop.set()
        for thread in self._jobs:
            thread.join(timeout=1.0)
        self._jobs.clear()
