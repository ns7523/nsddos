"""Deterministic chaos-readiness contracts."""

from __future__ import annotations

from nsddos.release.contracts import ChaosResult, ReleaseSourceBundle, ScenarioResult


def build_chaos_result(sources: ReleaseSourceBundle) -> ChaosResult:
    """Build deterministic chaos-readiness result."""
    scenarios = (
        ScenarioResult(
            "chaos-provider-outage",
            1.0 if sources.provider_burst_supported else 0.5,
            "healthy" if sources.provider_burst_supported else "degraded",
            "provider outage contract",
        ),
        ScenarioResult(
            "chaos-node-failure",
            1.0 if sources.rollback_available else 0.6,
            "healthy" if sources.rollback_available else "degraded",
            "node failure readiness",
        ),
        ScenarioResult(
            "chaos-leader-failure",
            1.0 if sources.active_nodes > 1 else 0.5,
            "healthy" if sources.active_nodes > 1 else "degraded",
            "leader failover readiness",
        ),
        ScenarioResult(
            "chaos-api-outage",
            1.0 if sources.service_health == "healthy" else 0.5,
            "healthy" if sources.service_health == "healthy" else "degraded",
            "api outage resilience",
        ),
        ScenarioResult(
            "chaos-stream-corruption",
            1.0 if sources.dashboard_health != "failed" else 0.4,
            "healthy" if sources.dashboard_health != "failed" else "degraded",
            "stream corruption recovery",
        ),
    )
    score = round(sum(item.score for item in scenarios) / len(scenarios), 4)
    return ChaosResult(score, scenarios)
