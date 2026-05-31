from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import cache_client
from app.db import models
from app.db.repositories import JobRepository
from app.generation.pipeline import GenerationPipeline, request_counts
from app.schemas.common import GenerationJobResponse

logger = logging.getLogger(__name__)


class DatasetService:
    _generation_lock = asyncio.Lock()

    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = JobRepository(db)
        self.pipeline = GenerationPipeline(db)

    async def create_job(
        self,
        record_count: int,
        enable_llm_enrichment: bool,
        dataset_version: str | None,
    ) -> models.DatasetGenerationJob:
        start_time = datetime.now(UTC)
        # Use microseconds to avoid collisions on rapid consecutive requests.
        version = dataset_version or datetime.now(UTC).strftime("v%Y%m%d%H%M%S%f")
        logger.info(
            "generation_job_received",
            extra={
                "requested_dataset_version": dataset_version,
                "resolved_dataset_version": version,
                "record_count": record_count,
                "enable_llm_enrichment": enable_llm_enrichment,
            },
        )
        existing = self.db.scalar(
            select(models.DatasetGenerationJob).where(
                models.DatasetGenerationJob.dataset_version == version
            )
        )
        if existing:
            logger.warning(
                "generation_job_duplicate_dataset_version",
                extra={"dataset_version": version},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dataset version already exists: {version}",
            )

        job = models.DatasetGenerationJob(
            job_id=f"JOB-{uuid4().hex[:10].upper()}",
            dataset_version=version,
            requested_counts=request_counts(record_count),
            status=models.JobStatus.RUNNING,
            validation_status=None,
            validation_errors=None,
        )

        async with self._generation_lock:
            logger.info(
                "generation_job_lock_acquired",
                extra={"job_id": job.job_id, "dataset_version": version},
            )
            self.jobs.create(job)
            self.db.flush()
            try:
                logger.info(
                    "generation_job_pipeline_started",
                    extra={"job_id": job.job_id, "dataset_version": version},
                )
                result = await self.pipeline.run(
                    dataset_version=version,
                    record_count=record_count,
                    enable_llm_enrichment=enable_llm_enrichment,
                )
                logger.info(
                    "generation_job_pipeline_completed",
                    extra={
                        "job_id": job.job_id,
                        "dataset_version": version,
                        "schema_valid": result.validation_report.schema_valid,
                        "business_rules_valid": result.validation_report.business_rules_valid,
                        "duplicates_found": result.validation_report.duplicates_found,
                        "realism_score": result.validation_report.realism_score,
                        "generated_counts": {
                            "aircrafts": len(result.generated.aircrafts),
                            "flights": len(result.generated.flights),
                            "bookings": len(result.generated.bookings),
                            "manage_travel": len(result.generated.manage_travel),
                            "irops": len(result.generated.irops),
                        },
                    },
                )
                job.status = models.JobStatus.COMPLETED
                job.validation_status = (
                    models.ValidationStatus.PASSED
                    if result.validation_report.business_rules_valid
                    and result.validation_report.schema_valid
                    and result.validation_report.duplicates_found == 0
                    else models.ValidationStatus.FAILED
                )
                job.validation_errors = result.validation_report.as_dict()
                job.completed_at = datetime.now(UTC)
                self.db.commit()
                await cache_client.invalidate_prefix(f"dataset:{version}:")
                logger.info(
                    "generation_job_completed",
                    extra={
                        "job_id": job.job_id,
                        "dataset_version": version,
                        "validation_status": (
                            job.validation_status.value if job.validation_status else None
                        ),
                        "started_at": start_time,
                        "completed_at": job.completed_at,
                    },
                )
                return job
            except IntegrityError as exc:
                self.db.rollback()
                job.status = models.JobStatus.FAILED
                job.validation_status = models.ValidationStatus.FAILED
                job.validation_errors = {"error": str(exc)}
                job.completed_at = datetime.now(UTC)
                self.db.add(job)
                self.db.commit()
                logger.exception(
                    "generation_job_integrity_error",
                    extra={
                        "job_id": job.job_id,
                        "dataset_version": version,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Dataset persistence conflict. Use a unique dataset_version "
                        "or omit dataset_version to auto-generate one."
                    ),
                ) from exc
            except Exception as exc:
                self.db.rollback()
                job.status = models.JobStatus.FAILED
                job.validation_status = models.ValidationStatus.FAILED
                job.validation_errors = {"error": str(exc)}
                job.completed_at = datetime.now(UTC)
                self.db.add(job)
                self.db.commit()
                logger.exception(
                    "generation_job_failed",
                    extra={
                        "job_id": job.job_id,
                        "dataset_version": version,
                    },
                )
                raise

    def get_job(self, job_id: str) -> models.DatasetGenerationJob | None:
        return self.jobs.get(job_id)

    def list_datasets(self) -> list[dict]:
        query = (
            select(models.DatasetGenerationJob)
            .where(models.DatasetGenerationJob.status == models.JobStatus.COMPLETED)
            .order_by(desc(models.DatasetGenerationJob.created_at))
        )
        rows = self.db.scalars(query).all()
        return [
            {
                "dataset_version": row.dataset_version,
                "job_id": row.job_id,
                "created_at": row.created_at,
                "validation_status": row.validation_status.value if row.validation_status else None,
            }
            for row in rows
        ]

    async def get_validation_report(self, dataset_version: str) -> dict | None:
        cache_key = f"dataset:{dataset_version}:validation-report"

        async def _producer() -> dict[str, Any] | None:
            row = self.db.scalar(
                select(models.DatasetGenerationJob)
                .where(models.DatasetGenerationJob.dataset_version == dataset_version)
                .order_by(desc(models.DatasetGenerationJob.created_at))
            )
            return row.validation_errors if row else None

        return await cache_client.cached(cache_key, _producer)

    @staticmethod
    def to_job_response(job: models.DatasetGenerationJob) -> GenerationJobResponse:
        return GenerationJobResponse(
            job_id=job.job_id,
            dataset_version=job.dataset_version,
            status=job.status.value,
            validation_status=job.validation_status.value if job.validation_status else None,
            requested_counts=job.requested_counts,
            validation_errors=job.validation_errors,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
