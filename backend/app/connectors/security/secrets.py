"""AutoFlow AI - Secret management (generated from metadata).

Encrypts/decrypts credential material at rest. Uses Fernet symmetric
encryption when ``cryptography`` is available; otherwise falls back to
a deterministic XOR obfuscation keyed by an environment secret so the
framework remains import-safe without optional dependencies.
"""

import base64
import hashlib
import os
from typing import Optional

# Try optional cryptography; fall back to XOR obfuscation.
try:
    from cryptography.fernet import Fernet, InvalidToken  # type: ignore
    HAS_FERNET = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_FERNET = False


def _default_key() -> str:
    """Derive a stable key from the environment (or a dev fallback)."""
    return os.environ.get("AUTOFLOW_SECRET_KEY", "autoflow-dev-secret-key")


class SecretManager:
    """Encrypts and decrypts connector credentials."""

    def __init__(self, key: Optional[str] = None) -> None:
        self.key = key or _default_key()
        self._fernet = None
        if HAS_FERNET:
            try:
                encoded = base64.urlsafe_b64encode(
                    hashlib.sha256(self.key.encode()).digest())
                self._fernet = Fernet(encoded)
            except Exception:  # noqa: BLE001 - fall back below
                self._fernet = None

    @property
    def using_fernet(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a secret string; returns a portable token."""
        if self._fernet is not None:
            return "f:" + self._fernet.encrypt(plaintext.encode()).decode()
        return "x:" + self._xor(plaintext)

    def decrypt(self, token: str) -> str:
        """Decrypt a token produced by :meth:`encrypt`."""
        if token.startswith("f:") and self._fernet is not None:
            try:
                return self._fernet.decrypt(token[2:].encode()).decode()
            except InvalidToken as exc:  # pragma: no cover - bad key/token
                raise ValueError("cannot decrypt secret") from exc
        if token.startswith("x:"):
            return self._xor(token[2:])
        raise ValueError("unsupported secret token format")

    def _xor(self, plaintext: str) -> str:
        """Deterministic XOR obfuscation keyed by self.key."""
        key_bytes = hashlib.sha256(self.key.encode()).digest()
        data = plaintext.encode()
        encoded = bytes(b ^ key_bytes[i % len(key_bytes)]
                        for i, b in enumerate(data))
        return base64.urlsafe_b64encode(encoded).decode()

    def mask(self, value: str, visible: int = 4) -> str:
        """Return a masked preview of a secret (e.g. ``sk_****abcd``)."""
        if not value:
            return ""
        if len(value) <= visible:
            return "*" * len(value)
        return value[:visible] + "*" * max(len(value) - visible, 4)
