from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, rate_limit_dependency
from app.core.security import require_scopes
from app.schemas.common import ValidationReportSchema
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", dependencies=[Depends(rate_limit_dependency)])
async def list_datasets(
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> list[dict]:
    service = DatasetService(db)
    return service.list_datasets()


@router.get(
    "/{dataset_version}/validation-report",
    response_model=ValidationReportSchema,
    dependencies=[Depends(rate_limit_dependency)],
)
async def get_validation_report(
    dataset_version: str,
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["validation:read"])),
) -> ValidationReportSchema:
    service = DatasetService(db)
    report = await service.get_validation_report(dataset_version)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation report not found")
    return ValidationReportSchema(**report)
