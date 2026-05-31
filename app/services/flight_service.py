from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cache import cache_client, stable_filters_hash
from app.db.repositories import FlightRepository
from app.schemas.common import PaginatedResponse
from app.schemas.flight import FlightSchema, FlightSearchRequest


class FlightService:
    def __init__(self, db: Session) -> None:
        self.repo = FlightRepository(db)

    async def list(
        self,
        dataset_version: str | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_dir: str,
        filters: dict,
    ) -> PaginatedResponse[FlightSchema]:
        filters_hash = stable_filters_hash({"dataset_version": dataset_version, **filters, "page": page, "page_size": page_size, "sort_by": sort_by, "sort_dir": sort_dir})
        cache_key = f"dataset:{dataset_version or 'latest'}:flights:{filters_hash}"

        async def _producer():
            rows, total = self.repo.list(dataset_version, page, page_size, sort_by, sort_dir, filters)
            return {
                "items": [FlightSchema.model_validate(row).model_dump(mode="json") for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        payload = await cache_client.cached(cache_key, _producer)
        return PaginatedResponse[FlightSchema](**payload)

    async def get(self, flight_id: str, dataset_version: str | None = None) -> FlightSchema | None:
        cache_key = f"dataset:{dataset_version or 'latest'}:flight:{flight_id}"

        async def _producer():
            if dataset_version:
                rows, _ = self.repo.list(dataset_version=dataset_version, page=1, page_size=1, filters={"flight_id": flight_id})
                row = rows[0] if rows else None
            else:
                row = self.repo.get(flight_id)
            return FlightSchema.model_validate(row).model_dump(mode="json") if row else None

        payload = await cache_client.cached(cache_key, _producer)
        return FlightSchema(**payload) if payload else None

    async def search(self, request: FlightSearchRequest) -> PaginatedResponse[FlightSchema]:
        filters = {
            "origin": request.origin,
            "destination": request.destination,
            "selling_status": request.selling_status,
            "operational_status": request.operational_status,
        }
        return await self.list(
            dataset_version=request.dataset_version,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_dir=request.sort_dir,
            filters=filters,
        )
