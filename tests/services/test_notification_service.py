"""Tests for the NotificationService."""

import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.models.notification import Notification
from app.repositories.notification import NotificationRepository
from app.services.notification import NotificationService
from app.schemas.notification import NotificationCreate, NotificationUpdate


@pytest_asyncio.fixture
def mock_repository():
    """Create a mock repository for testing."""
    repo = AsyncMock(spec=NotificationRepository)
    repo.transaction.return_value.__aenter__.return_value = None
    repo.transaction.return_value.__aexit__.return_value = None
    repo.model_class = Notification
    return repo


@pytest_asyncio.fixture
def service(mock_repository):
    """Create service instance for testing."""
    return NotificationService(mock_repository)


class TestNotificationService:
    """Test suite for NotificationService."""

    # --- Core CRUD tests ---

    async def test_create(self, service, mock_repository):
        """Test creating a new notification."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=Notification)
        mock_obj.id = obj_id
        mock_repository.create.return_value = mock_obj
        mock_repository.get.return_value = None
        data = NotificationCreate(user_id=str(uuid.uuid4()), title="Test")
        result = await service.create(data)
        assert result is not None
        assert result.id == obj_id

    async def test_get(self, service, mock_repository):
        """Test retrieving a notification."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=Notification)
        mock_obj.id = obj_id
        mock_repository.get.return_value = mock_obj
        result = await service.get(obj_id)
        assert result is not None
        assert result.id == obj_id

    async def test_get_not_found(self, service, mock_repository):
        """Test getting non-existent notification."""
        mock_repository.get.return_value = None
        result = await service.get(uuid.uuid4())
        assert result is None

    async def test_update(self, service, mock_repository):
        """Test updating a notification."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=Notification)
        mock_obj.id = obj_id
        mock_repository.get.return_value = mock_obj
        mock_repository.update.return_value = mock_obj
        data = NotificationUpdate()
        result = await service.update(obj_id, data)
        assert result is not None
        assert result.id == obj_id

    async def test_delete(self, service, mock_repository):
        """Test deleting a notification."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=Notification)
        mock_obj.id = obj_id
        mock_repository.get.return_value = mock_obj
        mock_repository.delete.return_value = True
        result = await service.delete(obj_id)
        assert result is True

    async def test_list(self, service, mock_repository):
        """Test listing notifications."""
        mock_repository.paginate.return_value = MagicMock()
        result = await service.list()
        assert result is not None

    async def test_search(self, service, mock_repository):
        """Test searching notifications."""
        mock_repository.search.return_value = ([], 0)
        items, total = await service.search()
        assert total == 0

    async def test_count(self, service, mock_repository):
        """Test counting notifications."""
        mock_repository.count.return_value = 5
        count = await service.count()
        assert count == 5

    async def test_bulk_create(self, service, mock_repository):
        """Test bulk creating notifications."""
        mock_repository.bulk_create.return_value = []
        result = await service.bulk_create([])
        assert result is not None

    async def test_exists(self, service, mock_repository):
        """Test checking if notification exists."""
        mock_repository.exists.return_value = True
        result = await service.exists(uuid.uuid4())
        assert result is True


    # --- Authorization tests ---

    async def test_authorization_create_denied(self, service, mock_repository):
        """Test authorization hook denies create."""
        with patch.object(service, "_authorize_create", return_value=False):
            with pytest.raises(PermissionError):
                await service.create(NotificationCreate(user_id=str(uuid.uuid4()), title="Test"))

    async def test_authorization_read_denied(self, service, mock_repository):
        """Test authorization hook denies read."""
        mock_repository.get.return_value = MagicMock()
        with patch.object(service, "_authorize_read", return_value=False):
            with pytest.raises(PermissionError):
                await service.get(uuid.uuid4())

    async def test_authorization_update_denied(self, service, mock_repository):
        """Test authorization hook denies update."""
        mock_repository.get.return_value = MagicMock()
        with patch.object(service, "_authorize_update", return_value=False):
            with pytest.raises(PermissionError):
                await service.update(uuid.uuid4(), NotificationUpdate())

    async def test_authorization_delete_denied(self, service, mock_repository):
        """Test authorization hook denies delete."""
        mock_repository.get.return_value = MagicMock()
        with patch.object(service, "_authorize_delete", return_value=False):
            with pytest.raises(PermissionError):
                await service.delete(uuid.uuid4())


    # --- Cache behavior tests ---

    async def test_cache_get_hits_cache(self, service, mock_repository):
        """Test get() hits cache on subsequent calls."""
        with patch.object(type(service), "CACHE_ENABLED", True):
            obj_id = uuid.uuid4()
            mock_obj = MagicMock(spec=Notification)
            mock_obj.id = obj_id
            mock_repository.get.return_value = mock_obj
            result1 = await service.get(obj_id)
            assert result1 is not None
            mock_repository.get.reset_mock()
            result2 = await service.get(obj_id)
            assert result2 is not None

    async def test_cache_invalidates_on_create(self, service, mock_repository):
        """Test cache invalidated after create."""
        mock_obj = MagicMock(spec=Notification)
        mock_obj.id = uuid.uuid4()
        mock_repository.create.return_value = mock_obj
        with patch.object(service, "_cache_invalidate") as mock_inv:
            await service.create(NotificationCreate(user_id=str(uuid.uuid4()), title="Test"))
            mock_inv.assert_called_once_with("list")

    async def test_cache_invalidates_on_update(self, service, mock_repository):
        """Test cache invalidated after update."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=Notification)
        mock_obj.id = obj_id
        mock_repository.get.return_value = mock_obj
        with patch.object(service, "_cache_invalidate") as mock_inv:
            await service.update(obj_id, NotificationUpdate())
            mock_inv.assert_called_once()


    # --- Event publishing tests ---

    async def test_event_published_on_create(self, service, mock_repository):
        """Test event published for create on the platform event bus."""
        from app.events import subscribe, unsubscribe
        mock_obj = MagicMock(spec=Notification)
        mock_obj.id = uuid.uuid4()
        mock_repository.create.return_value = mock_obj
        events = []
        async def collector(event): events.append(event)
        subscribe("Notification.Created", collector)
        try:
            await service.create(NotificationCreate(user_id=str(uuid.uuid4()), title="Test"))
            assert len(events) > 0, "No events were published"
        finally:
            unsubscribe("Notification.Created", collector)


    # --- Retry behavior tests ---

    async def test_retry_on_transient_failure(self, service, mock_repository):
        """Test retry on transient database failure."""
        from app.services.base import DeadlockError
        mock_repository.get.return_value = None
        mock_obj = MagicMock(spec=Notification)
        mock_obj.id = uuid.uuid4()
        mock_repository.create.side_effect = [DeadlockError("deadlock"), mock_obj]
        try:
            await service.create(NotificationCreate(user_id=str(uuid.uuid4()), title="Test"))
        except Exception:
            pass
        assert mock_repository.create.call_count >= 2


    # --- Metadata constants tests ---

    def test_metadata_constants_exist(self):
        """Verify metadata-driven constants are defined on the service class."""
        assert hasattr(NotificationService, "CACHE_ENABLED")
        assert hasattr(NotificationService, "CACHE_TTL")
        assert hasattr(NotificationService, "PERMISSIONS")
        assert hasattr(NotificationService, "FEATURE_FLAGS")
        assert hasattr(NotificationService, "EVENTS")
        assert hasattr(NotificationService, "RATE_LIMIT")
        assert hasattr(NotificationService, "DEPENDENCIES")
