"""AutoFlow AI - Pagination models."""

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        arbitrary_types_allowed = True


class CursorPage(BaseModel, Generic[T]):
    """Cursor-based pagination."""
    items: List[T]
    cursor: Optional[str] = None
    has_more: bool = False