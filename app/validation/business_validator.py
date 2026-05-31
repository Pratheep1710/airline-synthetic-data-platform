from __future__ import annotations

from datetime import datetime

from app.generation import catalogs


class BusinessValidator:
    def validate(self, data: dict[str, list[dict]]) -> list[str]:
        rule_errors: list[str] = []

        flight_ids = {row["flight_id"] for row in data.get("flights", [])}
        flights_by_id = {row["flight_id"]: row for row in data.get("flights", [])}
        aircraft_by_id = {row["aircraft_id"]: row for row in data.get("aircrafts", [])}

        for flight in data.get("flights", []):
            dep = datetime.fromisoformat(flight["departure_time_local"])
            arr = datetime.fromisoformat(flight["arrival_time_local"])
            if dep >= arr:
                rule_errors.append(f"Invalid flight time order {flight['flight_id']}")
            min_dur, max_dur = catalogs.route_duration_range(flight["origin"], flight["destination"])
            if not (min_dur <= int(flight["duration_minutes"]) <= max_dur):
                rule_errors.append(f"Unrealistic duration {flight['flight_id']}")
            for key in ("economy_inventory", "premium_economy_inventory", "business_inventory"):
                if int(flight[key]) < 0:
                    rule_errors.append(f"Negative inventory on flight {flight['flight_id']}")

        for booking in data.get("bookings", []):
            flight_id = booking["flight_id"]
            if flight_id not in flight_ids:
                continue
            flight = flights_by_id[flight_id]
            if flight["selling_status"] not in ("OPEN", "LIMITED"):
                rule_errors.append(f"Booking {booking['booking_id']} on non-sellable flight")

            aircraft = aircraft_by_id[flight["aircraft_id"]]
            seat_map = catalogs.SEAT_MAPS[aircraft["seat_map_id"]]
            valid_seats = set(seat_map["economy"] + seat_map["premium_economy"] + seat_map["business"])
            local_seen: set[str] = set()
            for pax in booking["passengers"]:
                seat = pax["seat_number"]
                if seat not in valid_seats:
                    rule_errors.append(f"Invalid seat {seat} in booking {booking['booking_id']}")
                if seat in local_seen:
                    rule_errors.append(f"Duplicate seat in booking {booking['booking_id']}")
                local_seen.add(seat)

        seat_map_by_flight: dict[str, set[str]] = {}
        for booking in data.get("bookings", []):
            taken = seat_map_by_flight.setdefault(booking["flight_id"], set())
            for pax in booking["passengers"]:
                seat = pax["seat_number"]
                if seat in taken:
                    rule_errors.append(f"Seat duplicated on flight {booking['flight_id']}: {seat}")
                taken.add(seat)

        for irop in data.get("irops", []):
            if irop["flight_id"] not in flight_ids:
                continue
            evt = irop["event_type"]
            if evt in {"DELAY", "CREW_DELAY", "ATC_DELAY", "WEATHER", "MAINTENANCE"}:
                if not irop.get("delay_minutes") or int(irop["delay_minutes"]) <= 0:
                    rule_errors.append(f"IROP {irop['irop_id']} missing positive delay")
                if not irop.get("revised_departure_time"):
                    rule_errors.append(f"IROP {irop['irop_id']} missing revised departure")
            if evt == "DIVERSION" and not irop.get("diversion_airport"):
                rule_errors.append(f"IROP {irop['irop_id']} missing diversion airport")
            if evt == "CANCELLATION" and irop.get("delay_minutes"):
                rule_errors.append(f"IROP {irop['irop_id']} cancellation should not have delay minutes")

        self._validate_aircraft_overlap(data.get("flights", []), rule_errors)
        self._validate_overbooking(data.get("flights", []), data.get("bookings", []), rule_errors)
        self._validate_baggage(
            data.get("manage_travel", []),
            data.get("bookings", []),
            data.get("flights", []),
            rule_errors,
        )
        self._validate_travel_alignment(
            data.get("manage_travel", []),
            data.get("bookings", []),
            data.get("flights", []),
            rule_errors,
        )

        return rule_errors

    def _validate_aircraft_overlap(self, flights: list[dict], errors: list[str]) -> None:
        by_aircraft: dict[str, list[tuple[datetime, datetime, str]]] = {}
        for flight in flights:
            dep = datetime.fromisoformat(flight["departure_time_local"])
            arr = datetime.fromisoformat(flight["arrival_time_local"])
            by_aircraft.setdefault(flight["aircraft_id"], []).append((dep, arr, flight["flight_id"]))
        for _, slots in by_aircraft.items():
            slots.sort(key=lambda x: x[0])
            for prev, curr in zip(slots, slots[1:], strict=False):
                if curr[0] < prev[1]:
                    errors.append(f"Aircraft schedule overlap between {prev[2]} and {curr[2]}")

    def _validate_overbooking(self, flights: list[dict], bookings: list[dict], errors: list[str]) -> None:
        inventory_by_flight = {
            fl["flight_id"]: fl["economy_inventory"] + fl["premium_economy_inventory"] + fl["business_inventory"]
            for fl in flights
        }
        booked_by_flight: dict[str, int] = {}
        for bk in bookings:
            booked_by_flight[bk["flight_id"]] = booked_by_flight.get(bk["flight_id"], 0) + int(
                bk["passenger_count"]
            )
        for flight_id, booked in booked_by_flight.items():
            if booked > inventory_by_flight.get(flight_id, 0):
                errors.append(f"Overbooking on flight {flight_id}")

    def _validate_baggage(
        self,
        manage_travel: list[dict],
        bookings: list[dict],
        flights: list[dict],
        errors: list[str],
    ) -> None:
        bookings_by_pnr = {row["pnr"]: row for row in bookings}
        flights_by_id = {row["flight_id"]: row for row in flights}
        for mt in manage_travel:
            pnr = mt["pnr"]
            if pnr not in bookings_by_pnr:
                continue
            booking = bookings_by_pnr[pnr]
            flight = flights_by_id.get(booking["flight_id"])
            if not flight:
                continue
            rule = catalogs.BAGGAGE_RULES[flight["baggage_rule_id"]]
            for bag in mt["extra_bags"]:
                if int(bag.get("count", 0)) > rule["max_checked_bags"]:
                    errors.append(f"Baggage rule violation on pnr {pnr}")

    def _validate_travel_alignment(
        self,
        manage_travel: list[dict],
        bookings: list[dict],
        flights: list[dict],
        errors: list[str],
    ) -> None:
        bookings_by_pnr = {row["pnr"]: row for row in bookings}
        flights_by_id = {row["flight_id"]: row for row in flights}
        for mt in manage_travel:
            booking = bookings_by_pnr.get(mt["pnr"])
            if not booking:
                continue
            flight = flights_by_id.get(booking["flight_id"])
            if not flight:
                continue
            arrival_time = datetime.fromisoformat(flight["arrival_time_local"])
            arrival_date = arrival_time.date()
            car = mt.get("car_booking")
            if car:
                if car.get("pickup_airport") != flight["destination"]:
                    errors.append(f"Car pickup airport mismatch for pnr {mt['pnr']}")
                pickup_time = datetime.fromisoformat(car["pickup_time"])
                if pickup_time < arrival_time:
                    errors.append(f"Car pickup before arrival for pnr {mt['pnr']}")
            hotel = mt.get("hotel_booking")
            if hotel:
                check_in = datetime.fromisoformat(hotel["check_in"])
                check_out = datetime.fromisoformat(hotel["check_out"])
                if check_out <= check_in:
                    errors.append(f"Hotel check-out before check-in for pnr {mt['pnr']}")
                if check_in.date() < arrival_date:
                    errors.append(f"Hotel check-in before arrival date for pnr {mt['pnr']}")
