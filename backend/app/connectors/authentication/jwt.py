"""AutoFlow AI - JWT authentication (generated from metadata).

Signs and validates JWTs. Uses PyJWT when available; falls back to an
HS256 implementation built on stdlib (hmac/sha256/base64/json).
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

# Try optional PyJWT; fall back to stdlib HS256.
try:
    import jwt as pyjwt  # type: ignore
    HAS_PYJWT = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_PYJWT = False


class JWTStrategy:
    """JWT strategy for service-to-service auth."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})
        self._secret = str(credentials.get("jwt_secret", "")) if credentials else ""

    def name(self) -> str:
        return "jwt"

    def supports_refresh(self) -> bool:
        return False

    def sign(self, claims: Optional[dict] = None,
             expires_in: int = 3600) -> str:
        """Sign a JWT (HS256)."""
        payload = dict(claims or {})
        payload.setdefault("iat", int(time.time()))
        payload.setdefault("exp", int(time.time()) + expires_in)
        payload.setdefault("iss", self.credentials.get("client_id", ""))
        if HAS_PYJWT:
            return pyjwt.encode(payload, self._secret, algorithm="HS256")
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"},
                       separators=(",", ":")).encode()).rstrip(b"=").decode()
        body = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=").decode()
        signing_input = f"{header}.{body}"
        sig = base64.urlsafe_b64encode(hmac.new(
            self._secret.encode(), signing_input.encode(),
            hashlib.sha256).digest()).rstrip(b"=").decode()
        return f"{signing_input}.{sig}"

    def verify(self, token: str) -> dict:
        """Verify a JWT and return its payload; raises on failure."""
        if HAS_PYJWT:
            return pyjwt.decode(token, self._secret, algorithms=["HS256"])
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("malformed JWT")
        header, body, sig = parts
        signing_input = f"{header}.{body}"
        expected = base64.urlsafe_b64encode(hmac.new(
            self._secret.encode(), signing_input.encode(),
            hashlib.sha256).digest()).rstrip(b"=").decode()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("invalid JWT signature")
        pad = lambda s: s + "=" * (-len(s) % 4)  # noqa: E731
        payload = json.loads(base64.urlsafe_b64decode(pad(body)).decode())
        if payload.get("exp") and int(payload["exp"]) < int(time.time()):
            raise ValueError("JWT expired")
        return payload

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        token = self.credentials.get("access_token", "")
        if not token:
            token = self.sign()
        return {"token_type": "Bearer", "access_token": token}

    def apply(self, connector: Any) -> None:
        result = self.authenticate(connector)
        if connector.transport is not None:
            connector.transport.set_default_header(
                "Authorization", f"Bearer {result['access_token']}")

    def invalidate(self) -> None:
        pass
