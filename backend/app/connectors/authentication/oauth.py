"""AutoFlow AI - OAuth2 / OAuth-PKCE authentication (generated from metadata).

Implements authorization-code and PKCE flows with automatic token
refresh, thread-safe refresh, and token caching. Provider-agnostic:
endpoints come from connector metadata.
"""

import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OAuth2Strategy:
    """OAuth2 authorization-code + PKCE strategy."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})
        self._token: Optional[dict] = None
        self._expires_at: float = 0.0
        self._lock = threading.RLock()

    # --- identity ---

    def name(self) -> str:
        return "oauth2"

    def supports_refresh(self) -> bool:
        return bool(self.config.get("requires_refresh", False))

    def get_authorization_url(self, redirect_uri: str,
                              state: str = "",
                              scopes: Optional[list] = None) -> str:
        """Build the authorization URL (PKCE when ``use_pkce`` is set)."""
        import urllib.parse
        base = self.config.get("auth_url", "")
        if not base:
            raise ValueError("no auth_url configured")
        params = {
            "client_id": self.credentials.get("client_id", ""),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or self.config.get("supported_scopes", [])),
            "state": state or uuid.uuid4().hex[:16],
        }
        if self.config.get("use_pkce", False):
            params["code_challenge"] = self._pkce_challenge()
            params["code_challenge_method"] = "S256"
        return base + "?" + urllib.parse.urlencode(params)

    def _pkce_challenge(self) -> str:
        import base64
        import hashlib
        verifier = self.credentials.get(
            "code_verifier", uuid.uuid4().hex + uuid.uuid4().hex)
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def exchange_code(self, code: str, redirect_uri: str,
                      transport: Any = None) -> dict:
        """Exchange an authorization code for tokens."""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.credentials.get("client_id", ""),
            "client_secret": self.credentials.get("client_secret", ""),
        }
        if self.config.get("use_pkce", False):
            payload["code_verifier"] = self.credentials.get(
                "code_verifier", "")
        return self._token_request(payload, transport)

    def refresh(self, connector: Any = None,
                transport: Any = None) -> Optional[str]:
        """Refresh the access token using the refresh token."""
        with self._lock:
            if self._token and time.time() < self._expires_at - 30:
                return (self._token or {}).get("access_token")
            refresh_token = self.credentials.get("refresh_token", "")
            if not refresh_token:
                return None
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.credentials.get("client_id", ""),
                "client_secret": self.credentials.get("client_secret", ""),
            }
            data = self._token_request(payload, transport)
            self._set_token(data)
            return (data or {}).get("access_token")

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        """Ensure a valid token exists; refresh when needed."""
        token = self.credentials.get("access_token", "")
        if self._token and time.time() < self._expires_at - 30:
            token = self._token.get("access_token", token)
        elif self.supports_refresh() and self.credentials.get("refresh_token"):
            token = self.refresh(connector=connector, transport=kwargs.get("transport")) or token
        if not token:
            raise ValueError("no access token available for OAuth2")
        return {"token_type": "Bearer", "access_token": token}

    def apply(self, connector: Any) -> None:
        """Attach the Authorization header to the connector transport."""
        result = self.authenticate(connector, transport=connector.transport)
        if connector.transport is not None:
            connector.transport.set_default_header(
                "Authorization", f"Bearer {result['access_token']}")

    def _token_request(self, payload: dict, transport: Any) -> dict:
        token_url = self.config.get("token_url", "")
        if not token_url:
            raise ValueError("no token_url configured")
        if transport is not None:
            data = transport.request(method="POST", url=token_url,
                                     data=payload, auth_header=False)
            self._set_token(data)
            return data
        # Import-safe fallback using urllib when no transport is injected.
        import json as _json
        import urllib.parse
        import urllib.request
        body = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(
            token_url, data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            data = _json.loads(resp.read().decode())
        self._set_token(data)
        return data

    def _set_token(self, data: dict) -> None:
        if not data:
            return
        self._token = dict(data)
        expires_in = int(data.get("expires_in", 3600))
        self._expires_at = time.time() + expires_in
        if data.get("refresh_token"):
            self.credentials["refresh_token"] = data["refresh_token"]
        if data.get("access_token"):
            self.credentials["access_token"] = data["access_token"]

    def invalidate(self) -> None:
        with self._lock:
            self._token = None
            self._expires_at = 0.0
