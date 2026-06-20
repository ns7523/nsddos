"""Deterministic release validation."""

from __future__ import annotations

from nsddos.release.contracts import (
    COMPLIANCE_STATES,
    DEPENDENCY_HEALTH_STATES,
    HARDENING_STATES,
    RELEASE_STATES,
    ReleaseCandidateEvaluation,
)


def validate_release_candidate(evaluation: ReleaseCandidateEvaluation) -> list[str]:
    """Validate release candidate evaluation."""
    errors: list[str] = []
    if evaluation.benchmark_score < 0.0 or evaluation.benchmark_score > 1.0:
        errors.append("benchmark_corruption")
    if evaluation.load_test_score < 0.0 or evaluation.stress_test_score < 0.0:
        errors.append("load_or_stress_corruption")
    if (
        evaluation.dependency_health not in DEPENDENCY_HEALTH_STATES
        or evaluation.dependencies.dependency_health not in DEPENDENCY_HEALTH_STATES
    ):
        errors.append("dependency_audit_failure")
    if evaluation.security_score < 0.0 or evaluation.security_score > 1.0:
        errors.append("security_audit_failure")
    if evaluation.hardening_state not in HARDENING_STATES:
        errors.append("hardening_failure")
    if evaluation.compliance_state not in COMPLIANCE_STATES:
        errors.append("compliance_failure")
    if evaluation.release_state not in RELEASE_STATES:
        errors.append("release_package_corruption")
    if not evaluation.package_metadata.bundle_name or not evaluation.package_metadata.archive_name:
        errors.append("packaging_failure")
    if not evaluation.artifacts or any(not item.checksum or not item.signature for item in evaluation.artifacts):
        errors.append("artifact_corruption")
    if not evaluation.release_notes.title or not evaluation.release_notes.summary:
        errors.append("release_notes_corruption")
    return errors
