from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AircraftSchema(BaseModel):
    aircraft_id: str
    dataset_version: str
    tail_number: str
    aircraft_type: str
    manufacturer: str
    model: str
    seat_map_id: str
    total_seats: int
    status: str
    current_airport: str
    last_maintenance_date: datetime
    next_maintenance_due: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
