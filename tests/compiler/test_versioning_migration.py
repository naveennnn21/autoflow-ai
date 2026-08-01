"""AutoFlow AI - Versioning/migration tests (generated from metadata)."""

import pytest

from app.compiler.exceptions import MigrationError, VersionError
from app.compiler.migration import migrate, register_migration
from app.compiler.versioning import SpecVersionManager
from app.compiler.workflow_spec import SPEC_VERSION, SUPPORTED_SPEC_VERSIONS


def test_spec_version_constants():
    assert SPEC_VERSION == 1
    assert 1 in SUPPORTED_SPEC_VERSIONS


def test_version_manager():
    mgr = SpecVersionManager()
    assert mgr.current_version() == 1
    assert mgr.is_supported(1)
    assert not mgr.is_supported(99)


def test_version_manager_assert():
    mgr = SpecVersionManager()
    with pytest.raises(VersionError):
        mgr.assert_supported(42)


def test_version_manager_report():
    mgr = SpecVersionManager()
    report = mgr.compatibility_report(1)
    assert report["supported"] is True


def test_migrate_same_version():
    result = migrate({"version": 1, "workflow": "w"}, 1, 1)
    assert result["version"] == 1


def test_migrate_downward_raises():
    with pytest.raises(MigrationError):
        migrate({"version": 2}, 2, 1)


def test_migrate_applies_rule():
    def _rule(data):
        data["upgraded"] = True
        return data

    register_migration(2, _rule)
    result = migrate({"version": 1, "workflow": "w"}, 1, 2)
    assert result["version"] == 2
    assert result.get("upgraded") is True


def test_migrate_bad_payload():
    with pytest.raises(MigrationError):
        migrate("nope", 1, 1)
