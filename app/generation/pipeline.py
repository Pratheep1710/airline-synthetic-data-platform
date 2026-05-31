from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.generation.deterministic_generator import DeterministicDataGenerator, GeneratedDataset
from app.generation.llm_enrichment import get_llm_client
from app.validation.business_validator import BusinessValidator
from app.validation.duplicate_validator import DuplicateValidator
from app.validation.realism_validator import RealismValidator
from app.validation.referential_validator import ReferentialIntegrityValidator
from app.validation.schema_validator import JsonSchemaValidator
from app.validation.validation_report import ValidationReport

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    dataset_version: str
    generated: GeneratedDataset
    validation_report: ValidationReport


def _to_dict(dataset: GeneratedDataset) -> dict[str, list[dict[str, Any]]]:
    def _row(obj: Any) -> dict[str, Any]:
        data = {}
        for key, value in obj.__dict__.items():
            if key.startswith("_"):
                continue
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif hasattr(value, "value"):
                data[key] = value.value
            else:
                data[key] = value
        return data

    return {
        "aircrafts": [_row(row) for row in dataset.aircrafts],
        "flights": [_row(row) for row in dataset.flights],
        "bookings": [_row(row) for row in dataset.bookings],
        "manage_travel": [_row(row) for row in dataset.manage_travel],
        "irops": [_row(row) for row in dataset.irops],
    }


class GenerationPipeline:
    def __init__(self, db: Session, schema_dir: str = "json_schemas") -> None:
        self.db = db
        self.schema_validator = JsonSchemaValidator(schema_dir=schema_dir)
        self.duplicate_validator = DuplicateValidator()
        self.referential_validator = ReferentialIntegrityValidator()
        self.business_validator = BusinessValidator()
        self.realism_validator = RealismValidator()

    async def run(
        self,
        dataset_version: str,
        record_count: int,
        enable_llm_enrichment: bool = False,
    ) -> PipelineResult:
        run_start = perf_counter()
        logger.info(
            "pipeline_started",
            extra={
                "dataset_version": dataset_version,
                "record_count": record_count,
                "enable_llm_enrichment": enable_llm_enrichment,
            },
        )
        llm_client = get_llm_client(enable_llm=enable_llm_enrichment)
        generator = DeterministicDataGenerator(dataset_version, record_count, llm_client=llm_client)

        generate_start = perf_counter()
        generated = await generator.generate()
        logger.info(
            "pipeline_stage_generated",
            extra={
                "dataset_version": dataset_version,
                "duration_ms": round((perf_counter() - generate_start) * 1000, 2),
                "counts": {
                    "aircrafts": len(generated.aircrafts),
                    "flights": len(generated.flights),
                    "bookings": len(generated.bookings),
                    "manage_travel": len(generated.manage_travel),
                    "irops": len(generated.irops),
                },
            },
        )

        validate_start = perf_counter()
        report = self._validate(generated)
        logger.info(
            "pipeline_stage_validated",
            extra={
                "dataset_version": dataset_version,
                "duration_ms": round((perf_counter() - validate_start) * 1000, 2),
                "schema_valid": report.schema_valid,
                "business_rules_valid": report.business_rules_valid,
                "duplicates_found": report.duplicates_found,
                "referential_error_count": len(report.referential_errors),
                "business_error_count": len(report.business_rule_errors),
                "realism_score": report.realism_score,
            },
        )

        if not self._is_valid(report):
            logger.info("Validation failed, attempting deterministic repair loop")
            repair_start = perf_counter()
            generated = self._repair(generated, report)
            logger.info(
                "pipeline_stage_repaired",
                extra={
                    "dataset_version": dataset_version,
                    "duration_ms": round((perf_counter() - repair_start) * 1000, 2),
                },
            )

            revalidate_start = perf_counter()
            report = self._validate(generated)
            logger.info(
                "pipeline_stage_revalidated",
                extra={
                    "dataset_version": dataset_version,
                    "duration_ms": round((perf_counter() - revalidate_start) * 1000, 2),
                    "schema_valid": report.schema_valid,
                    "business_rules_valid": report.business_rules_valid,
                    "duplicates_found": report.duplicates_found,
                    "referential_error_count": len(report.referential_errors),
                    "business_error_count": len(report.business_rule_errors),
                    "realism_score": report.realism_score,
                },
            )

        persist_start = perf_counter()
        self._persist(generated)
        logger.info(
            "pipeline_stage_persisted",
            extra={
                "dataset_version": dataset_version,
                "duration_ms": round((perf_counter() - persist_start) * 1000, 2),
            },
        )

        logger.info(
            "pipeline_completed",
            extra={
                "dataset_version": dataset_version,
                "total_duration_ms": round((perf_counter() - run_start) * 1000, 2),
                "final_schema_valid": report.schema_valid,
                "final_business_rules_valid": report.business_rules_valid,
                "final_duplicates_found": report.duplicates_found,
                "final_realism_score": report.realism_score,
            },
        )
        return PipelineResult(dataset_version=dataset_version, generated=generated, validation_report=report)

    def _persist(self, generated: GeneratedDataset) -> None:
        for row in generated.aircrafts + generated.flights + generated.bookings + generated.manage_travel + generated.irops:
            self.db.add(row)
        self.db.flush()

    def _validate(self, generated: GeneratedDataset) -> ValidationReport:
        data = _to_dict(generated)
        report = ValidationReport()

        report.schema_valid, schema_errors = self.schema_validator.validate_all(data)
        if schema_errors:
            report.business_rule_errors.extend(schema_errors)

        duplicates, duplicate_errors = self.duplicate_validator.validate(data)
        report.duplicates_found = duplicates
        report.business_rule_errors.extend(duplicate_errors)

        ref_errors = self.referential_validator.validate(data)
        business_errors = self.business_validator.validate(data)
        report.referential_errors.extend(ref_errors)
        report.business_rule_errors.extend(business_errors)
        report.business_rules_valid = not (ref_errors or business_errors or duplicates)

        score, warnings = self.realism_validator.score(data)
        report.realism_score = score
        report.warnings = warnings
        return report

    def _is_valid(self, report: ValidationReport) -> bool:
        return (
            report.schema_valid
            and report.business_rules_valid
            and report.duplicates_found == 0
            and not report.referential_errors
            and report.realism_score >= 80
        )

    def _repair(self, generated: GeneratedDataset, report: ValidationReport) -> GeneratedDataset:
        if report.realism_score < 80:
            for irop in generated.irops:
                if len(irop.customer_message) < 30:
                    irop.customer_message = (
                        f"Flight {irop.flight_id} impacted. Guests can rebook without change fee."
                    )
        for irop in generated.irops:
            if irop.event_type in {
                models.IropEventType.DELAY,
                models.IropEventType.ATC_DELAY,
                models.IropEventType.CREW_DELAY,
                models.IropEventType.WEATHER,
                models.IropEventType.MAINTENANCE,
            } and (not irop.delay_minutes or irop.delay_minutes <= 0):
                irop.delay_minutes = 30
                irop.revised_departure_time = (
                    irop.original_departure_time or datetime.now(UTC)
                ) + timedelta(minutes=30)
        return generated


def request_counts(record_count: int) -> dict[str, int]:
    return {
        "available_aircrafts": record_count,
        "available_flights": record_count,
        "bookings": record_count,
        "manage_travel": record_count,
        "irops": record_count,
    }
