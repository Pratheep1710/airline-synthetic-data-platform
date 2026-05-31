from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    code: str
    country: str
    timezone: str
    domestic: bool


AIRPORTS: dict[str, Airport] = {
    "MAA": Airport("MAA", "IN", "Asia/Kolkata", True),
    "BLR": Airport("BLR", "IN", "Asia/Kolkata", True),
    "DEL": Airport("DEL", "IN", "Asia/Kolkata", True),
    "BOM": Airport("BOM", "IN", "Asia/Kolkata", True),
    "HYD": Airport("HYD", "IN", "Asia/Kolkata", True),
    "CJB": Airport("CJB", "IN", "Asia/Kolkata", True),
    "CCU": Airport("CCU", "IN", "Asia/Kolkata", True),
    "COK": Airport("COK", "IN", "Asia/Kolkata", True),
    "SIN": Airport("SIN", "SG", "Asia/Singapore", False),
    "DXB": Airport("DXB", "AE", "Asia/Dubai", False),
    "DOH": Airport("DOH", "QA", "Asia/Qatar", False),
    "LHR": Airport("LHR", "GB", "Europe/London", False),
}

AIRCRAFT_TYPES = {
    "A320": {"manufacturer": "Airbus", "model": "A320-200", "seat_map_id": "SM-A320", "total": 180},
    "A321": {
        "manufacturer": "Airbus",
        "model": "A321neo",
        "seat_map_id": "SM-A321",
        "total": 210,
    },
    "B738": {"manufacturer": "Boeing", "model": "737-800", "seat_map_id": "SM-B738", "total": 186},
    "B789": {"manufacturer": "Boeing", "model": "787-9", "seat_map_id": "SM-B789", "total": 290},
}

SEAT_MAPS: dict[str, dict[str, list[str]]] = {
    "SM-A320": {"economy": [f"{r}{c}" for r in range(8, 31) for c in "ABCDEF"], "business": [f"{r}{c}" for r in range(1, 8) for c in "ACDF"], "premium_economy": []},
    "SM-A321": {"economy": [f"{r}{c}" for r in range(10, 35) for c in "ABCDEF"], "business": [f"{r}{c}" for r in range(1, 10) for c in "ACDF"], "premium_economy": []},
    "SM-B738": {"economy": [f"{r}{c}" for r in range(7, 31) for c in "ABCDEF"], "business": [f"{r}{c}" for r in range(1, 7) for c in "ACDF"], "premium_economy": []},
    "SM-B789": {
        "economy": [f"{r}{c}" for r in range(20, 51) for c in "ABCDEFGHJK"],
        "premium_economy": [f"{r}{c}" for r in range(10, 20) for c in "ACDFGHJK"],
        "business": [f"{r}{c}" for r in range(1, 10) for c in "ACDF"],
    },
}

BAGGAGE_RULES = {
    "BAG-STD": {"max_checked_bags": 1, "max_weight_per_bag_kg": 23},
    "BAG-PREMIUM": {"max_checked_bags": 2, "max_weight_per_bag_kg": 23},
    "BAG-BIZ": {"max_checked_bags": 2, "max_weight_per_bag_kg": 32},
}

FARE_BRANDS = ["LITE", "VALUE", "FLEX", "BUSINESS_FLEX"]
MEAL_OPTIONS = ["VEG", "NON_VEG", "JAIN", "NO_MEAL"]
SSR_CODES = ["WCHR", "WCHS", "BLND", "DEAF", "PETC", "NONE"]

ROUTE_DURATION_RULES = {
    "DOMESTIC": (45, 210),
    "MIDDLE_EAST_SIN": (180, 330),
    "LHR": (540, 660),
}

ROUTES: list[tuple[str, str]] = [
    ("MAA", "BLR"),
    ("BLR", "DEL"),
    ("DEL", "BOM"),
    ("BOM", "HYD"),
    ("HYD", "COK"),
    ("CCU", "DEL"),
    ("MAA", "CJB"),
    ("BOM", "DXB"),
    ("MAA", "SIN"),
    ("DEL", "DOH"),
    ("BLR", "LHR"),
    ("MAA", "LHR"),
    ("COK", "DXB"),
]


def route_duration_range(origin: str, destination: str) -> tuple[int, int]:
    if destination == "LHR":
        return ROUTE_DURATION_RULES["LHR"]
    if AIRPORTS[origin].domestic and AIRPORTS[destination].domestic:
        return ROUTE_DURATION_RULES["DOMESTIC"]
    return ROUTE_DURATION_RULES["MIDDLE_EAST_SIN"]
