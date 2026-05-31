from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FlightSchema(BaseModel):
    flight_id: str
    dataset_version: str
    airline_code: str
    flight_number: str
    aircraft_id: str
    origin: str
    destination: str
    departure_time_local: datetime
    arrival_time_local: datetime
    departure_time_utc: datetime
    arrival_time_utc: datetime
    duration_minutes: int
    selling_status: str
    operational_status: str
    baggage_rule_id: str
    economy_inventory: int
    premium_economy_inventory: int
    business_inventory: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FlightSearchRequest(BaseModel):
    dataset_version: str | None = None
    origin: str | None = None
    destination: str | None = None
    selling_status: str | None = None
    operational_status: str | None = None
    page: int = 1
    page_size: int = 25
    sort_by: str | None = "departure_time_local"
    sort_dir: str = "asc"
