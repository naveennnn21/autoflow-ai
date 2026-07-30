"""AutoFlow AI - API exception handlers."""

import logging
from typing import Any, Callable
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: int = 500, detail: Any = None):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", detail: Any = None):
        super().__init__(message, code=404, detail=detail)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists", detail: Any = None):
        super().__init__(message, code=409, detail=detail)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized", detail: Any = None):
        super().__init__(message, code=401, detail=detail)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden", detail: Any = None):
        super().__init__(message, code=403, detail=detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(status_code=exc.code, content={"detail": exc.message})

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": "Validation error", "errors": exc.errors()})

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        return JSONResponse(status_code=409, content={"detail": "Resource conflict"})

    @app.exception_handler(SQLAlchemyError)
    async def db_handler(request: Request, exc: SQLAlchemyError):
        return JSONResponse(status_code=500, content={"detail": "Database error"})