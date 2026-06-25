"""Deterministic load-testing contracts."""

from __future__ import annotations

from nsddos.release.contracts import LoadTestResult, ReleaseSourceBundle, ScenarioResult


def build_load_test_result(
    config: dict, sources: ReleaseSourceBundle
) -> LoadTestResult:
    """Build deterministic load test result."""
    release_config = config.get("release", {})
    event_workload = int(release_config.get("load_event_count", 10000))
    api_burst = int(release_config.get("api_burst_count", 250))
    stream_burst = int(release_config.get("stream_burst_count", 256))
    provider_burst = int(release_config.get("provider_burst_count", 128))
    scenarios = (
        ScenarioResult(
            "load-events",
            round(
                min(
                    max(sources.stream_throughput, 0.1) / max(stream_burst / 10.0, 1.0),
                    1.0,
                ),
                4,
            ),
            "healthy" if sources.stream_throughput >= 1.0 else "degraded",
            f"event_workload={event_workload}",
        ),
        ScenarioResult(
            "load-api-burst",
            round(min((1.0 if sources.service_health != "failed" else 0.35), 1.0), 4),
            "healthy" if sources.service_health == "healthy" else "degraded",
            f"api_burst_count={api_burst}",
        ),
        ScenarioResult(
            "load-stream-pressure",
            round(
                min(max(sources.stream_throughput, 0.1) / max(stream_burst, 1), 1.0), 4
            ),
            "healthy" if sources.dashboard_health != "failed" else "degraded",
            f"stream_burst_count={stream_burst}",
        ),
        ScenarioResult(
            "load-provider-burst",
            1.0 if sources.provider_burst_supported else 0.5,
            "healthy" if sources.provider_burst_supported else "degraded",
            f"provider_burst_count={provider_burst}",
        ),
    )
    score = round(sum(item.score for item in scenarios) / len(scenarios), 4)
    return LoadTestResult(
        event_workload, api_burst, stream_burst, provider_burst, score, scenarios
    )
