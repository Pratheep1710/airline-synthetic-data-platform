from __future__ import annotations

import random
import string
from datetime import datetime


class DeterministicIdGenerator:
    def __init__(self, seed: int = 42, namespace: str = "AAAA") -> None:
        self.random = random.Random(seed)
        cleaned = "".join(ch for ch in namespace.upper() if ch.isalnum())
        self.namespace_id = cleaned[:4].ljust(4, "A")
        self.namespace_pnr = cleaned[:2].ljust(2, "A")
        self.counters = {
            "aircraft": 0,
            "flight": 0,
            "booking": 0,
            "manage_travel": 0,
            "irop": 0,
        }
        self.generated_pnrs: set[str] = set()

    def aircraft_id(self, aircraft_type: str) -> str:
        self.counters["aircraft"] += 1
        return f"AC-{aircraft_type}-{self.namespace_id}{self.counters['aircraft']:04d}"

    def flight_id(self, departure_date: datetime, flight_number: str) -> str:
        self.counters["flight"] += 1
        return (
            f"FLT-{departure_date:%Y%m%d}-{flight_number}-"
            f"{self.namespace_id}{self.counters['flight']:04d}"
        )

    def booking_id(self) -> str:
        self.counters["booking"] += 1
        return f"BKG-{self.namespace_id}{self.counters['booking']:06d}"

    def manage_travel_id(self) -> str:
        self.counters["manage_travel"] += 1
        return f"MT-{self.namespace_id}{self.counters['manage_travel']:06d}"

    def irop_id(self) -> str:
        self.counters["irop"] += 1
        return f"IROP-{self.namespace_id}{self.counters['irop']:06d}"

    def pnr(self) -> str:
        while True:
            candidate = self.namespace_pnr + "".join(
                self.random.choices(string.ascii_uppercase + string.digits, k=4)
            )
            if candidate not in self.generated_pnrs:
                self.generated_pnrs.add(candidate)
                return candidate
