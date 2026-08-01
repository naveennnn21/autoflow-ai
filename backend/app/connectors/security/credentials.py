"""AutoFlow AI - Credential store (generated from metadata).

Multi-tenant credential store with rotation and versioning. Credential
values are encrypted at rest via :class:`SecretManager` and only
decrypted on explicit read.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.connectors.security.secrets import SecretManager


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CredentialStore:
    """Tenant-scoped store for connector credentials."""

    def __init__(self, secret_manager: Optional[SecretManager] = None) -> None:
        self.secrets = secret_manager or SecretManager()
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _key(organization_id: str, connector: str) -> str:
        return f"{organization_id or '*'}:{connector}"

    def save(self, organization_id: str, connector: str,
             credentials: Dict[str, Any]) -> str:
        """Store credentials for a tenant + connector; returns version id."""
        version = uuid.uuid4().hex[:12]
        encrypted = {
            k: self.secrets.encrypt(v) if isinstance(v, str) else v
            for k, v in credentials.items()
        }
        with self._lock:
            key = self._key(organization_id, connector)
            entry = self._store.get(key, {
                "organization_id": organization_id,
                "connector": connector,
                "versions": {},
                "active_version": None,
            })
            entry["versions"][version] = {
                "version": version,
                "encrypted": encrypted,
                "created_at": _now_utc().isoformat(),
            }
            entry["active_version"] = version
            self._store[key] = entry
        return version

    def get(self, organization_id: str, connector: str,
            version: Optional[str] = None) -> Dict[str, Any]:
        """Return decrypted credentials (active version by default)."""
        with self._lock:
            key = self._key(organization_id, connector)
            entry = self._store.get(key)
            if entry is None:
                return {}
            version = version or entry.get("active_version")
            if version is None or version not in entry.get("versions", {}):
                return {}
            encrypted = entry["versions"][version]["encrypted"]
            return {
                k: self.secrets.decrypt(v) if isinstance(v, str)
                and (v.startswith("f:") or v.startswith("x:")) else v
                for k, v in encrypted.items()
            }

    def rotate(self, organization_id: str, connector: str,
               new_credentials: Dict[str, Any]) -> Optional[str]:
        """Rotate to a new credential version; returns the new version id."""
        return self.save(organization_id, connector, new_credentials)

    def list_versions(self, organization_id: str,
                      connector: str) -> list:
        with self._lock:
            entry = self._store.get(self._key(organization_id, connector))
            if entry is None:
                return []
            return sorted(
                entry.get("versions", {}).keys(),
                key=lambda v: entry["versions"][v]["created_at"],
                reverse=True,
            )

    def delete(self, organization_id: str, connector: str) -> bool:
        with self._lock:
            return self._store.pop(self._key(organization_id, connector),
                                   None) is not None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
