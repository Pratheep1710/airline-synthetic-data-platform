from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.core.cache import cache_client
from app.db.repositories import IropRepository
from app.schemas.common import PaginatedResponse
from app.schemas.irop import IropSchema


class IropService:
    def __init__(self, db: Session) -> None:
        self.repo = IropRepository(db)

    async def list(
        self,
        dataset_version: str | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_dir: str,
        filters: dict,
    ) -> PaginatedResponse[IropSchema]:
        cache_key = f"dataset:{dataset_version or 'latest'}:irops:page:{page}:size:{page_size}:{filters}"

        async def _producer():
            rows, total = self.repo.list(dataset_version, page, page_size, sort_by, sort_dir, filters)
            return {
                "items": [IropSchema.model_validate(row).model_dump(mode="json") for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        payload = await cache_client.cached(cache_key, _producer)
        return PaginatedResponse[IropSchema](**payload)

    async def get(self, irop_id: str, dataset_version: str | None = None) -> IropSchema | None:
        cache_key = f"dataset:{dataset_version or 'latest'}:irop:{irop_id}"

        async def _producer():
            if dataset_version:
                rows, _ = self.repo.list(dataset_version=dataset_version, page=1, page_size=1, filters={"irop_id": irop_id})
                row = rows[0] if rows else None
            else:
                row = self.repo.get(irop_id)
            return IropSchema.model_validate(row).model_dump(mode="json") if row else None

        payload = await cache_client.cached(cache_key, _producer)
        return IropSchema(**payload) if payload else None

    async def by_flight(self, flight_id: str, dataset_version: str | None = None) -> List[IropSchema]:
        cache_key = f"dataset:{dataset_version or 'latest'}:irops:flight:{flight_id}"

        async def _producer():
            rows = self.repo.by_flight(flight_id, dataset_version=dataset_version)
            return [IropSchema.model_validate(row).model_dump(mode="json") for row in rows]

        payload = await cache_client.cached(cache_key, _producer)
        return [IropSchema(**row) for row in payload]
