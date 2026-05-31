from __future__ import annotations

import pytest

from app.services.dataset_service import DatasetService


@pytest.mark.asyncio
async def test_generation_pipeline_generates_requested_count(db_session):
    service = DatasetService(db_session)
    job = await service.create_job(record_count=20, enable_llm_enrichment=False, dataset_version="vtest001")
    assert job.status.value == "COMPLETED"
    assert job.requested_counts["available_aircrafts"] == 20
    assert job.validation_errors is not None
    assert job.validation_errors["schema_valid"] is True


@pytest.mark.asyncio
async def test_ids_and_pnrs_are_unique(db_session):
    service = DatasetService(db_session)
    job = await service.create_job(record_count=15, enable_llm_enrichment=False, dataset_version="vtest002")
    report = job.validation_errors or {}
    assert report.get("duplicates_found") == 0
    assert report.get("referential_errors") == []
