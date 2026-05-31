from __future__ import annotations

import pytest

from app.services.dataset_service import DatasetService


@pytest.mark.asyncio
async def test_business_rules_pass_for_generated_dataset(db_session):
    service = DatasetService(db_session)
    job = await service.create_job(record_count=25, enable_llm_enrichment=False, dataset_version="vtest004")
    report = job.validation_errors or {}

    assert report["business_rules_valid"] is True
    assert report["referential_errors"] == []
    assert not any("overlap" in msg.lower() for msg in report["business_rule_errors"])
    assert not any("overbooking" in msg.lower() for msg in report["business_rule_errors"])
    assert not any("invalid flight time order" in msg.lower() for msg in report["business_rule_errors"])
