"""AutoFlow AI - Connector registry endpoints.

Exposes the connector catalog (marketplace items of type "connector")
to the frontend Marketplace. The catalog is stored in the database via
the MarketplaceItem entity - the same registry the AI planner consumes
through ``app.connectors`` - so the marketplace is never driven by
hardcoded frontend data.

Endpoints
---------
- GET /connectors            list connectors (paginated, filterable)
- GET /connectors/{slug}     connector detail (404 when unknown)
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser, get_current_organization, get_current_user
from app.core.database import get_db
from app.models.marketplace_item import MarketplaceItem
from app.repositories.marketplace_item import MarketplaceItemRepository

router = APIRouter(prefix="/connectors", tags=["Connectors"])


def _safe(value: Any, default: Any = None) -> Any:
    return value if value is not None else default


def _connector_payload(item: MarketplaceItem) -> Dict[str, Any]:
    """Map a MarketplaceItem row into the frontend Connector shape."""
    cfg = item.config if isinstance(item.config, dict) else {}
    actions = [
        {
            "id": a.get("id", ""),
            "name": a.get("name", ""),
            "description": a.get("description", ""),
            "inputs": a.get("inputs", []),
            "outputs": a.get("outputs", []),
            "kind": a.get("kind", "write"),
        }
        for a in (cfg.get("actions") or [])
        if isinstance(a, dict)
    ]
    triggers = [
        {
            "id": t.get("id", ""),
            "name": t.get("name", ""),
            "description": t.get("description", ""),
            "kind": t.get("kind", "manual"),
        }
        for t in (cfg.get("triggers") or [])
        if isinstance(t, dict)
    ]
    health = _safe(cfg.get("health"), "unknown")
    if health not in ("healthy", "degraded", "down"):
        health = "unknown"
    return {
        "id": item.slug,
        "slug": item.slug,
        "name": item.name,
        "category": _safe(item.category, "General"),
        "description": _safe(item.description, ""),
        "logo": _safe(cfg.get("logo"), "plug"),
        "color": _safe(cfg.get("color"), "#6366f1"),
        "auth": _safe(cfg.get("auth"), "none"),
        "scopes": cfg.get("scopes") or [],
        "actions": actions,
        "triggers": triggers,
        "rateLimit": _safe(cfg.get("rateLimit"), "—"),
        "health": health,
        "rating": item.rating if item.rating is not None else 0.0,
        "installs": item.download_count or 0,
        "installed": False,
        "verified": bool(item.is_verified),
        "popular": bool(cfg.get("popular")),
        "tags": cfg.get("tags") or [],
        "version": _safe(item.version, "1.0.0"),
        "capabilities": {
            "actions": len(actions) > 0,
            "triggers": len(triggers) > 0,
            "webhook": any(t.get("kind") == "webhook" for t in triggers),
            "polling": any(t.get("kind") == "polling" for t in triggers),
        },
    }


@router.get("", summary="List connectors from the registry")
async def list_connectors(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search name/description/category"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return the connector catalog as paginated marketplace items."""
    repo = MarketplaceItemRepository(db)
    filters: List[dict] = [{"field": "type", "operator": "eq", "value": "connector"}]
    if category:
        filters.append({"field": "category", "operator": "eq", "value": category})
    items, total = await repo.search(
        query=search,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [_connector_payload(it) for it in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // max(page_size, 1)),
    }


@router.get("/{slug}", summary="Get connector detail by slug")
async def get_connector(
    slug: str,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return a single connector's detail by its slug."""
    repo = MarketplaceItemRepository(db)
    item = await repo.get_by_slug(slug)
    if item is None or (item.type or "") != "connector":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found",
        )
    return _connector_payload(item)
