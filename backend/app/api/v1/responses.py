"""AutoFlow AI - Standard API response models."""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    success: bool = True
    data: Optional[T] = None
    message: str = "Success"


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    code: int = 500
    detail_data: Optional[Any] = None