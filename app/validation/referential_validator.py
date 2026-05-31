from __future__ import annotations


class ReferentialIntegrityValidator:
    def validate(self, data: dict[str, list[dict]]) -> list[str]:
        errors: list[str] = []
        aircraft_ids = {row["aircraft_id"] for row in data.get("aircrafts", [])}
        flight_ids = {row["flight_id"] for row in data.get("flights", [])}
        bookings_by_pnr = {row["pnr"]: row for row in data.get("bookings", [])}

        for flight in data.get("flights", []):
            if flight["aircraft_id"] not in aircraft_ids:
                errors.append(f"Flight {flight['flight_id']} references missing aircraft_id")

        for booking in data.get("bookings", []):
            if booking["flight_id"] not in flight_ids:
                errors.append(f"Booking {booking['booking_id']} references missing flight_id")

        for mt in data.get("manage_travel", []):
            booking_row: dict | None = bookings_by_pnr.get(mt["pnr"])
            if booking_row is None:
                errors.append(f"Manage travel {mt['manage_travel_id']} references missing pnr")
            elif booking_row["booking_status"] not in ("CONFIRMED", "TICKETED"):
                errors.append(
                    f"Manage travel {mt['manage_travel_id']} references non-confirmed/ticketed pnr"
                )

        for irop in data.get("irops", []):
            if irop["flight_id"] not in flight_ids:
                errors.append(f"IROP {irop['irop_id']} references missing flight_id")

        return errors
