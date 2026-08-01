from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from app.middleware.manager import register_middleware
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
register_middleware(app)

@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.app_version}

from app.api.v1 import api_v1_router
app.include_router(api_v1_router)
