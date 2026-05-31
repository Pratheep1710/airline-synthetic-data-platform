from __future__ import annotations

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import rate_limiter
from app.db.session import get_db
from app.schemas.common import PaginationParams


def get_pagination(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=get_settings().default_page_size, ge=1, le=get_settings().max_page_size),
    sort_by: str | None = Query(default=None),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    dataset_version: str | None = Query(default=None),
) -> PaginationParams:
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        dataset_version=dataset_version,
    )


def db_session(db: Session = Depends(get_db)) -> Session:
    return db


async def rate_limit_dependency(request: Request) -> None:
    await rate_limiter.check(request)
