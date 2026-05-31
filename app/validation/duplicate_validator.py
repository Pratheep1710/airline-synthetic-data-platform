from __future__ import annotations

from collections import Counter
from typing import Any


class DuplicateValidator:
    @staticmethod
    def _count_duplicates(values: list[Any]) -> int:
        counts = Counter(values)
        return sum(count - 1 for count in counts.values() if count > 1)

    def validate(self, data: dict[str, list[dict]]) -> tuple[int, list[str]]:
        errors: list[str] = []
        duplicate_count = 0
        rules = [
            ("aircrafts", "aircraft_id"),
            ("aircrafts", "tail_number"),
            ("flights", "flight_id"),
            ("bookings", "booking_id"),
            ("bookings", "pnr"),
            ("manage_travel", "manage_travel_id"),
            ("irops", "irop_id"),
        ]

        for bucket, field in rules:
            values = [row[field] for row in data.get(bucket, [])]
            duplicates = self._count_duplicates(values)
            duplicate_count += duplicates
            if duplicates:
                errors.append(f"Duplicate {field} found in {bucket}: {duplicates}")
        return duplicate_count, errors
