"""Deterministic compliance validation."""

from __future__ import annotations

from nsddos.release.contracts import ComplianceResult, HardeningResult, ReleaseSourceBundle


def build_compliance_result(sources: ReleaseSourceBundle, hardening: HardeningResult) -> ComplianceResult:
    """Build deterministic compliance result."""
    deployment_policy_ok = sources.deployment_state != "failed_validation"
    runtime_policy_ok = sources.failure_count == 0
    release_integrity_ok = hardening.hardening_state != "failed"
    findings: list[str] = []
    if not deployment_policy_ok:
        findings.append("deployment_policy_non_compliant")
    if not runtime_policy_ok:
        findings.append("runtime_policy_non_compliant")
    if not release_integrity_ok:
        findings.append("release_integrity_non_compliant")
    if all((deployment_policy_ok, runtime_policy_ok, release_integrity_ok)):
        state = "compliant"
    elif deployment_policy_ok and release_integrity_ok:
        state = "degraded"
    else:
        state = "failed"
    return ComplianceResult(
        compliance_state=state,
        deployment_policy_ok=deployment_policy_ok,
        runtime_policy_ok=runtime_policy_ok,
        release_integrity_ok=release_integrity_ok,
        findings=tuple(findings),
    )
