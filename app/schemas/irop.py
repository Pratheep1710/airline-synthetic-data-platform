from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class IropSchema(BaseModel):
    irop_id: str
    dataset_version: str
    flight_id: str
    event_type: str
    severity: str
    event_time: datetime
    delay_minutes: int | None
    original_departure_time: datetime | None
    revised_departure_time: datetime | None
    diversion_airport: str | None
    reason_code: str
    customer_message: str
    operational_note: str
    recovery_action: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
