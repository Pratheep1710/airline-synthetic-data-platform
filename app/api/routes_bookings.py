from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, rate_limit_dependency
from app.core.security import require_scopes
from app.schemas.booking import BookingSchema
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/{pnr}", response_model=BookingSchema, dependencies=[Depends(rate_limit_dependency)])
async def get_booking_by_pnr(
    pnr: str,
    dataset_version: str | None = Query(default=None),
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> BookingSchema:
    service = BookingService(db)
    row = await service.get_by_pnr(pnr, dataset_version=dataset_version)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return row
