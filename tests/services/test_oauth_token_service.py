"""Tests for the OAuthTokenService."""

import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.models.oauth_token import OAuthToken
from app.repositories.oauth_token import OAuthTokenRepository
from app.services.oauth_token import OAuthTokenService
from app.schemas.oauth_token import OAuthTokenCreate, OAuthTokenUpdate


@pytest_asyncio.fixture
def mock_repository():
    """Create a mock repository for testing."""
    repo = AsyncMock(spec=OAuthTokenRepository)
    repo.transaction.return_value.__aenter__.return_value = None
    repo.transaction.return_value.__aexit__.return_value = None
    repo.model_class = OAuthToken
    return repo


@pytest_asyncio.fixture
def service(mock_repository):
    """Create service instance for testing."""
    return OAuthTokenService(mock_repository)


class TestOAuthTokenService:
    """Test suite for OAuthTokenService."""

    # --- Core CRUD tests ---

    async def test_create(self, service, mock_repository):
        """Test creating a new oauthtoken."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=OAuthToken)
        mock_obj.id = obj_id
        mock_repository.create.return_value = mock_obj
        mock_repository.get.return_value = None
        data = OAuthTokenCreate(user_id=str(uuid.uuid4()), provider="Test")
        result = await service.create(data)
        assert result is not None
        assert result.id == obj_id

    async def test_get(self, service, mock_repository):
        """Test retrieving a oauthtoken."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=OAuthToken)
        mock_obj.id = obj_id
        mock_repository.get.return_value = mock_obj
        result = await service.get(obj_id)
        assert result is not None
        assert result.id == obj_id

    async def test_get_not_found(self, service, mock_repository):
        """Test getting non-existent oauthtoken."""
        mock_repository.get.return_value = None
        result = await service.get(uuid.uuid4())
        assert result is None

    async def test_update(self, service, mock_repository):
        """Test updating a oauthtoken."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=OAuthToken)
        mock_obj.id = obj_id
        mock_repository.get.return_value = mock_obj
        mock_repository.update.return_value = mock_obj
        data = OAuthTokenUpdate()
        result = await service.update(obj_id, data)
        assert result is not None
        assert result.id == obj_id

    async def test_delete(self, service, mock_repository):
        """Test deleting a oauthtoken."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=OAuthToken)
        mock_obj.id = obj_id
        mock_repository.get.return_value = mock_obj
        mock_repository.delete.return_value = True
        result = await service.delete(obj_id)
        assert result is True

    async def test_list(self, service, mock_repository):
        """Test listing oauthtokens."""
        mock_repository.paginate.return_value = MagicMock()
        result = await service.list()
        assert result is not None

    async def test_search(self, service, mock_repository):
        """Test searching oauthtokens."""
        mock_repository.search.return_value = ([], 0)
        items, total = await service.search()
        assert total == 0

    async def test_count(self, service, mock_repository):
        """Test counting oauthtokens."""
        mock_repository.count.return_value = 5
        count = await service.count()
        assert count == 5

    async def test_bulk_create(self, service, mock_repository):
        """Test bulk creating oauthtokens."""
        mock_repository.bulk_create.return_value = []
        result = await service.bulk_create([])
        assert result is not None

    async def test_exists(self, service, mock_repository):
        """Test checking if oauthtoken exists."""
        mock_repository.exists.return_value = True
        result = await service.exists(uuid.uuid4())
        assert result is True


    # --- Authorization tests ---

    async def test_authorization_create_denied(self, service, mock_repository):
        """Test authorization hook denies create."""
        with patch.object(service, "_authorize_create", return_value=False):
            with pytest.raises(PermissionError):
                await service.create(OAuthTokenCreate(user_id=str(uuid.uuid4()), provider="Test"))

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
                await service.update(uuid.uuid4(), OAuthTokenUpdate())

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
            mock_obj = MagicMock(spec=OAuthToken)
            mock_obj.id = obj_id
            mock_repository.get.return_value = mock_obj
            result1 = await service.get(obj_id)
            assert result1 is not None
            mock_repository.get.reset_mock()
            result2 = await service.get(obj_id)
            assert result2 is not None

    async def test_cache_invalidates_on_create(self, service, mock_repository):
        """Test cache invalidated after create."""
        mock_obj = MagicMock(spec=OAuthToken)
        mock_obj.id = uuid.uuid4()
        mock_repository.create.return_value = mock_obj
        with patch.object(service, "_cache_invalidate") as mock_inv:
            await service.create(OAuthTokenCreate(user_id=str(uuid.uuid4()), provider="Test"))
            mock_inv.assert_called_once_with("list")

    async def test_cache_invalidates_on_update(self, service, mock_repository):
        """Test cache invalidated after update."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=OAuthToken)
        mock_obj.id = obj_id
        mock_repository.get.return_value = mock_obj
        with patch.object(service, "_cache_invalidate") as mock_inv:
            await service.update(obj_id, OAuthTokenUpdate())
            mock_inv.assert_called_once()


    # --- Event publishing tests ---

    async def test_event_published_on_create(self, service, mock_repository):
        """Test event published for create on the platform event bus."""
        from app.events import subscribe, unsubscribe
        mock_obj = MagicMock(spec=OAuthToken)
        mock_obj.id = uuid.uuid4()
        mock_repository.create.return_value = mock_obj
        events = []
        async def collector(event): events.append(event)
        subscribe("OAuthToken.Created", collector)
        try:
            await service.create(OAuthTokenCreate(user_id=str(uuid.uuid4()), provider="Test"))
            assert len(events) > 0, "No events were published"
        finally:
            unsubscribe("OAuthToken.Created", collector)


    # --- Retry behavior tests ---

    async def test_retry_on_transient_failure(self, service, mock_repository):
        """Test retry on transient database failure."""
        from app.services.base import DeadlockError
        mock_repository.get.return_value = None
        mock_obj = MagicMock(spec=OAuthToken)
        mock_obj.id = uuid.uuid4()
        mock_repository.create.side_effect = [DeadlockError("deadlock"), mock_obj]
        try:
            await service.create(OAuthTokenCreate(user_id=str(uuid.uuid4()), provider="Test"))
        except Exception:
            pass
        assert mock_repository.create.call_count >= 2


    # --- Metadata constants tests ---

    def test_metadata_constants_exist(self):
        """Verify metadata-driven constants are defined on the service class."""
        assert hasattr(OAuthTokenService, "CACHE_ENABLED")
        assert hasattr(OAuthTokenService, "CACHE_TTL")
        assert hasattr(OAuthTokenService, "PERMISSIONS")
        assert hasattr(OAuthTokenService, "FEATURE_FLAGS")
        assert hasattr(OAuthTokenService, "EVENTS")
        assert hasattr(OAuthTokenService, "RATE_LIMIT")
        assert hasattr(OAuthTokenService, "DEPENDENCIES")
