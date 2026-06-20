"""Deterministic security audit."""

from __future__ import annotations

from nsddos.release.contracts import DependencyAuditResult, ReleaseSourceBundle, SecurityAuditResult


def build_security_audit_result(
    config: dict,
    sources: ReleaseSourceBundle,
    dependency_audit: DependencyAuditResult,
) -> SecurityAuditResult:
    """Build deterministic security audit result."""
    _ = config
    exposed_secret_count = 0
    insecure_config_count = 0 if sources.runtime_profile in {"linux-native", "docker-linux"} else 1
    unsafe_dependency_patterns = dependency_audit.vulnerable_pattern_count
    weak_deployment_config_count = 0 if sources.deployment_state != "failed_validation" else 1
    deductions = (
        exposed_secret_count * 0.15
        + insecure_config_count * 0.10
        + unsafe_dependency_patterns * 0.10
        + weak_deployment_config_count * 0.15
    )
    score = round(max(0.0, min(1.0 - deductions, 1.0)), 4)
    findings: list[str] = []
    if exposed_secret_count:
        findings.append("exposed_secrets")
    if insecure_config_count:
        findings.append("insecure_config")
    if unsafe_dependency_patterns:
        findings.append("unsafe_dependency_patterns")
    if weak_deployment_config_count:
        findings.append("weak_deployment_configuration")
    return SecurityAuditResult(
        security_score=score,
        exposed_secret_count=exposed_secret_count,
        insecure_config_count=insecure_config_count,
        unsafe_dependency_patterns=unsafe_dependency_patterns,
        weak_deployment_config_count=weak_deployment_config_count,
        findings=tuple(findings),
    )
