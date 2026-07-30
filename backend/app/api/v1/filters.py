"""AutoFlow AI - Filter and sort models."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class FilterParam(BaseModel):
    """Single filter parameter."""
    field: str
    op: str = Field(default="eq", description="Filter operator: eq, neq, gt, gte, lt, lte, contains, in, between")
    value: Any


class SortParam(BaseModel):
    """Single sort parameter."""
    field: str
    order: str = Field(default="asc", description="Sort order: asc or desc")


class FilterSet(BaseModel):
    """Collection of filters and sorts."""
    filters: List[FilterParam] = []
    sorts: List[SortParam] = []
    search: Optional[str] = None