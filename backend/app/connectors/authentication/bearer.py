"""AutoFlow AI - Bearer token authentication (generated from metadata)."""

from typing import Any, Dict, Optional


class BearerStrategy:
    """Static bearer token strategy."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})

    def name(self) -> str:
        return "bearer"

    def supports_refresh(self) -> bool:
        return False

    def _token(self) -> str:
        for field in ("bearer_token", "access_token", "token"):
            if self.credentials.get(field):
                return str(self.credentials[field])
        return ""

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        token = self._token()
        if not token:
            raise ValueError("no bearer token credential provided")
        return {"token_type": "Bearer", "access_token": token}

    def apply(self, connector: Any) -> None:
        token = self._token()
        if not token:
            raise ValueError("no bearer token credential provided")
        if connector.transport is not None:
            connector.transport.set_default_header(
                "Authorization", f"Bearer {token}")

    def invalidate(self) -> None:
        pass
