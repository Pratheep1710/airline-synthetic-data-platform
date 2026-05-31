from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, rate_limit_dependency
from app.core.security import require_scopes
from app.schemas.manage_travel import ManageTravelSchema
from app.services.manage_travel_service import ManageTravelService

router = APIRouter(prefix="/manage-travel", tags=["manage-travel"])


@router.get("/{pnr}", response_model=ManageTravelSchema, dependencies=[Depends(rate_limit_dependency)])
async def get_manage_travel_by_pnr(
    pnr: str,
    dataset_version: str | None = Query(default=None),
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> ManageTravelSchema:
    service = ManageTravelService(db)
    row = await service.get_by_pnr(pnr, dataset_version=dataset_version)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manage travel not found")
    return row
