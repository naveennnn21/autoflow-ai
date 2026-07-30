"""Tests for dependency injection."""

import pytest
from unittest.mock import AsyncMock
from app.services.di import get_service, SERVICE_REGISTRY


class TestDI:
    """Test dependency injection."""

    def test_service_registry_has_all_services(self):
        """Verify all services are registered."""
        expected = {"Team", "Notification", "OAuthToken", "AuditLog", "User", "WorkflowNode", "Execution", "Workflow", "Project", "Template", "Invoice", "Subscription", "Organization", "APIKey", "MarketplaceItem"}
        assert set(SERVICE_REGISTRY.keys()) == expected

    def test_service_registry_not_empty(self):
        """Verify registry has entries."""
        assert len(SERVICE_REGISTRY) > 0
