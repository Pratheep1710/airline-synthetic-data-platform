from __future__ import annotations

import random
import string
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.db import models
from app.generation import catalogs
from app.generation.id_generator import DeterministicIdGenerator
from app.generation.llm_enrichment import LLMClient, enrich_passenger_name, enrich_text


@dataclass
class GeneratedDataset:
    aircrafts: list[models.Aircraft]
    flights: list[models.Flight]
    bookings: list[models.Booking]
    manage_travel: list[models.ManageTravel]
    irops: list[models.IROP]


class DeterministicDataGenerator:
    def __init__(self, dataset_version: str, record_count: int, llm_client: LLMClient, seed: int = 42) -> None:
        self.dataset_version = dataset_version
        self.record_count = record_count
        namespace = "".join(ch for ch in dataset_version.upper() if ch.isalnum())[-4:] or "AAAA"
        derived_seed = seed + sum(ord(ch) for ch in dataset_version)
        self.random = random.Random(derived_seed)
        self.ids = DeterministicIdGenerator(seed=derived_seed, namespace=namespace)
        self.llm_client = llm_client
        self.tail_prefix = self._dataset_tail_prefix(dataset_version)

    @staticmethod
    def _dataset_tail_prefix(dataset_version: str) -> str:
        chars = string.ascii_uppercase + string.digits
        value = sum((idx + 1) * ord(ch) for idx, ch in enumerate(dataset_version))
        encoded = []
        for _ in range(4):
            value, rem = divmod(value, len(chars))
            encoded.append(chars[rem])
        return "".join(encoded)

    async def generate(self) -> GeneratedDataset:
        aircrafts = self.generate_aircrafts()
        flights = self.generate_flights(aircrafts)
        bookings = await self.generate_bookings(flights, aircrafts)
        manage_travel = await self.generate_manage_travel(bookings, flights)
        irops = await self.generate_irops(flights)
        return GeneratedDataset(
            aircrafts=aircrafts,
            flights=flights,
            bookings=bookings,
            manage_travel=manage_travel,
            irops=irops,
        )

    def generate_aircrafts(self) -> list[models.Aircraft]:
        choices = list(catalogs.AIRCRAFT_TYPES.keys())
        airports = list(catalogs.AIRPORTS.keys())
        aircrafts: list[models.Aircraft] = []

        for idx in range(self.record_count):
            aircraft_type = choices[idx % len(choices)]
            type_meta = catalogs.AIRCRAFT_TYPES[aircraft_type]
            aircraft_id = self.ids.aircraft_id(aircraft_type)
            tail_number = f"VT-{self.tail_prefix}{idx + 1:04d}"
            status = self.random.choices(
                [
                    models.AircraftStatus.AVAILABLE,
                    models.AircraftStatus.ACTIVE,
                    models.AircraftStatus.MAINTENANCE,
                    models.AircraftStatus.OUT_OF_SERVICE,
                ],
                weights=[45, 40, 10, 5],
                k=1,
            )[0]
            now = datetime.now(UTC)
            aircrafts.append(
                models.Aircraft(
                    aircraft_id=aircraft_id,
                    dataset_version=self.dataset_version,
                    tail_number=tail_number,
                    aircraft_type=aircraft_type,
                    manufacturer=type_meta["manufacturer"],
                    model=type_meta["model"],
                    seat_map_id=type_meta["seat_map_id"],
                    total_seats=type_meta["total"],
                    status=status,
                    current_airport=airports[idx % len(airports)],
                    last_maintenance_date=now - timedelta(days=self.random.randint(5, 90)),
                    next_maintenance_due=now + timedelta(days=self.random.randint(7, 120)),
                    created_at=now,
                    updated_at=now,
                )
            )
        return aircrafts

    def generate_flights(self, aircrafts: list[models.Aircraft]) -> list[models.Flight]:
        usable_aircraft = [
            ac
            for ac in aircrafts
            if ac.status in (models.AircraftStatus.AVAILABLE, models.AircraftStatus.ACTIVE)
        ]
        if not usable_aircraft:
            aircrafts[0].status = models.AircraftStatus.AVAILABLE
            usable_aircraft = [aircrafts[0]]
        last_arrival: dict[str, datetime] = {}
        flights: list[models.Flight] = []

        for idx in range(self.record_count):
            aircraft = usable_aircraft[idx % len(usable_aircraft)]
            origin, destination = catalogs.ROUTES[idx % len(catalogs.ROUTES)]
            duration_min, duration_max = catalogs.route_duration_range(origin, destination)
            duration = self.random.randint(duration_min, duration_max)
            origin_tz = ZoneInfo(catalogs.AIRPORTS[origin].timezone)
            destination_tz = ZoneInfo(catalogs.AIRPORTS[destination].timezone)
            base_date = datetime.now(origin_tz).replace(hour=5, minute=0, second=0, microsecond=0) + timedelta(
                days=idx // 8
            )
            candidate_departure = base_date + timedelta(hours=(idx % 8) * 2 + self.random.randint(0, 1))
            if aircraft.aircraft_id in last_arrival:
                minimum_departure = last_arrival[aircraft.aircraft_id] + timedelta(
                    minutes=self.random.randint(45, 90)
                )
                if candidate_departure < minimum_departure:
                    candidate_departure = minimum_departure

            departure_local = candidate_departure
            departure_utc = departure_local.astimezone(UTC)
            arrival_utc = departure_utc + timedelta(minutes=duration)
            arrival_local = arrival_utc.astimezone(destination_tz)
            last_arrival[aircraft.aircraft_id] = departure_local + timedelta(minutes=duration)

            flight_number = f"AI{450 + (idx % 350)}"
            seat_map = catalogs.SEAT_MAPS[aircraft.seat_map_id]
            econ = len(seat_map["economy"])
            prem = len(seat_map["premium_economy"])
            biz = len(seat_map["business"])
            selling_status = self.random.choices(
                [
                    models.SellingStatus.OPEN,
                    models.SellingStatus.LIMITED,
                    models.SellingStatus.CLOSED,
                    models.SellingStatus.WAITLIST,
                ],
                weights=[55, 25, 15, 5],
                k=1,
            )[0]

            flights.append(
                models.Flight(
                    flight_id=self.ids.flight_id(departure_local, flight_number),
                    dataset_version=self.dataset_version,
                    airline_code="AI",
                    flight_number=flight_number,
                    aircraft_id=aircraft.aircraft_id,
                    origin=origin,
                    destination=destination,
                    departure_time_local=departure_local,
                    arrival_time_local=arrival_local,
                    departure_time_utc=departure_utc,
                    arrival_time_utc=arrival_utc,
                    duration_minutes=duration,
                    selling_status=selling_status,
                    operational_status=self.random.choice(
                        [
                            models.OperationalStatus.SCHEDULED,
                            models.OperationalStatus.BOARDING,
                            models.OperationalStatus.DEPARTED,
                            models.OperationalStatus.ARRIVED,
                            models.OperationalStatus.DELAYED,
                            models.OperationalStatus.CANCELLED,
                        ]
                    ),
                    baggage_rule_id=self.random.choice(list(catalogs.BAGGAGE_RULES.keys())),
                    economy_inventory=econ,
                    premium_economy_inventory=prem,
                    business_inventory=biz,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
        return flights

    async def generate_bookings(
        self, flights: list[models.Flight], aircrafts: list[models.Aircraft]
    ) -> list[models.Booking]:
        sellable = [
            fl
            for fl in flights
            if fl.selling_status in (models.SellingStatus.OPEN, models.SellingStatus.LIMITED)
        ]
        if not sellable:
            for fl in flights[: min(5, len(flights))]:
                fl.selling_status = models.SellingStatus.OPEN
            sellable = [
                fl
                for fl in flights
                if fl.selling_status in (models.SellingStatus.OPEN, models.SellingStatus.LIMITED)
            ]
        aircraft_map = {ac.aircraft_id: ac for ac in aircrafts}
        cabin_seat_pools: dict[str, dict[str, list[str]]] = {}
        bookings: list[models.Booking] = []

        for fl in sellable:
            ac = aircraft_map[fl.aircraft_id]
            seat_map = catalogs.SEAT_MAPS[ac.seat_map_id]
            cabin_seat_pools[fl.flight_id] = {
                "ECONOMY": seat_map["economy"].copy(),
                "PREMIUM_ECONOMY": seat_map["premium_economy"].copy(),
                "BUSINESS": seat_map["business"].copy(),
            }

        idx = 0
        attempts = 0
        max_attempts = max(500, self.record_count * 20)
        while len(bookings) < self.record_count and attempts < max_attempts:
            fl = sellable[idx % len(sellable)]
            cabin = self.random.choices(
                ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS"], weights=[70, 10, 20], k=1
            )[0]
            seat_pool = cabin_seat_pools[fl.flight_id][cabin]
            if not seat_pool:
                attempts += 1
                idx += 1
                continue
            pax_count = min(self.random.randint(1, 3), len(seat_pool))
            passengers = []
            for pidx in range(pax_count):
                seat = seat_pool.pop(0)
                first, last = await enrich_passenger_name(
                    self.llm_client,
                    first_name=self.random.choice(["Arun", "Priya", "Karan", "Neha", "Rohan", "Sara"]),
                    last_name=self.random.choice(["Iyer", "Sharma", "Khan", "Nair", "Reddy", "Das"]),
                )
                passengers.append(
                    {
                        "passenger_id": f"PAX-{idx + 1:04d}-{pidx + 1}",
                        "first_name": first,
                        "last_name": last,
                        "passenger_type": self.random.choices(
                            ["ADULT", "CHILD", "INFANT"], weights=[80, 15, 5], k=1
                        )[0],
                        "seat_number": seat,
                        "meal_preference": self.random.choice(catalogs.MEAL_OPTIONS),
                        "special_service_request": self.random.choice(catalogs.SSR_CODES),
                    }
                )
            booking_status = self.random.choices(
                [
                    models.BookingStatus.CONFIRMED,
                    models.BookingStatus.TICKETED,
                    models.BookingStatus.CANCELLED,
                    models.BookingStatus.HOLD,
                ],
                weights=[52, 38, 6, 4],
                k=1,
            )[0]
            fare_brand = self.random.choice(catalogs.FARE_BRANDS)
            amount = Decimal(str(2000 + 1500 * pax_count + self.random.randint(100, 20000)))
            bookings.append(
                models.Booking(
                    booking_id=self.ids.booking_id(),
                    dataset_version=self.dataset_version,
                    pnr=self.ids.pnr(),
                    flight_id=fl.flight_id,
                    passenger_count=pax_count,
                    passengers=passengers,
                    booking_status=booking_status,
                    fare_brand=fare_brand,
                    cabin=cabin,
                    total_amount=amount,
                    currency="INR",
                    payment_status=self.random.choice(["PAID", "PENDING", "REFUNDED"]),
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            idx += 1
            attempts += 1

        # Guarantee enough confirmed/ticketed bookings for manage travel generation.
        required = min(self.record_count, len(bookings))
        for booking in bookings[:required]:
            if booking.booking_status not in (
                models.BookingStatus.CONFIRMED,
                models.BookingStatus.TICKETED,
            ):
                booking.booking_status = self.random.choice(
                    [models.BookingStatus.CONFIRMED, models.BookingStatus.TICKETED]
                )
        return bookings

    async def generate_manage_travel(
        self, bookings: list[models.Booking], flights: list[models.Flight]
    ) -> list[models.ManageTravel]:
        flight_map = {f.flight_id: f for f in flights}
        allowed = [b for b in bookings if b.booking_status in (models.BookingStatus.CONFIRMED, models.BookingStatus.TICKETED)]
        generated: list[models.ManageTravel] = []

        for booking in allowed[: min(self.record_count, len(allowed))]:
            flight = flight_map[booking.flight_id]
            arrival_date = flight.arrival_time_local.date()
            selected_seats = [{"passenger_id": p["passenger_id"], "seat_number": p["seat_number"]} for p in booking.passengers]
            extra_bags = [{"passenger_id": p["passenger_id"], "count": self.random.randint(0, 1)} for p in booking.passengers]
            meals = [{"passenger_id": p["passenger_id"], "meal": p["meal_preference"]} for p in booking.passengers]
            include_hotel = self.random.random() < 0.35
            include_car = self.random.random() < 0.4

            generated.append(
                models.ManageTravel(
                    manage_travel_id=self.ids.manage_travel_id(),
                    dataset_version=self.dataset_version,
                    pnr=booking.pnr,
                    selected_seats=selected_seats,
                    extra_bags=extra_bags,
                    meals=meals,
                    car_booking=(
                        {
                            "vendor": "ZoomCar",
                            "pickup_airport": flight.destination,
                            "pickup_time": (flight.arrival_time_local + timedelta(minutes=45)).isoformat(),
                        }
                        if include_car
                        else None
                    ),
                    hotel_booking=(
                        {
                            "hotel_name": "Airport Transit Suites",
                            "check_in": datetime.combine(
                                arrival_date, datetime.min.time(), tzinfo=flight.arrival_time_local.tzinfo
                            )
                            .replace(hour=15)
                            .isoformat(),
                            "check_out": datetime.combine(
                                arrival_date + timedelta(days=1),
                                datetime.min.time(),
                                tzinfo=flight.arrival_time_local.tzinfo,
                            )
                            .replace(hour=11)
                            .isoformat(),
                        }
                        if include_hotel
                        else None
                    ),
                    special_assistance={"note": "Wheelchair at arrival gate"}
                    if self.random.random() < 0.1
                    else None,
                    contact_update={"email": f"{booking.pnr.lower()}@example.com", "phone": "+919999000111"},
                    status="ACTIVE",
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
        return generated

    async def generate_irops(self, flights: list[models.Flight]) -> list[models.IROP]:
        chosen = self.random.sample(flights, k=min(self.record_count, len(flights)))
        irops: list[models.IROP] = []
        for flight in chosen:
            event_type = self.random.choice(list(models.IropEventType))
            delay_minutes = None
            revised_departure = None
            diversion_airport = None
            if event_type in {
                models.IropEventType.DELAY,
                models.IropEventType.CREW_DELAY,
                models.IropEventType.ATC_DELAY,
                models.IropEventType.WEATHER,
                models.IropEventType.MAINTENANCE,
            }:
                delay_minutes = self.random.randint(20, 240)
                revised_departure = flight.departure_time_local + timedelta(minutes=delay_minutes)
            if event_type == models.IropEventType.DIVERSION:
                diversion_airport = self.random.choice(
                    [code for code in catalogs.AIRPORTS.keys() if code not in (flight.origin, flight.destination)]
                )

            message = await enrich_text(
                self.llm_client,
                f"Flight {flight.flight_number} is impacted by {event_type.value.lower().replace('_', ' ')}.",
                {"origin": flight.origin, "destination": flight.destination},
                max_len=560,
            )
            note = await enrich_text(
                self.llm_client,
                "Ops team coordinating recovery and passenger support.",
                {"event_type": event_type.value},
                max_len=560,
            )
            action = await enrich_text(
                self.llm_client,
                "Reaccommodate on next available service with waiver.",
                {"event_type": event_type.value},
                max_len=560,
            )

            irops.append(
                models.IROP(
                    irop_id=self.ids.irop_id(),
                    dataset_version=self.dataset_version,
                    flight_id=flight.flight_id,
                    event_type=event_type,
                    severity=self.random.choice(list(models.IropSeverity)),
                    event_time=flight.departure_time_local - timedelta(minutes=self.random.randint(10, 180)),
                    delay_minutes=delay_minutes,
                    original_departure_time=flight.departure_time_local,
                    revised_departure_time=revised_departure,
                    diversion_airport=diversion_airport,
                    reason_code=event_type.value[:12],
                    customer_message=message,
                    operational_note=note,
                    recovery_action=action,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
        return irops
