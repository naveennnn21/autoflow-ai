"""AutoFlow AI - Webhook manager (generated from metadata).

Registers webhook triggers, verifies signatures, and dispatches
verified payloads to handlers with duplicate protection.
"""

import hashlib
import hmac
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WebhookManager:
    """Signature verification + dispatch for connector webhooks."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = {}
        self._secrets: Dict[str, str] = {}
        self._seen: Dict[str, set] = {}
        self._lock = threading.RLock()

    def register(self, trigger: str, handler: Callable,
                 secret: str = "", signing_header: str = "") -> None:
        with self._lock:
            self._handlers.setdefault(trigger, []).append(handler)
            if secret:
                self._secrets[trigger] = secret

    def verify(self, payload: bytes, signature: str, secret: str,
               algorithm: str = "sha256") -> bool:
        """Verify an HMAC signature (supports sha1/sha256)."""
        if not secret or not signature:
            return False
        digest = getattr(hashlib, algorithm, hashlib.sha256)
        expected = hmac.new(secret.encode(), payload, digest).hexdigest()
        if signature.startswith(f"{algorithm}="):
            signature = signature.split("=", 1)[1]
        return hmac.compare_digest(expected, signature)

    def dispatch(self, trigger: str, payload: bytes,
                 signature: str = "", event_id: str = "") -> int:
        """Verify + dispatch a webhook payload; returns handler count."""
        secret = self._secrets.get(trigger, "")
        if secret and not self.verify(payload, signature, secret):
            logger.warning("webhook %s failed signature verification", trigger)
            return 0
        with self._lock:
            seen = self._seen.setdefault(trigger, set())
        if event_id:
            if event_id in seen:
                return 0  # duplicate event
            seen.add(event_id)
        import json as _json
        try:
            data = _json.loads(payload.decode("utf-8"))
        except Exception:  # noqa: BLE001 - raw text payload
            data = {"raw": payload.decode("utf-8", errors="replace")}
        handlers = list(self._handlers.get(trigger, []))
        for handler in handlers:
            try:
                handler(trigger, data)
            except Exception as exc:  # noqa: BLE001
                logger.warning("webhook handler %s failed: %s", trigger, exc)
        return len(handlers)

    def reset(self) -> None:
        with self._lock:
            self._handlers.clear()
            self._secrets.clear()
            self._seen.clear()
