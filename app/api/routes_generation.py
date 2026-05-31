from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, rate_limit_dependency
from app.core.security import require_scopes
from app.schemas.common import GenerationJobRequest, GenerationJobResponse
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/generation", tags=["generation"])


@router.post("/jobs", response_model=GenerationJobResponse, dependencies=[Depends(rate_limit_dependency)])
async def create_generation_job(
    request: GenerationJobRequest,
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:generate"])),
) -> GenerationJobResponse:
    service = DatasetService(db)
    job = await service.create_job(
        record_count=request.record_count,
        enable_llm_enrichment=request.enable_llm_enrichment,
        dataset_version=request.dataset_version,
    )
    return service.to_job_response(job)


@router.get("/jobs/{job_id}", response_model=GenerationJobResponse, dependencies=[Depends(rate_limit_dependency)])
async def get_generation_job(
    job_id: str,
    db: Session = Depends(db_session),
    _user=Security(require_scopes(["dataset:read"])),
) -> GenerationJobResponse:
    service = DatasetService(db)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return service.to_job_response(job)
