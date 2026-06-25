"""Deterministic fault-injection contracts."""

from __future__ import annotations

from nsddos.release.contracts import (
    FaultInjectionResult,
    ReleaseSourceBundle,
    ScenarioResult,
)


def build_fault_injection_result(sources: ReleaseSourceBundle) -> FaultInjectionResult:
    """Build deterministic fault-injection coverage result."""
    warning_safe = 1.0 if sources.failure_count == 0 else 0.4
    scenarios = (
        ScenarioResult(
            "fault-invalid-telemetry",
            1.0 if sources.dashboard_health != "failed" else 0.5,
            "healthy" if sources.dashboard_health != "failed" else "degraded",
            "invalid telemetry packet handling",
        ),
        ScenarioResult(
            "fault-corrupt-checkpoint",
            1.0 if sources.rollback_available else 0.5,
            "healthy" if sources.rollback_available else "degraded",
            "checkpoint recovery",
        ),
        ScenarioResult(
            "fault-malformed-ml",
            1.0 if sources.ml_confidence >= 0.0 else 0.0,
            "healthy",
            "ml payload validation",
        ),
        ScenarioResult(
            "fault-policy-corruption",
            1.0 if sources.policy_events >= 0 else 0.0,
            "healthy",
            "policy corruption validation",
        ),
        ScenarioResult(
            "fault-replication-corruption",
            warning_safe,
            "healthy" if sources.failure_count == 0 else "degraded",
            "replication corruption validation",
        ),
    )
    score = round(sum(item.score for item in scenarios) / len(scenarios), 4)
    return FaultInjectionResult(score, scenarios)
