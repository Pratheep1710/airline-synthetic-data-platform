from __future__ import annotations

from app.validation.duplicate_validator import DuplicateValidator


def test_duplicate_validator_catches_duplicates():
    payload = {
        "aircrafts": [
            {"aircraft_id": "AC-A320-0001", "tail_number": "VT-AA1"},
            {"aircraft_id": "AC-A320-0001", "tail_number": "VT-AA1"},
        ],
        "flights": [{"flight_id": "F1"}, {"flight_id": "F1"}],
        "bookings": [
            {"booking_id": "B1", "pnr": "ABC123"},
            {"booking_id": "B1", "pnr": "ABC123"},
        ],
        "manage_travel": [{"manage_travel_id": "M1"}, {"manage_travel_id": "M1"}],
        "irops": [{"irop_id": "I1"}, {"irop_id": "I1"}],
    }
    duplicates, errors = DuplicateValidator().validate(payload)
    assert duplicates > 0
    assert errors
