from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    sort_by: str | None = None
    sort_dir: str = Field(default="asc", pattern="^(asc|desc)$")
    dataset_version: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ValidationReportSchema(BaseModel):
    schema_valid: bool
    business_rules_valid: bool
    duplicates_found: int
    referential_errors: list[str]
    business_rule_errors: list[str]
    realism_score: int
    warnings: list[str]


class GenerationJobRequest(BaseModel):
    record_count: int = Field(default=75, ge=1, le=5000)
    enable_llm_enrichment: bool = False
    dataset_version: str | None = Field(
        default=None,
        description="Optional. Leave empty to auto-generate a unique dataset version.",
    )

    @field_validator("dataset_version", mode="before")
    @classmethod
    def normalize_dataset_version(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        # Swagger's default placeholder value often appears as literal "string".
        if normalized == "" or normalized.lower() == "string":
            return None
        return normalized


class GenerationJobResponse(BaseModel):
    job_id: str
    dataset_version: str
    status: str
    validation_status: str | None = None
    requested_counts: dict[str, int]
    validation_errors: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None
