"""AutoFlow AI - WebSocket transport (generated from metadata).

WebSocket client for streaming connectors. Uses ``websockets`` when
available; otherwise import-safe with clear runtime errors.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import websockets  # type: ignore  # noqa: F401
    HAS_WEBSOCKETS = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_WEBSOCKETS = False


class WebSocketTransport:
    """Minimal async WebSocket client."""

    def __init__(self, url: str = "",
                 headers: Optional[Dict[str, str]] = None) -> None:
        self.url = url
        self.headers = dict(headers or {})
        self._ws = None

    async def connect(self) -> None:
        if not HAS_WEBSOCKETS:
            raise RuntimeError("websockets is not installed")
        import websockets  # noqa: F811 - local alias
        self._ws = await websockets.connect(self.url,
                                            extra_headers=self.headers)

    async def send(self, data: Any) -> None:
        if self._ws is None:
            raise RuntimeError("websocket not connected")
        payload = json.dumps(data, default=str) if not isinstance(data, str) else data
        await self._ws.send(payload)

    async def receive(self) -> Any:
        if self._ws is None:
            raise RuntimeError("websocket not connected")
        raw = await self._ws.recv()
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    def set_default_header(self, name: str, value: str) -> None:
        self.headers[name] = value

    def set_default_query_param(self, name: str, value: str) -> None:
        pass
