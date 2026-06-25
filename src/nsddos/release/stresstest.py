"""Deterministic stress-test contracts."""

from __future__ import annotations

from nsddos.release.contracts import (
    ReleaseSourceBundle,
    ScenarioResult,
    StressTestResult,
)


def build_stress_test_result(
    config: dict, sources: ReleaseSourceBundle
) -> StressTestResult:
    """Build deterministic stress test result from persisted pressure proxies."""
    target_stream = max(
        float(config.get("release", {}).get("stream_burst_count", 256)), 1.0
    )
    cpu_pressure = round(max(0.2, min((sources.policy_events + 1) / 100.0, 1.0)), 4)
    memory_pressure = round(max(0.2, min((sources.active_alerts + 1) / 10.0, 1.0)), 4)
    queue_overflow = round(
        max(0.2, min(max(sources.stream_throughput, 0.1) / target_stream, 1.0)), 4
    )
    node_denominator = max(float(sources.active_nodes), 1.0)
    saturation = round(
        max(0.2, min((node_denominator - 0.0) / max(node_denominator + 1.0, 1.0), 1.0)),
        4,
    )
    scenarios = (
        ScenarioResult(
            "stress-cpu",
            cpu_pressure,
            "healthy" if cpu_pressure < 0.8 else "degraded",
            f"cpu_pressure_score={cpu_pressure:.4f}",
        ),
        ScenarioResult(
            "stress-memory",
            memory_pressure,
            "healthy" if memory_pressure < 0.8 else "degraded",
            f"memory_pressure_score={memory_pressure:.4f}",
        ),
        ScenarioResult(
            "stress-queue",
            queue_overflow,
            "healthy" if queue_overflow >= 0.2 else "degraded",
            f"queue_overflow_score={queue_overflow:.4f}",
        ),
        ScenarioResult(
            "stress-distributed",
            saturation,
            "healthy" if sources.cluster_health == "healthy" else "degraded",
            f"distributed_saturation_score={saturation:.4f}",
        ),
    )
    stress_score = round(sum(item.score for item in scenarios) / len(scenarios), 4)
    return StressTestResult(
        cpu_pressure,
        memory_pressure,
        queue_overflow,
        saturation,
        stress_score,
        scenarios,
    )
