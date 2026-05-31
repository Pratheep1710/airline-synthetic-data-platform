from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PassengerSchema(BaseModel):
    passenger_id: str
    first_name: str
    last_name: str
    passenger_type: str
    seat_number: str
    meal_preference: str
    special_service_request: str | None = None


class BookingSchema(BaseModel):
    booking_id: str
    dataset_version: str
    pnr: str
    flight_id: str
    passenger_count: int
    passengers: list[dict[str, Any]]
    booking_status: str
    fare_brand: str
    cabin: str
    total_amount: float
    currency: str
    payment_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
