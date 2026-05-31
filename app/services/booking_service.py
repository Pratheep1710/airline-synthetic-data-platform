from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cache import cache_client
from app.db.repositories import BookingRepository
from app.schemas.booking import BookingSchema


class BookingService:
    def __init__(self, db: Session) -> None:
        self.repo = BookingRepository(db)

    async def get_by_pnr(self, pnr: str, dataset_version: str | None = None) -> BookingSchema | None:
        cache_key = f"dataset:{dataset_version or 'latest'}:booking:{pnr}"

        async def _producer():
            row = self.repo.get_by_pnr(pnr=pnr, dataset_version=dataset_version)
            return BookingSchema.model_validate(row).model_dump(mode="json") if row else None

        payload = await cache_client.cached(cache_key, _producer)
        return BookingSchema(**payload) if payload else None
