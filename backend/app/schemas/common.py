# ---------------------------------------------------------------------------
# Common schemas
# ---------------------------------------------------------------------------
from pydantic import BaseModel
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")

class PaginationParams:
    page: int = 1
    page_size: int = 20

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

class FilterRequest(BaseModel):
    field: str
    operator: str  # eq, neq, gt, gte, lt, lte, contains, in
    value: Any

class SearchRequest(BaseModel):
    query: str
    filters: List[FilterRequest] = []
    sort_by: Optional[str] = None
    sort_order: str = "asc"
    page: int = 1
    page_size: int = 20
