"""AutoFlow AI - HTTP Basic authentication (generated from metadata)."""

import base64
from typing import Any, Dict, Optional


class BasicAuthStrategy:
    """Username/password basic auth strategy."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})

    def name(self) -> str:
        return "basic"

    def supports_refresh(self) -> bool:
        return False

    def _creds(self) -> tuple:
        username = self.credentials.get("username", "") or             self.credentials.get("user", "")
        password = self.credentials.get("password", "") or             self.credentials.get("pass", "")
        return str(username), str(password)

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        username, password = self._creds()
        raw = f"{username}:{password}"
        encoded = base64.b64encode(raw.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    def apply(self, connector: Any) -> None:
        if connector.transport is None:
            return
        result = self.authenticate(connector)
        connector.transport.set_default_header(
            "Authorization", result["Authorization"])

    def invalidate(self) -> None:
        pass
