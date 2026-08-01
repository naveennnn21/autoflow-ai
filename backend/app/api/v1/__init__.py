"""API v1 registry."""
from fastapi import APIRouter
from app.api.v1.routers.team import router as team_router
from app.api.v1.routers.notification import router as notification_router
from app.api.v1.routers.oauth_token import router as oauth_token_router
from app.api.v1.routers.audit_log import router as audit_log_router
from app.api.v1.routers.user import router as user_router
from app.api.v1.routers.workflow_node import router as workflow_node_router
from app.api.v1.routers.execution import router as execution_router
from app.api.v1.routers.workflow import router as workflow_router
from app.api.v1.routers.project import router as project_router
from app.api.v1.routers.template import router as template_router
from app.api.v1.routers.invoice import router as invoice_router
from app.api.v1.routers.subscription import router as subscription_router
from app.api.v1.routers.organization import router as organization_router
from app.api.v1.routers.api_key import router as api_key_router
from app.api.v1.routers.marketplace_item import router as marketplace_item_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.billing import router as billing_router
from app.api.v1.routers.monitoring import router as monitoring_router


# Create versioned router
api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(team_router)
api_v1_router.include_router(notification_router)
api_v1_router.include_router(oauth_token_router)
api_v1_router.include_router(audit_log_router)
api_v1_router.include_router(user_router)
api_v1_router.include_router(workflow_node_router)
api_v1_router.include_router(execution_router)
api_v1_router.include_router(workflow_router)
api_v1_router.include_router(project_router)
api_v1_router.include_router(template_router)
api_v1_router.include_router(invoice_router)
api_v1_router.include_router(subscription_router)
api_v1_router.include_router(organization_router)
api_v1_router.include_router(api_key_router)
api_v1_router.include_router(marketplace_item_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(billing_router)
api_v1_router.include_router(monitoring_router)