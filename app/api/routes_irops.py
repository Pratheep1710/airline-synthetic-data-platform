from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_pagination, rate_limit_dependency
from app.core.security import require_scopes
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.irop import IropSchema
from app.services.irop_service import IropService

router = APIRouter(tags=["irops"])


@router.get("/irops", response_model=PaginatedResponse[IropSchema], dependencies=[Depends(rate_limit_dependency)])
async def list_irops(
    pagination: PaginationParams = Depends(get_pagination),
    flight_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> PaginatedResponse[IropSchema]:
    service = IropService(db)
    return await service.list(
        dataset_version=pagination.dataset_version,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=pagination.sort_by,
        sort_dir=pagination.sort_dir,
        filters={"flight_id": flight_id, "event_type": event_type},
    )


@router.get("/irops/{irop_id}", response_model=IropSchema, dependencies=[Depends(rate_limit_dependency)])
async def get_irop(
    irop_id: str,
    dataset_version: str | None = Query(default=None),
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> IropSchema:
    service = IropService(db)
    row = await service.get(irop_id, dataset_version=dataset_version)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IROP not found")
    return row


@router.get(
    "/flights/{flight_id}/irops",
    response_model=list[IropSchema],
    dependencies=[Depends(rate_limit_dependency)],
)
async def list_flight_irops(
    flight_id: str,
    dataset_version: str | None = Query(default=None),
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> list[IropSchema]:
    service = IropService(db)
    rows = await service.by_flight(flight_id=flight_id, dataset_version=dataset_version)
    return rows
