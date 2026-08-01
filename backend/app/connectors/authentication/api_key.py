"""AutoFlow AI - API key authentication (generated from metadata)."""

from typing import Any, Dict, Optional


class APIKeyStrategy:
    """API key strategy (header, query, or bearer-style key)."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})

    def name(self) -> str:
        return "api_key"

    def supports_refresh(self) -> bool:
        return False

    def _key(self) -> str:
        for field in ("api_key", "key", "token"):
            if self.credentials.get(field):
                return str(self.credentials[field])
        return ""

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        key = self._key()
        if not key:
            raise ValueError("no api_key credential provided")
        return {"api_key": key}

    def apply(self, connector: Any) -> None:
        key = self._key()
        if not key:
            raise ValueError("no api_key credential provided")
        if connector.transport is None:
            return
        placement = self.config.get("placement", "header")
        header_name = self.config.get("header_name", "X-Api-Key")
        if placement == "query":
            connector.transport.set_default_query_param(
                self.config.get("query_param", "api_key"), key)
        elif placement == "header":
            connector.transport.set_default_header(header_name, key)
        else:  # bearer-style
            connector.transport.set_default_header(
                "Authorization", f"Bearer {key}")

    def invalidate(self) -> None:
        pass
