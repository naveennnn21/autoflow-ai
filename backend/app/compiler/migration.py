"""AutoFlow AI - Specification migration (generated from metadata).

Migration rules for Workflow Specifications. Version 1 is the initial
version; future versions register migration functions here and the
``migrate`` helper applies them automatically.
"""

from typing import Any, Callable, Dict, List, Optional

from app.compiler.exceptions import MigrationError, VersionError
from app.compiler.workflow_spec import SUPPORTED_SPEC_VERSIONS

# migration rules: target_version -> function(spec_dict) -> spec_dict
MIGRATION_RULES: Dict[int, Callable[[dict], dict]] = {}


def register_migration(target_version: int,
                       fn: Callable[[dict], dict]) -> None:
    """Register a migration function for a target version."""
    MIGRATION_RULES[int(target_version)] = fn


def migrate(data: Dict[str, Any], from_version: Optional[int] = None,
            to_version: Optional[int] = None) -> Dict[str, Any]:
    """Migrate a spec dict to a target version by applying registered
    rules in ascending order. Unregistered steps are no-ops."""
    if not isinstance(data, dict):
        raise MigrationError("cannot migrate non-dict payload")
    current = int(from_version if from_version is not None
                  else data.get("version", 1))
    target = int(to_version if to_version is not None
                 else max(SUPPORTED_SPEC_VERSIONS))
    if current > target:
        raise MigrationError(
            f"cannot migrate downward: {current} -> {target}")
    if current not in SUPPORTED_SPEC_VERSIONS:
        raise VersionError(f"unsupported source version: {current}")
    # The target may be a registered future version (has a migration rule)
    # even before it is added to SUPPORTED_SPEC_VERSIONS.
    if target not in SUPPORTED_SPEC_VERSIONS and \
            target not in MIGRATION_RULES:
        raise VersionError(f"unsupported target version: {target}")
    migrated = dict(data)
    for version in range(current + 1, target + 1):
        fn = MIGRATION_RULES.get(version)
        if fn is not None:
            migrated = fn(migrated)
        migrated["version"] = version
    return migrated
