"""AutoFlow AI - Specification version manager (generated from metadata).

Manages the Workflow Specification version: the current version,
supported versions, and backward/forward compatibility rules.
"""

from typing import Any, Dict, List, Optional

from app.compiler.exceptions import VersionError
from app.compiler.workflow_spec import SPEC_VERSION, SUPPORTED_SPEC_VERSIONS


class SpecVersionManager:
    """Version management for Workflow Specifications."""

    def __init__(self, supported: Optional[List[int]] = None):
        self.supported = list(supported or SUPPORTED_SPEC_VERSIONS)
        self.current = max(self.supported) if self.supported else SPEC_VERSION

    def current_version(self) -> int:
        """Return the current specification version."""
        return self.current

    def is_supported(self, version: int) -> bool:
        """Return True when the version is supported."""
        return int(version) in self.supported

    def assert_supported(self, version: int) -> None:
        """Raise VersionError when the version is not supported."""
        if not self.is_supported(version):
            raise VersionError(
                f"unsupported specification version {version}; "
                f"supported: {self.supported}")

    def is_backward_compatible(self, from_version: int,
                               to_version: int) -> bool:
        """vN consumers may read specs produced by v(N+1)? No — older
        consumers cannot read newer specs. Backward compatibility means
        a new reader can read old specs (from_version < to_version)."""
        return int(from_version) <= int(to_version)

    def is_forward_compatible(self, from_version: int,
                              to_version: int) -> bool:
        """Forward compatibility: old reader + new spec. Not guaranteed."""
        return int(from_version) == int(to_version)

    def compatibility_report(self, version: int) -> Dict[str, Any]:
        """Describe compatibility of a version against the current one."""
        version = int(version)
        return {
            "version": version,
            "supported": self.is_supported(version),
            "current": self.current,
            "backward_compatible": self.is_backward_compatible(
                version, self.current),
            "forward_compatible": self.is_forward_compatible(
                version, self.current),
            "needs_migration": self.is_supported(version)
            and version < self.current,
        }
