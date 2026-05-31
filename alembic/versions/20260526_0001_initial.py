"""initial schema

Revision ID: 20260526_0001
Revises:
Create Date: 2026-05-26 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aircrafts",
        sa.Column("aircraft_id", sa.String(length=32), nullable=False),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("tail_number", sa.String(length=16), nullable=False),
        sa.Column("aircraft_type", sa.String(length=16), nullable=False),
        sa.Column("manufacturer", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=32), nullable=False),
        sa.Column("seat_map_id", sa.String(length=32), nullable=False),
        sa.Column("total_seats", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("AVAILABLE", "ACTIVE", "MAINTENANCE", "OUT_OF_SERVICE", name="aircraftstatus"),
            nullable=False,
        ),
        sa.Column("current_airport", sa.String(length=3), nullable=False),
        sa.Column("last_maintenance_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_maintenance_due", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("aircraft_id"),
        sa.UniqueConstraint("tail_number", name="uq_aircraft_tail_number"),
    )
    op.create_index("ix_aircraft_dataset_version", "aircrafts", ["dataset_version"])
    op.create_index("ix_aircraft_aircraft_id", "aircrafts", ["aircraft_id"])

    op.create_table(
        "flights",
        sa.Column("flight_id", sa.String(length=48), nullable=False),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("airline_code", sa.String(length=4), nullable=False),
        sa.Column("flight_number", sa.String(length=8), nullable=False),
        sa.Column("aircraft_id", sa.String(length=32), nullable=False),
        sa.Column("origin", sa.String(length=3), nullable=False),
        sa.Column("destination", sa.String(length=3), nullable=False),
        sa.Column("departure_time_local", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrival_time_local", sa.DateTime(timezone=True), nullable=False),
        sa.Column("departure_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrival_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "selling_status",
            sa.Enum("OPEN", "LIMITED", "CLOSED", "WAITLIST", name="sellingstatus"),
            nullable=False,
        ),
        sa.Column(
            "operational_status",
            sa.Enum(
                "SCHEDULED",
                "BOARDING",
                "DEPARTED",
                "ARRIVED",
                "DELAYED",
                "CANCELLED",
                name="operationalstatus",
            ),
            nullable=False,
        ),
        sa.Column("baggage_rule_id", sa.String(length=32), nullable=False),
        sa.Column("economy_inventory", sa.Integer(), nullable=False),
        sa.Column("premium_economy_inventory", sa.Integer(), nullable=False),
        sa.Column("business_inventory", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("duration_minutes > 0", name="ck_flight_duration_positive"),
        sa.CheckConstraint("origin <> destination", name="ck_flight_origin_dest_different"),
        sa.ForeignKeyConstraint(["aircraft_id"], ["aircrafts.aircraft_id"]),
        sa.PrimaryKeyConstraint("flight_id"),
    )
    op.create_index("ix_flight_dataset_version", "flights", ["dataset_version"])
    op.create_index("ix_flight_flight_id", "flights", ["flight_id"])
    op.create_index("ix_flight_origin", "flights", ["origin"])
    op.create_index("ix_flight_destination", "flights", ["destination"])
    op.create_index("ix_flight_departure_time_local", "flights", ["departure_time_local"])
    op.create_index("ix_flight_operational_status", "flights", ["operational_status"])
    op.create_index("ix_flight_selling_status", "flights", ["selling_status"])

    op.create_table(
        "bookings",
        sa.Column("booking_id", sa.String(length=32), nullable=False),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("pnr", sa.String(length=6), nullable=False),
        sa.Column("flight_id", sa.String(length=48), nullable=False),
        sa.Column("passenger_count", sa.Integer(), nullable=False),
        sa.Column("passengers", sa.JSON(), nullable=False),
        sa.Column(
            "booking_status",
            sa.Enum("CONFIRMED", "TICKETED", "CANCELLED", "HOLD", name="bookingstatus"),
            nullable=False,
        ),
        sa.Column("fare_brand", sa.String(length=32), nullable=False),
        sa.Column("cabin", sa.String(length=16), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("payment_status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("passenger_count > 0", name="ck_booking_passenger_count_positive"),
        sa.ForeignKeyConstraint(["flight_id"], ["flights.flight_id"]),
        sa.PrimaryKeyConstraint("booking_id"),
        sa.UniqueConstraint("pnr", name="uq_booking_pnr"),
    )
    op.create_index("ix_booking_dataset_version", "bookings", ["dataset_version"])
    op.create_index("ix_booking_pnr", "bookings", ["pnr"])

    op.create_table(
        "manage_travel",
        sa.Column("manage_travel_id", sa.String(length=32), nullable=False),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("pnr", sa.String(length=6), nullable=False),
        sa.Column("selected_seats", sa.JSON(), nullable=False),
        sa.Column("extra_bags", sa.JSON(), nullable=False),
        sa.Column("meals", sa.JSON(), nullable=False),
        sa.Column("car_booking", sa.JSON(), nullable=True),
        sa.Column("hotel_booking", sa.JSON(), nullable=True),
        sa.Column("special_assistance", sa.JSON(), nullable=True),
        sa.Column("contact_update", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pnr"], ["bookings.pnr"]),
        sa.PrimaryKeyConstraint("manage_travel_id"),
        sa.UniqueConstraint("pnr", name="uq_manage_travel_pnr"),
    )
    op.create_index("ix_manage_travel_dataset_version", "manage_travel", ["dataset_version"])

    op.create_table(
        "irops",
        sa.Column("irop_id", sa.String(length=32), nullable=False),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("flight_id", sa.String(length=48), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "DELAY",
                "CANCELLATION",
                "DIVERSION",
                "MISCONNECTION",
                "AIRCRAFT_SWAP",
                "CREW_DELAY",
                "WEATHER",
                "ATC_DELAY",
                "MAINTENANCE",
                name="iropeventtype",
            ),
            nullable=False,
        ),
        sa.Column("severity", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="iropseverity"), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delay_minutes", sa.Integer(), nullable=True),
        sa.Column("original_departure_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revised_departure_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("diversion_airport", sa.String(length=3), nullable=True),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("customer_message", sa.String(length=600), nullable=False),
        sa.Column("operational_note", sa.String(length=600), nullable=False),
        sa.Column("recovery_action", sa.String(length=600), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["flight_id"], ["flights.flight_id"]),
        sa.PrimaryKeyConstraint("irop_id"),
    )
    op.create_index("ix_irop_dataset_version", "irops", ["dataset_version"])
    op.create_index("ix_irop_flight_id", "irops", ["flight_id"])

    op.create_table(
        "dataset_generation_jobs",
        sa.Column("job_id", sa.String(length=32), nullable=False),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("requested_counts", sa.JSON(), nullable=False),
        sa.Column(
            "status", sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="jobstatus"), nullable=False
        ),
        sa.Column(
            "validation_status",
            sa.Enum("PASSED", "FAILED", "PARTIAL", name="validationstatus"),
            nullable=True,
        ),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        "ix_generation_job_dataset_version", "dataset_generation_jobs", ["dataset_version"]
    )


def downgrade() -> None:
    op.drop_index("ix_generation_job_dataset_version", table_name="dataset_generation_jobs")
    op.drop_table("dataset_generation_jobs")
    op.drop_index("ix_irop_flight_id", table_name="irops")
    op.drop_index("ix_irop_dataset_version", table_name="irops")
    op.drop_table("irops")
    op.drop_index("ix_manage_travel_dataset_version", table_name="manage_travel")
    op.drop_table("manage_travel")
    op.drop_index("ix_booking_pnr", table_name="bookings")
    op.drop_index("ix_booking_dataset_version", table_name="bookings")
    op.drop_table("bookings")
    op.drop_index("ix_flight_selling_status", table_name="flights")
    op.drop_index("ix_flight_operational_status", table_name="flights")
    op.drop_index("ix_flight_departure_time_local", table_name="flights")
    op.drop_index("ix_flight_destination", table_name="flights")
    op.drop_index("ix_flight_origin", table_name="flights")
    op.drop_index("ix_flight_flight_id", table_name="flights")
    op.drop_index("ix_flight_dataset_version", table_name="flights")
    op.drop_table("flights")
    op.drop_index("ix_aircraft_aircraft_id", table_name="aircrafts")
    op.drop_index("ix_aircraft_dataset_version", table_name="aircrafts")
    op.drop_table("aircrafts")
