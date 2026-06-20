"""Typed verification execution results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nsddos.runtime.models import SCHEMA_VERSION, VerificationResult
from nsddos.runtime.verification.severity import severity_for_status, worst_severity


@dataclass
class VerificationEvidenceReference:
    """Evidence pointer attached to verification output."""

    kind: str
    reference: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationCategoryResult:
    """Category-level verification output."""

    category: str
    results: list[VerificationResult] = field(default_factory=list)
    evidence: list[VerificationEvidenceReference] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def severity(self) -> str:
        return worst_severity([severity_for_status(item.status) for item in self.results])

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "duration_ms": self.duration_ms,
            "results": [item.to_dict() for item in self.results],
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass
class VerificationExecutionResult:
    """Full verification execution output."""

    run_id: str
    timestamp: str
    schema_version: str = SCHEMA_VERSION
    results: list[VerificationResult] = field(default_factory=list)
    categories: list[VerificationCategoryResult] = field(default_factory=list)
    validator_order: list[str] = field(default_factory=list)
    skipped_validators: list[str] = field(default_factory=list)
    degraded_validators: list[str] = field(default_factory=list)
    dependency_graph: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[VerificationEvidenceReference] = field(default_factory=list)
    performance: dict[str, float] = field(default_factory=dict)

    @property
    def severity(self) -> str:
        return worst_severity([severity_for_status(item.status) for item in self.results])

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "results": [item.to_dict() for item in self.results],
            "categories": [item.to_dict() for item in self.categories],
            "validator_order": self.validator_order,
            "skipped_validators": self.skipped_validators,
            "degraded_validators": self.degraded_validators,
            "dependency_graph": self.dependency_graph,
            "evidence": [item.to_dict() for item in self.evidence],
            "performance": self.performance,
        }
