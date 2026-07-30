import pathlib
r = pathlib.Path(__file__).resolve().parent.parent
def w(p, c):
    f = r / p
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(c, encoding='utf-8')
    print(f'  OK {p}')

w('backend/app/services/auth_service.py', r'''from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.user import Organization, OrganizationMember, User, UserRole, UserStatus
from app.schemas.auth import TokenResponse, UserCreate, UserResponse

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserCreate) -> TokenResponse:
        existing = await self.db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user = User(email=data.email, password_hash=hash_password(data.password), full_name=data.full_name, status=UserStatus.ACTIVE, is_verified=True)
        self.db.add(user)
        await self.db.flush()
        org_name = data.organization_name or f"{data.full_name}'s Organization"
        org_slug = org_name.lower().replace(" ", "-").replace("'", "")[:255]
        organization = Organization(name=org_name, slug=org_slug)
        self.db.add(organization)
        await self.db.flush()
        membership = OrganizationMember(organization_id=organization.id, user_id=user.id, role=UserRole.ADMIN)
        self.db.add(membership)
        return await self._create_token_response(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
        user.last_login_at = datetime.now(timezone.utc)
        return await self._create_token_response(user)

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
            result = await self.db.execute(select(User).where(User.id == UUID(payload.get("sub"))))
            user = result.scalar_one_or_none()
            if not user or user.status != UserStatus.ACTIVE:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
            return await self._create_token_response(user)
        except (ValueError, Exception) as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    async def get_user(self, user_id: UUID) -> UserResponse:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserResponse.model_validate(user)

    async def _create_token_response(self, user: User) -> TokenResponse:
        access_token = create_access_token(subject=str(user.id), extra_claims={"email": user.email, "full_name": user.full_name, "is_superuser": user.is_superuser})
        refresh_token = create_refresh_token(subject=str(user.id))
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, expires_in=1800)
''')

w('backend/app/services/workflow_service.py', r'''from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, WorkflowVersion
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowStepResponse, WorkflowUpdate

class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_workflow(self, organization_id: UUID, user_id: UUID, data: WorkflowCreate) -> WorkflowResponse:
        workflow = Workflow(organization_id=organization_id, name=data.name, description=data.description, tags=data.tags, created_by=user_id)
        self.db.add(workflow)
        await self.db.flush()
        for i, step_data in enumerate(data.steps):
            step = WorkflowStep(workflow_id=workflow.id, name=step_data.name, step_type=step_data.step_type, order=step_data.order or i, config=step_data.config, input_mapping=step_data.input_mapping, output_mapping=step_data.output_mapping, retry_count=step_data.retry_count, retry_delay_ms=step_data.retry_delay_ms, timeout_ms=step_data.timeout_ms, conditions=step_data.conditions)
            self.db.add(step)
        await self._create_version(workflow.id, user_id)
        return await self.get_workflow(workflow.id)

    async def get_workflow(self, workflow_id: UUID) -> WorkflowResponse:
        result = await self.db.execute(select(Workflow).where(Workflow.id == workflow_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        steps_result = await self.db.execute(select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.order))
        steps = steps_result.scalars().all()
        response = WorkflowResponse.model_validate(workflow)
        response.steps = [WorkflowStepResponse.model_validate(s) for s in steps]
        return response

    async def list_workflows(self, organization_id: UUID, status_filter: Optional[str] = None, search: Optional[str] = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        query = select(Workflow).where(Workflow.organization_id == organization_id)
        if status_filter:
            query = query.where(Workflow.status == status_filter)
        if search:
            query = query.where(Workflow.name.ilike(f"%{search}%"))
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0
        query = query.order_by(Workflow.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        workflows = (await self.db.execute(query)).scalars().all()
        return {"items": [WorkflowResponse.model_validate(w) for w in workflows], "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}

    async def update_workflow(self, workflow_id: UUID, data: WorkflowUpdate, user_id: UUID) -> WorkflowResponse:
        result = await self.db.execute(select(Workflow).where(Workflow.id == workflow_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(workflow, field, value)
        if data.status == "active" and workflow.status != "active":
            await self._create_version(workflow.id, user_id)
        return await self.get_workflow(workflow_id)

    async def delete_workflow(self, workflow_id: UUID) -> None:
        result = await self.db.execute(select(Workflow).where(Workflow.id == workflow_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPExcept
