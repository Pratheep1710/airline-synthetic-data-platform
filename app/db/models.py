from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AircraftStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class SellingStatus(str, enum.Enum):
    OPEN = "OPEN"
    LIMITED = "LIMITED"
    CLOSED = "CLOSED"
    WAITLIST = "WAITLIST"


class OperationalStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    BOARDING = "BOARDING"
    DEPARTED = "DEPARTED"
    ARRIVED = "ARRIVED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    TICKETED = "TICKETED"
    CANCELLED = "CANCELLED"
    HOLD = "HOLD"


class IropEventType(str, enum.Enum):
    DELAY = "DELAY"
    CANCELLATION = "CANCELLATION"
    DIVERSION = "DIVERSION"
    MISCONNECTION = "MISCONNECTION"
    AIRCRAFT_SWAP = "AIRCRAFT_SWAP"
    CREW_DELAY = "CREW_DELAY"
    WEATHER = "WEATHER"
    ATC_DELAY = "ATC_DELAY"
    MAINTENANCE = "MAINTENANCE"


class IropSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ValidationStatus(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class Aircraft(Base):
    __tablename__ = "aircrafts"
    __table_args__ = (
        UniqueConstraint("tail_number", name="uq_aircraft_tail_number"),
        Index("ix_aircraft_dataset_version", "dataset_version"),
        Index("ix_aircraft_aircraft_id", "aircraft_id"),
    )

    aircraft_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    tail_number: Mapped[str] = mapped_column(String(16), nullable=False)
    aircraft_type: Mapped[str] = mapped_column(String(16), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(32), nullable=False)
    seat_map_id: Mapped[str] = mapped_column(String(32), nullable=False)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AircraftStatus] = mapped_column(Enum(AircraftStatus), nullable=False)
    current_airport: Mapped[str] = mapped_column(String(3), nullable=False)
    last_maintenance_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_maintenance_due: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Flight(Base):
    __tablename__ = "flights"
    __table_args__ = (
        Index("ix_flight_dataset_version", "dataset_version"),
        Index("ix_flight_flight_id", "flight_id"),
        Index("ix_flight_origin", "origin"),
        Index("ix_flight_destination", "destination"),
        Index("ix_flight_departure_time_local", "departure_time_local"),
        Index("ix_flight_operational_status", "operational_status"),
        Index("ix_flight_selling_status", "selling_status"),
        CheckConstraint("duration_minutes > 0", name="ck_flight_duration_positive"),
        CheckConstraint("origin <> destination", name="ck_flight_origin_dest_different"),
    )

    flight_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    airline_code: Mapped[str] = mapped_column(String(4), nullable=False)
    flight_number: Mapped[str] = mapped_column(String(8), nullable=False)
    aircraft_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("aircrafts.aircraft_id"), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_time_local: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_time_local: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    departure_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    selling_status: Mapped[SellingStatus] = mapped_column(Enum(SellingStatus), nullable=False)
    operational_status: Mapped[OperationalStatus] = mapped_column(
        Enum(OperationalStatus), nullable=False
    )
    baggage_rule_id: Mapped[str] = mapped_column(String(32), nullable=False)
    economy_inventory: Mapped[int] = mapped_column(Integer, nullable=False)
    premium_economy_inventory: Mapped[int] = mapped_column(Integer, nullable=False)
    business_inventory: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("pnr", name="uq_booking_pnr"),
        Index("ix_booking_dataset_version", "dataset_version"),
        Index("ix_booking_pnr", "pnr"),
        CheckConstraint("passenger_count > 0", name="ck_booking_passenger_count_positive"),
    )

    booking_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    pnr: Mapped[str] = mapped_column(String(6), nullable=False)
    flight_id: Mapped[str] = mapped_column(String(48), ForeignKey("flights.flight_id"), nullable=False)
    passenger_count: Mapped[int] = mapped_column(Integer, nullable=False)
    passengers: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    booking_status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), nullable=False)
    fare_brand: Mapped[str] = mapped_column(String(32), nullable=False)
    cabin: Mapped[str] = mapped_column(String(16), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ManageTravel(Base):
    __tablename__ = "manage_travel"
    __table_args__ = (
        Index("ix_manage_travel_dataset_version", "dataset_version"),
        UniqueConstraint("pnr", name="uq_manage_travel_pnr"),
    )

    manage_travel_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    pnr: Mapped[str] = mapped_column(String(6), ForeignKey("bookings.pnr"), nullable=False)
    selected_seats: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    extra_bags: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    meals: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    car_booking: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hotel_booking: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    special_assistance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contact_update: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class IROP(Base):
    __tablename__ = "irops"
    __table_args__ = (
        Index("ix_irop_dataset_version", "dataset_version"),
        Index("ix_irop_flight_id", "flight_id"),
    )

    irop_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    flight_id: Mapped[str] = mapped_column(String(48), ForeignKey("flights.flight_id"), nullable=False)
    event_type: Mapped[IropEventType] = mapped_column(Enum(IropEventType), nullable=False)
    severity: Mapped[IropSeverity] = mapped_column(Enum(IropSeverity), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delay_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revised_departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    diversion_airport: Mapped[str | None] = mapped_column(String(3), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_message: Mapped[str] = mapped_column(String(600), nullable=False)
    operational_note: Mapped[str] = mapped_column(String(600), nullable=False)
    recovery_action: Mapped[str] = mapped_column(String(600), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DatasetGenerationJob(Base):
    __tablename__ = "dataset_generation_jobs"
    __table_args__ = (Index("ix_generation_job_dataset_version", "dataset_version"),)

    job_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_counts: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False)
    validation_status: Mapped[ValidationStatus | None] = mapped_column(
        Enum(ValidationStatus), nullable=True
    )
    validation_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
