"""AutoFlow AI - Dependency injection providers."""

from functools import lru_cache
from typing import AsyncGenerator, Any

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

from app.repositories.team import TeamRepository
from app.services.team import TeamService
from app.repositories.notification import NotificationRepository
from app.services.notification import NotificationService
from app.repositories.oauth_token import OAuthTokenRepository
from app.services.oauth_token import OAuthTokenService
from app.repositories.audit_log import AuditLogRepository
from app.services.audit_log import AuditLogService
from app.repositories.user import UserRepository
from app.services.user import UserService
from app.repositories.workflow_node import WorkflowNodeRepository
from app.services.workflow_node import WorkflowNodeService
from app.repositories.execution import ExecutionRepository
from app.services.execution import ExecutionService
from app.repositories.workflow import WorkflowRepository
from app.services.workflow import WorkflowService
from app.repositories.project import ProjectRepository
from app.services.project import ProjectService
from app.repositories.template import TemplateRepository
from app.services.template import TemplateService
from app.repositories.invoice import InvoiceRepository
from app.services.invoice import InvoiceService
from app.repositories.subscription import SubscriptionRepository
from app.services.subscription import SubscriptionService
from app.repositories.organization import OrganizationRepository
from app.services.organization import OrganizationService
from app.repositories.api_key import APIKeyRepository
from app.services.api_key import APIKeyService
from app.repositories.marketplace_item import MarketplaceItemRepository
from app.services.marketplace_item import MarketplaceItemService


# Repository providers

async def get_team_repository(
    db: AsyncSession,
) -> TeamRepository:
    """Dependency provider for TeamRepository."""
    return TeamRepository(db)


async def get_notification_repository(
    db: AsyncSession,
) -> NotificationRepository:
    """Dependency provider for NotificationRepository."""
    return NotificationRepository(db)


async def get_oauth_token_repository(
    db: AsyncSession,
) -> OAuthTokenRepository:
    """Dependency provider for OAuthTokenRepository."""
    return OAuthTokenRepository(db)


async def get_audit_log_repository(
    db: AsyncSession,
) -> AuditLogRepository:
    """Dependency provider for AuditLogRepository."""
    return AuditLogRepository(db)


async def get_user_repository(
    db: AsyncSession,
) -> UserRepository:
    """Dependency provider for UserRepository."""
    return UserRepository(db)


async def get_workflow_node_repository(
    db: AsyncSession,
) -> WorkflowNodeRepository:
    """Dependency provider for WorkflowNodeRepository."""
    return WorkflowNodeRepository(db)


async def get_execution_repository(
    db: AsyncSession,
) -> ExecutionRepository:
    """Dependency provider for ExecutionRepository."""
    return ExecutionRepository(db)


async def get_workflow_repository(
    db: AsyncSession,
) -> WorkflowRepository:
    """Dependency provider for WorkflowRepository."""
    return WorkflowRepository(db)


async def get_project_repository(
    db: AsyncSession,
) -> ProjectRepository:
    """Dependency provider for ProjectRepository."""
    return ProjectRepository(db)


async def get_template_repository(
    db: AsyncSession,
) -> TemplateRepository:
    """Dependency provider for TemplateRepository."""
    return TemplateRepository(db)


async def get_invoice_repository(
    db: AsyncSession,
) -> InvoiceRepository:
    """Dependency provider for InvoiceRepository."""
    return InvoiceRepository(db)


async def get_subscription_repository(
    db: AsyncSession,
) -> SubscriptionRepository:
    """Dependency provider for SubscriptionRepository."""
    return SubscriptionRepository(db)


async def get_organization_repository(
    db: AsyncSession,
) -> OrganizationRepository:
    """Dependency provider for OrganizationRepository."""
    return OrganizationRepository(db)


async def get_api_key_repository(
    db: AsyncSession,
) -> APIKeyRepository:
    """Dependency provider for APIKeyRepository."""
    return APIKeyRepository(db)


async def get_marketplace_item_repository(
    db: AsyncSession,
) -> MarketplaceItemRepository:
    """Dependency provider for MarketplaceItemRepository."""
    return MarketplaceItemRepository(db)

# Service providers

async def get_team_service(
    repository: TeamRepository,
) -> TeamService:
    """Dependency provider for TeamService."""
    return TeamService(repository)


async def get_notification_service(
    repository: NotificationRepository,
) -> NotificationService:
    """Dependency provider for NotificationService."""
    return NotificationService(repository)


async def get_oauth_token_service(
    repository: OAuthTokenRepository,
) -> OAuthTokenService:
    """Dependency provider for OAuthTokenService."""
    return OAuthTokenService(repository)


async def get_audit_log_service(
    repository: AuditLogRepository,
) -> AuditLogService:
    """Dependency provider for AuditLogService."""
    return AuditLogService(repository)


async def get_user_service(
    repository: UserRepository,
) -> UserService:
    """Dependency provider for UserService."""
    return UserService(repository)


async def get_workflow_node_service(
    repository: WorkflowNodeRepository,
) -> WorkflowNodeService:
    """Dependency provider for WorkflowNodeService."""
    return WorkflowNodeService(repository)


async def get_execution_service(
    repository: ExecutionRepository,
) -> ExecutionService:
    """Dependency provider for ExecutionService."""
    return ExecutionService(repository)


async def get_workflow_service(
    repository: WorkflowRepository,
) -> WorkflowService:
    """Dependency provider for WorkflowService."""
    return WorkflowService(repository)


async def get_project_service(
    repository: ProjectRepository,
) -> ProjectService:
    """Dependency provider for ProjectService."""
    return ProjectService(repository)


async def get_template_service(
    repository: TemplateRepository,
) -> TemplateService:
    """Dependency provider for TemplateService."""
    return TemplateService(repository)


async def get_invoice_service(
    repository: InvoiceRepository,
) -> InvoiceService:
    """Dependency provider for InvoiceService."""
    return InvoiceService(repository)


async def get_subscription_service(
    repository: SubscriptionRepository,
) -> SubscriptionService:
    """Dependency provider for SubscriptionService."""
    return SubscriptionService(repository)


async def get_organization_service(
    repository: OrganizationRepository,
) -> OrganizationService:
    """Dependency provider for OrganizationService."""
    return OrganizationService(repository)


async def get_api_key_service(
    repository: APIKeyRepository,
) -> APIKeyService:
    """Dependency provider for APIKeyService."""
    return APIKeyService(repository)


async def get_marketplace_item_service(
    repository: MarketplaceItemRepository,
) -> MarketplaceItemService:
    """Dependency provider for MarketplaceItemService."""
    return MarketplaceItemService(repository)



SERVICE_REGISTRY = {
    "Team": TeamService,
    "Notification": NotificationService,
    "OAuthToken": OAuthTokenService,
    "AuditLog": AuditLogService,
    "User": UserService,
    "WorkflowNode": WorkflowNodeService,
    "Execution": ExecutionService,
    "Workflow": WorkflowService,
    "Project": ProjectService,
    "Template": TemplateService,
    "Invoice": InvoiceService,
    "Subscription": SubscriptionService,
    "Organization": OrganizationService,
    "APIKey": APIKeyService,
    "MarketplaceItem": MarketplaceItemService,
}
