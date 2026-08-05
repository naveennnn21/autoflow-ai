"""AutoFlow AI - Billing endpoints.

Real implementations backed by the Subscription, Invoice and Execution
repositories. Plan changes and cancellations operate on the
organization's current subscription; invoices are listed per
organization. Stripe webhook handling is intentionally not included in
this deployment.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser, get_current_organization, get_current_user
from app.core.database import get_db
from app.models.subscription import Subscription
from app.repositories.execution import ExecutionRepository
from app.repositories.invoice import InvoiceRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/billing", tags=["Billing"])


def _require_org(org_id: Optional[Any]) -> Any:
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization context for this request",
        )
    return org_id


def _subscription_payload(sub: Subscription) -> Dict[str, Any]:
    return {
        "id": str(sub.id),
        "plan_id": sub.plan_id,
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat()
        if sub.current_period_start else None,
        "current_period_end": sub.current_period_end.isoformat()
        if sub.current_period_end else None,
        "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        "organization_id": str(sub.organization_id),
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    }


async def _get_subscription(db: AsyncSession, org_id: Any) -> Subscription:
    repo = SubscriptionRepository(db)
    sub = await repo.get_by_field("organization_id", org_id)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found for this organization",
        )
    return sub


class SubscriptionUpdateRequest(BaseModel):
    plan_id: Optional[str] = None
    status: Optional[str] = None


@router.get("/subscription", summary="Get current subscription details")
async def get_subscription(
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return the current subscription for the request organization."""
    org_id = _require_org(org_id)
    sub = await _get_subscription(db, org_id)
    return _subscription_payload(sub)


@router.patch("/subscription", summary="Change subscription plan")
async def update_subscription(
    body: SubscriptionUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update plan or status fields on the organization subscription."""
    org_id = _require_org(org_id)
    sub = await _get_subscription(db, org_id)
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nothing to update",
        )
    repo = SubscriptionRepository(db)
    updated = await repo.update(sub.id, changes)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    return _subscription_payload(updated)


@router.post("/subscription/cancel", summary="Cancel subscription")
async def cancel_subscription(
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Mark the organization subscription as cancelled."""
    org_id = _require_org(org_id)
    sub = await _get_subscription(db, org_id)
    repo = SubscriptionRepository(db)
    updated = await repo.update(sub.id, {
        "status": "cancelled",
        "cancelled_at": datetime.now(timezone.utc),
    })
    return _subscription_payload(updated)


@router.get("/invoices", response_model=PaginatedResponse, summary="List invoices")
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    """List invoices for the request organization, newest first."""
    org_id = _require_org(org_id)
    repo = InvoiceRepository(db)
    items, total = await repo.search(
        sort_by="created_at", sort_order="desc",
        page=page, page_size=page_size, organization_id=org_id,
    )
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // max(page_size, 1),
    )


@router.get("/invoices/{id}", summary="Get invoice details")
async def get_invoice(
    id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return a single invoice for the request organization."""
    org_id = _require_org(org_id)
    repo = InvoiceRepository(db)
    invoice = await repo.get(id)
    if invoice is None or str(invoice.organization_id) != str(org_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    return {
        "id": str(invoice.id),
        "subscription_id": str(invoice.subscription_id)
        if invoice.subscription_id else None,
        "amount": invoice.amount,
        "currency": invoice.currency,
        "status": invoice.status,
        "description": invoice.description,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
    }


@router.get("/usage", summary="Get current usage metrics")
async def get_usage(
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return execution and invoice usage counts for the organization."""
    org_id = _require_org(org_id)
    executions = await ExecutionRepository(db).count(organization_id=org_id)
    invoices = await InvoiceRepository(db).count(organization_id=org_id)
    return {
        "organization_id": str(org_id),
        "execution_count": executions,
        "invoice_count": invoices,
        "period": "all-time",
    }
