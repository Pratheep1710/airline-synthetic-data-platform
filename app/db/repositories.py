from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import Select, and_, desc, func, select
from sqlalchemy.orm import Session

from app.db import models

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: type[T]) -> None:
        self.db = db
        self.model = model

    def create(self, instance: T) -> T:
        self.db.add(instance)
        return instance

    def get(self, pk: Any) -> T | None:
        return self.db.get(self.model, pk)

    def list(
        self,
        dataset_version: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[T], int]:
        filters = filters or {}
        query: Select[Any] = select(self.model)
        query = self._apply_filters(query, dataset_version, filters)

        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0

        if sort_by and hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            query = query.order_by(desc(sort_column) if sort_dir.lower() == "desc" else sort_column)

        query = query.offset((page - 1) * page_size).limit(page_size)
        return list(self.db.scalars(query).all()), total

    def _apply_filters(
        self, query: Select[Any], dataset_version: str | None, filters: dict[str, Any]
    ) -> Select[Any]:
        clauses = []
        if dataset_version and hasattr(self.model, "dataset_version"):
            clauses.append(getattr(self.model, "dataset_version") == dataset_version)
        for key, value in filters.items():
            if value is None or not hasattr(self.model, key):
                continue
            clauses.append(getattr(self.model, key) == value)
        if clauses:
            query = query.where(and_(*clauses))
        return query


class AircraftRepository(BaseRepository[models.Aircraft]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, models.Aircraft)


class FlightRepository(BaseRepository[models.Flight]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, models.Flight)


class BookingRepository(BaseRepository[models.Booking]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, models.Booking)

    def get_by_pnr(self, pnr: str, dataset_version: str | None = None) -> models.Booking | None:
        query = select(models.Booking).where(models.Booking.pnr == pnr)
        if dataset_version:
            query = query.where(models.Booking.dataset_version == dataset_version)
        return self.db.scalar(query)


class ManageTravelRepository(BaseRepository[models.ManageTravel]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, models.ManageTravel)

    def get_by_pnr(
        self, pnr: str, dataset_version: str | None = None
    ) -> models.ManageTravel | None:
        query = select(models.ManageTravel).where(models.ManageTravel.pnr == pnr)
        if dataset_version:
            query = query.where(models.ManageTravel.dataset_version == dataset_version)
        return self.db.scalar(query)


class IropRepository(BaseRepository[models.IROP]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, models.IROP)

    def by_flight(self, flight_id: str, dataset_version: str | None = None) -> list[models.IROP]:
        query = select(models.IROP).where(models.IROP.flight_id == flight_id)
        if dataset_version:
            query = query.where(models.IROP.dataset_version == dataset_version)
        return list(self.db.scalars(query).all())


class JobRepository(BaseRepository[models.DatasetGenerationJob]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, models.DatasetGenerationJob)
