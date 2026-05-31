from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ManageTravelSchema(BaseModel):
    manage_travel_id: str
    dataset_version: str
    pnr: str
    selected_seats: list[dict[str, Any]]
    extra_bags: list[dict[str, Any]]
    meals: list[dict[str, Any]]
    car_booking: dict[str, Any] | None
    hotel_booking: dict[str, Any] | None
    special_assistance: dict[str, Any] | None
    contact_update: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
