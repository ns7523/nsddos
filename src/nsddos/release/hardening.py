"""Deterministic release hardening validation."""

from __future__ import annotations

from nsddos.release.contracts import HardeningResult, ReleaseSourceBundle


def build_hardening_result(
    config: dict, sources: ReleaseSourceBundle
) -> HardeningResult:
    """Build hardening validation result."""
    runtime_live_enabled = bool(
        config.get("runtime", {}).get("live", {}).get("enabled", False)
    )
    production_config_ready = bool(config.get("release", {}).get("version"))
    strict_runtime_config = not runtime_live_enabled or sources.provider_burst_supported
    secret_enforcement = sources.missing_secret_count == 0
    deployment_integrity = sources.deployment_state != "failed_validation"
    findings: list[str] = []
    if not production_config_ready:
        findings.append("missing_release_version")
    if not strict_runtime_config:
        findings.append("runtime_config_not_strict")
    if not secret_enforcement:
        findings.append("secret_enforcement_failed")
    if not deployment_integrity:
        findings.append("deployment_integrity_failed")
    if all(
        (
            production_config_ready,
            strict_runtime_config,
            secret_enforcement,
            deployment_integrity,
        )
    ):
        state = "strict"
    elif deployment_integrity:
        state = "degraded"
    else:
        state = "failed"
    return HardeningResult(
        hardening_state=state,
        production_config_ready=production_config_ready,
        strict_runtime_config=strict_runtime_config,
        secret_enforcement=secret_enforcement,
        deployment_integrity=deployment_integrity,
        findings=tuple(findings),
    )
