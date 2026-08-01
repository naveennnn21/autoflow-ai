"""AutoFlow AI - Permission validation (generated from metadata).

Checks that a tenant's granted scopes cover the required permissions of
an action/trigger, enforces tenant isolation, and emits audit events.
"""

from typing import Any, Dict, List, Optional

from app.connectors.exceptions import PermissionDeniedError, TenantIsolationError


class PermissionValidator:
    """Validates scopes + tenant isolation for connector operations."""

    def __init__(self, events: Any = None) -> None:
        self.events = events

    def check(self, connector: str, action: str, action_def: dict,
              organization_id: str = "", granted_scopes: Optional[List[str]] = None,
              require_tenant: bool = True) -> None:
        """Raise when the tenant lacks required permissions."""
        required = action_def.get("required_permissions", [])
        if not required:
            return
        if not granted_scopes:
            raise PermissionDeniedError(
                f"no scopes granted for action '{action}'",
                connector=connector, action=action)
        missing = [p for p in required if p not in granted_scopes]
        if missing:
            if self.events is not None:
                self.events.error(
                    connector, f"missing permissions: {missing}",
                    action=action, organization_id=organization_id)
            raise PermissionDeniedError(
                f"action '{action}' requires: {missing}",
                connector=connector, action=action)

    def check_tenant(self, owner_organization_id: str,
                     caller_organization_id: str,
                     resource: str = "") -> None:
        """Enforce tenant isolation on a resource."""
        if not caller_organization_id:
            return
        if (owner_organization_id and owner_organization_id != caller_organization_id):
            raise TenantIsolationError(
                f"cross-tenant access to {resource or 'resource'} blocked",
                connector=resource.split(".")[0] if "." in resource else "")

    def scopes_for_role(self, permissions: Dict[str, Any],
                        role: str) -> List[str]:
        """Resolve granted scopes for a role from connector metadata."""
        scopes: List[str] = []
        for op, entries in permissions.items():
            if role in entries:
                scopes.append(op)
        return scopes
