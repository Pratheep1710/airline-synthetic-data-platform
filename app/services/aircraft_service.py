from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cache import cache_client
from app.db.repositories import AircraftRepository
from app.schemas.aircraft import AircraftSchema
from app.schemas.common import PaginatedResponse


class AircraftService:
    def __init__(self, db: Session) -> None:
        self.repo = AircraftRepository(db)

    async def list(
        self,
        dataset_version: str | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_dir: str,
        filters: dict,
    ) -> PaginatedResponse[AircraftSchema]:
        cache_key = (
            f"dataset:{dataset_version or 'latest'}:aircrafts:page:{page}:size:{page_size}:"
            f"sort:{sort_by or 'aircraft_id'}:{sort_dir}:filters:{filters}"
        )

        async def _producer():
            rows, total = self.repo.list(dataset_version, page, page_size, sort_by, sort_dir, filters)
            return {
                "items": [AircraftSchema.model_validate(row).model_dump(mode="json") for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        payload = await cache_client.cached(cache_key, _producer)
        return PaginatedResponse[AircraftSchema](**payload)

    async def get(self, aircraft_id: str, dataset_version: str | None = None) -> AircraftSchema | None:
        cache_key = f"dataset:{dataset_version or 'latest'}:aircraft:{aircraft_id}"

        async def _producer():
            if dataset_version:
                rows, _ = self.repo.list(dataset_version=dataset_version, page=1, page_size=1, filters={"aircraft_id": aircraft_id})
                row = rows[0] if rows else None
            else:
                row = self.repo.get(aircraft_id)
            return AircraftSchema.model_validate(row).model_dump(mode="json") if row else None

        payload = await cache_client.cached(cache_key, _producer)
        return AircraftSchema(**payload) if payload else None
