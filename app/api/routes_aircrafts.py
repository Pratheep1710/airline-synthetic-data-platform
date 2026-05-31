from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_pagination, rate_limit_dependency
from app.core.security import require_scopes
from app.schemas.aircraft import AircraftSchema
from app.schemas.common import PaginatedResponse, PaginationParams
from app.services.aircraft_service import AircraftService

router = APIRouter(prefix="/aircrafts", tags=["aircrafts"])


@router.get("", response_model=PaginatedResponse[AircraftSchema], dependencies=[Depends(rate_limit_dependency)])
async def list_aircrafts(
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> PaginatedResponse[AircraftSchema]:
    service = AircraftService(db)
    return await service.list(
        dataset_version=pagination.dataset_version,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=pagination.sort_by,
        sort_dir=pagination.sort_dir,
        filters={"status": status_filter},
    )


@router.get("/{aircraft_id}", response_model=AircraftSchema, dependencies=[Depends(rate_limit_dependency)])
async def get_aircraft(
    aircraft_id: str,
    dataset_version: str | None = Query(default=None),
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> AircraftSchema:
    service = AircraftService(db)
    row = await service.get(aircraft_id, dataset_version=dataset_version)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aircraft not found")
    return row
