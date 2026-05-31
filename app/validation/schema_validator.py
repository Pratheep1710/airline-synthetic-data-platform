from __future__ import annotations

import json
from pathlib import Path

from jsonschema import ValidationError, validate


class JsonSchemaValidator:
    def __init__(self, schema_dir: str = "json_schemas") -> None:
        path = Path(schema_dir)
        if path.is_absolute():
            self.schema_dir = path
        else:
            self.schema_dir = Path(__file__).resolve().parents[2] / schema_dir

    def _load_schema(self, name: str) -> dict:
        with (self.schema_dir / f"{name}.schema.json").open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def validate_all(self, data: dict[str, list[dict]]) -> tuple[bool, list[str]]:
        errors: list[str] = []
        mapping = {
            "aircrafts": "aircraft",
            "flights": "flight",
            "bookings": "booking",
            "manage_travel": "manage_travel",
            "irops": "irop",
        }

        for entity, schema_name in mapping.items():
            schema = self._load_schema(schema_name)
            for idx, row in enumerate(data.get(entity, [])):
                try:
                    validate(instance=row, schema=schema)
                except ValidationError as exc:
                    errors.append(f"{entity}[{idx}]: {exc.message}")
        return not errors, errors
