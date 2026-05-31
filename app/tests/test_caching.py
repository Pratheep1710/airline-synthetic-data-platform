from __future__ import annotations

import pytest

from app.core.cache import cache_client
from app.services.dataset_service import DatasetService


@pytest.mark.asyncio
async def test_cached_endpoint_consistency_and_invalidation(db_session):
    service = DatasetService(db_session)
    await service.create_job(record_count=10, enable_llm_enrichment=False, dataset_version="vcache001")

    first = await service.get_validation_report("vcache001")
    second = await service.get_validation_report("vcache001")
    assert first == second

    await cache_client.set_json("dataset:vcache001:validation-report", {"schema_valid": False}, ttl_seconds=60)
    cached = await cache_client.get_json("dataset:vcache001:validation-report")
    assert cached == {"schema_valid": False}

    await service.create_job(record_count=12, enable_llm_enrichment=False, dataset_version="vcache001")
    assert await cache_client.get_json("dataset:vcache001:validation-report") is None
