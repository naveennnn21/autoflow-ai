import pathlib
r = pathlib.Path(__file__).resolve().parent.parent

def w(p, c):
    f = r / p
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(c, encoding='utf-8')
    print(f'  OK {p}')

# Main app
w('backend/app/main.py', '''from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.cache import close_cache, init_cache

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await init_db()
    await init_cache()
    if settings.sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.2)
    yield
    await close_db()
    await close_cache()

app = FastAPI(title=settings.app_name, version=settings.app_version, docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Organization-Id"])

@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.app_version}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred", "type": type(exc).__name__})

from app.api.v1.auth import router as auth_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.executions import router as executions_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.billing import router as billing_router

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(workflows_router, prefix=settings.api_v1_prefix)
app.include_router(executions_router, prefix=settings.api_v1_prefix)
app.include_router(monitoring_router, prefix=settings.api_v1_prefix)
app.include_router(billing_router, prefix=settings.api_v1_prefix)
''')

# API routes - Auth
w('backend/app/api/v1/auth.py', '''from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import Organization, OrganizationMember, User
from app.models.user import UserRole
from app.schemas.auth import (
    OrganizationResponse, OrganizationMemberResponse,
    PasswordChange, TokenRefresh, TokenResponse,
    UserCreate, UserLogin, UserResponse
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, auth_service: AuthService = Depends()):
    return await auth_service.register(data)

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, auth_service: AuthService = Depends()):
    return await auth_service.login(data.email, data.password)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefresh, auth_service: AuthService = Depends()):
    return await auth_service.refresh_token(data.refresh_token)

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.get("/organizations", response_model=list[OrganizationResponse])
async def list_organizations(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Organization).join(OrganizationMember).where(OrganizationMember.user_id == current_user.id))
    return [OrganizationResponse.model_validate(o) for o in result.scalars().all()]

@router.get("/organizations/{organization_id}/members", response_model=list[OrganizationMemberResponse])
async def list_organization_members(organization_id: UUID, db=Depends(get_db)):
    result = await db.execute(select(OrganizationMember).where(OrganizationMember.organization_id == organization_id))
    members = result.scalars().all()
    responses = []
    for m in members:
        resp = OrganizationMemberResponse.model_validate(m)
        user_result = await db.execute(select(User).where(User.id == m.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            resp.user = UserResponse.model_validate(user)
        responses.append(resp)
    return responses
''')

# API routes - Workflows
w('backend/app/api/v1/workflows.py', '''from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.middleware.auth import get_current_organization, get_current_user
from app.models.user import User
from app.schemas.workflow import WorkflowCreate, WorkflowListResponse, WorkflowPromptRequest, WorkflowPromptResponse, WorkflowResponse, WorkflowUpdate
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows"])

@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(data: WorkflowCreate, current_user: User = Depends(get_current_user), org_data=Depends(get_current_organization), workflow_service: WorkflowService = Depends()):
    organization, _ = org_data
    return await workflow_service.create_workflow(organization_id=organization.id, user_id=current_user.id, data=data)

@router.post("/generate", response_model=WorkflowPromptResponse)
async def generate_workflow_from_prompt(data: WorkflowPromptRequest, current_user: User = Depends(get_current_user), org_data=Depends(get_current_organization), workflow_service: WorkflowService = Depends()):
    organization, _ = org_data
    workflow, prompt_id = await workflow_service.generate_from_prompt(organization_id=organization.id, user_id=current_user.id, prompt=data.prompt, provider=data.provider, model=data.model)
    return WorkflowPromptResponse(workflow=workflow, prompt_id=prompt_id)

@router.get("", response_model=WorkflowListResponse)
async def list_workflows(status: Optional[str] = Query(None), search: Optional[str] = Query(None), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), org_data=Depends(get_current_organization), workflow_service: WorkflowService = Depends()):
    organization, _ = org_data
    return await workflow_service.list_workflows(organization_id=organization.id, status_filter=status, search=search, page=page, page_size=page_size)

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID, workflow_service: WorkflowService = Depends()):
    return await workflow_service.get_workflow(workflow_id)

@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: UUID, data: WorkflowUpdate, current_user: User = Depends(get_current_user), workflow_service: WorkflowService = Depends()):
    return await workflow_service.update_workflow(workflow_id=workflow_id, data=data, user_id=current_user.id)

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: UUID, workflow_service: WorkflowService = Depends()):
    await workflow_service.delete_workflow(workflow_id)

@router.post("/{workflow_id}/deploy", response_model=WorkflowResponse)
async def deploy_workflow(workflow_id: UUID, current_user: User = Depends(get_current_user), workflow_service: WorkflowService = Depends()):
    return await workflow_service.update_workflow(workflow_id=workflow_id, data=WorkflowUpdate(status="active"), user_id=current_user.id)

@router.post("/{workflow_id}/pause", response_model=WorkflowResponse)
async def pause_workflow(workflow_id: UUID, current_user: User = Depends(get_current_user)
