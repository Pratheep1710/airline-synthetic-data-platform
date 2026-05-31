from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cache import cache_client
from app.db.repositories import ManageTravelRepository
from app.schemas.manage_travel import ManageTravelSchema


class ManageTravelService:
    def __init__(self, db: Session) -> None:
        self.repo = ManageTravelRepository(db)

    async def get_by_pnr(self, pnr: str, dataset_version: str | None = None) -> ManageTravelSchema | None:
        cache_key = f"dataset:{dataset_version or 'latest'}:manage-travel:{pnr}"

        async def _producer():
            row = self.repo.get_by_pnr(pnr=pnr, dataset_version=dataset_version)
            return ManageTravelSchema.model_validate(row).model_dump(mode="json") if row else None

        payload = await cache_client.cached(cache_key, _producer)
        return ManageTravelSchema(**payload) if payload else None
