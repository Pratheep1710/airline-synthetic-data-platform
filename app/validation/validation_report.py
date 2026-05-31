from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    schema_valid: bool = True
    business_rules_valid: bool = True
    duplicates_found: int = 0
    referential_errors: list[str] = field(default_factory=list)
    business_rule_errors: list[str] = field(default_factory=list)
    realism_score: int = 100
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "schema_valid": self.schema_valid,
            "business_rules_valid": self.business_rules_valid,
            "duplicates_found": self.duplicates_found,
            "referential_errors": self.referential_errors,
            "business_rule_errors": self.business_rule_errors,
            "realism_score": self.realism_score,
            "warnings": self.warnings,
        }
