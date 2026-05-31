from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    routes_aircrafts,
    routes_auth,
    routes_bookings,
    routes_flights,
    routes_generation,
    routes_irops,
    routes_manage_travel,
    routes_validation,
)
from app.core.cache import cache_client
from app.core.config import get_settings
from app.core.logging import request_id_ctx_var, setup_logging
from app.db.base import Base
from app.db.session import engine

settings = get_settings()
setup_logging()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # In development/test we auto-create tables for convenience.
    # In production, rely on Alembic migrations only.
    if settings.environment in {"development", "test"}:
        Base.metadata.create_all(bind=engine)
    await cache_client.connect()
    yield
    await cache_client.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_and_audit_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    token = request_id_ctx_var.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client": request.client.host if request.client else None,
            },
        )
        return response
    finally:
        request_id_ctx_var.reset(token)


@app.exception_handler(Exception)
async def catch_all_exception_handler(_request: Request, exc: Exception):
    logger.exception("unhandled_exception", exc_info=exc)
    if settings.environment == "production":
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    # Preserve FastAPI HTTP status codes (e.g. 401/403/404/409) in production.
    logger.info("http_exception", extra={"status_code": exc.status_code, "detail": exc.detail})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


app.include_router(routes_auth.router, prefix=settings.api_v1_prefix)
app.include_router(routes_generation.router, prefix=settings.api_v1_prefix)
app.include_router(routes_validation.router, prefix=settings.api_v1_prefix)
app.include_router(routes_aircrafts.router, prefix=settings.api_v1_prefix)
app.include_router(routes_flights.router, prefix=settings.api_v1_prefix)
app.include_router(routes_bookings.router, prefix=settings.api_v1_prefix)
app.include_router(routes_manage_travel.router, prefix=settings.api_v1_prefix)
app.include_router(routes_irops.router, prefix=settings.api_v1_prefix)
