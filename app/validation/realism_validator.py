from __future__ import annotations

from datetime import datetime

from app.generation import catalogs


class RealismValidator:
    def score(self, data: dict[str, list[dict]]) -> tuple[int, list[str]]:
        score = 100
        warnings: list[str] = []

        for flight in data.get("flights", []):
            if flight["origin"] == flight["destination"]:
                score -= 15
                warnings.append(f"Route realism issue in {flight['flight_id']}")
            min_dur, max_dur = catalogs.route_duration_range(flight["origin"], flight["destination"])
            duration = int(flight["duration_minutes"])
            if duration < min_dur or duration > max_dur:
                score -= 10
                warnings.append(f"Schedule realism issue in {flight['flight_id']}")

        for irop in data.get("irops", []):
            if len(irop.get("customer_message", "")) < 20:
                score -= 2
                warnings.append(f"Short customer message in {irop['irop_id']}")

        for mt in data.get("manage_travel", []):
            hotel = mt.get("hotel_booking")
            if hotel:
                check_in = datetime.fromisoformat(hotel["check_in"])
                check_out = datetime.fromisoformat(hotel["check_out"])
                if check_out <= check_in:
                    score -= 5
                    warnings.append(f"Hotel date alignment issue in {mt['manage_travel_id']}")

        score = max(0, min(100, score))
        return score, warnings
