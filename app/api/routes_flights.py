from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_pagination, rate_limit_dependency
from app.core.security import require_scopes
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.flight import FlightSchema, FlightSearchRequest
from app.services.flight_service import FlightService

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("", response_model=PaginatedResponse[FlightSchema], dependencies=[Depends(rate_limit_dependency)])
async def list_flights(
    pagination: PaginationParams = Depends(get_pagination),
    origin: str | None = Query(default=None),
    destination: str | None = Query(default=None),
    selling_status: str | None = Query(default=None),
    operational_status: str | None = Query(default=None),
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> PaginatedResponse[FlightSchema]:
    service = FlightService(db)
    return await service.list(
        dataset_version=pagination.dataset_version,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=pagination.sort_by,
        sort_dir=pagination.sort_dir,
        filters={
            "origin": origin,
            "destination": destination,
            "selling_status": selling_status,
            "operational_status": operational_status,
        },
    )


@router.get("/{flight_id}", response_model=FlightSchema, dependencies=[Depends(rate_limit_dependency)])
async def get_flight(
    flight_id: str,
    dataset_version: str | None = Query(default=None),
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> FlightSchema:
    service = FlightService(db)
    row = await service.get(flight_id, dataset_version=dataset_version)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")
    return row


@router.post("/search", response_model=PaginatedResponse[FlightSchema], dependencies=[Depends(rate_limit_dependency)])
async def search_flights(
    request: FlightSearchRequest,
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> PaginatedResponse[FlightSchema]:
    service = FlightService(db)
    return await service.search(request)
