from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import models
from app.services.dataset_service import DatasetService


@pytest.mark.asyncio
async def test_references_are_valid(db_session):
    service = DatasetService(db_session)
    await service.create_job(record_count=18, enable_llm_enrichment=False, dataset_version="vtest003")

    aircraft_ids = {row.aircraft_id for row in db_session.scalars(select(models.Aircraft)).all()}
    flight_ids = {row.flight_id for row in db_session.scalars(select(models.Flight)).all()}
    bookings = db_session.scalars(select(models.Booking)).all()
    manage_rows = db_session.scalars(select(models.ManageTravel)).all()
    irops = db_session.scalars(select(models.IROP)).all()

    assert all(f.aircraft_id in aircraft_ids for f in db_session.scalars(select(models.Flight)).all())
    assert all(b.flight_id in flight_ids for b in bookings)
    assert all(m.pnr in {b.pnr for b in bookings} for m in manage_rows)
    assert all(i.flight_id in flight_ids for i in irops)
