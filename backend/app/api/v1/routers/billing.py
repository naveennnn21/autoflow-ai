"""AutoFlow AI - Billing endpoints from metadata."""

from fastapi import APIRouter, Depends, Query
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

router = APIRouter(prefix="/billing", tags=["Billing"])

@router.get("/subscription")
async def get_subscription(
    current_user: CurrentUser = Depends(get_current_user),
    org_id = Depends(get_current_organization),
):
    """Get current subscription details"""
    return {"status": "ok", "operation": "get_subscription"}
@router.patch("/subscription")
async def update_subscription(
    current_user: CurrentUser = Depends(get_current_user),
    org_id = Depends(get_current_organization),
    body: dict = None,
):
    """Change subscription plan"""
    return {"status": "ok", "operation": "update_subscription"}
@router.post("/subscription/cancel")
async def cancel_subscription(
    current_user: CurrentUser = Depends(get_current_user),
    org_id = Depends(get_current_organization),
):
    """Cancel subscription"""
    return {"status": "ok", "operation": "cancel_subscription"}
@router.get("/invoices")
async def list_invoices(
    current_user: CurrentUser = Depends(get_current_user),
    org_id = Depends(get_current_organization),
):
    """List invoices"""
    return {"status": "ok", "operation": "list_invoices"}
@router.get("/invoices/{id}")
async def get_invoice(
    current_user: CurrentUser = Depends(get_current_user),
    org_id = Depends(get_current_organization),
):
    """Get invoice details"""
    return {"status": "ok", "operation": "get_invoice"}
@router.get("/usage")
async def get_usage(
    current_user: CurrentUser = Depends(get_current_user),
    org_id = Depends(get_current_organization),
):
    """Get current usage metrics"""
    return {"status": "ok", "operation": "get_usage"}
