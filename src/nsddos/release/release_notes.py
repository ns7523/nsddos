"""Deterministic release notes generation."""

from __future__ import annotations

from nsddos.release.contracts import (
    ComplianceResult,
    HardeningResult,
    ReleaseNotesPayload,
    SecurityAuditResult,
)


def build_release_notes(
    release_version: str,
    benchmark_score: float,
    security_audit: SecurityAuditResult,
    hardening: HardeningResult,
    compliance: ComplianceResult,
) -> ReleaseNotesPayload:
    """Build deterministic release notes payload."""
    known_limitations = tuple(
        finding
        for finding in (
            *security_audit.findings,
            *hardening.findings,
            *compliance.findings,
        )
    ) or ("no_blocking_limitations_recorded",)
    return ReleaseNotesPayload(
        title=f"NS-DDoS {release_version} Release Candidate",
        summary=f"Deterministic release evaluation for {release_version}",
        benchmark_summary=f"benchmark_score={benchmark_score:.4f}",
        security_summary=f"security_score={security_audit.security_score:.4f}",
        deployment_summary=(
            f"hardening_state={hardening.hardening_state} "
            f"compliance_state={compliance.compliance_state}"
        ),
        known_limitations=known_limitations,
    )
