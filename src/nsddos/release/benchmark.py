"""Deterministic benchmark evaluation."""

from __future__ import annotations

from nsddos.release.contracts import BenchmarkResult, ReleaseSourceBundle, ScenarioResult


def _bounded_score(value: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0
    return round(min(value / baseline, 1.0), 4)


def build_benchmark_result(
    config: dict,
    sources: ReleaseSourceBundle,
) -> BenchmarkResult:
    """Build deterministic benchmark result from persisted state."""
    target = max(float(config.get("release", {}).get("stream_burst_count", 256)), 1.0)
    detection_throughput = round(max(sources.ml_confidence * 100.0, 5.0), 4)
    mitigation_throughput = round(max(float(sources.mitigation_events) * 2.0, 2.0), 4)
    streaming_throughput = round(max(sources.stream_throughput, 0.1), 4)
    cluster_throughput = round(max(float(sources.active_nodes) * 25.0, 10.0), 4)
    scenarios = (
        ScenarioResult(
            "benchmark-detection",
            _bounded_score(detection_throughput, 100.0),
            "healthy" if detection_throughput >= 50.0 else "degraded",
            f"detection_throughput={detection_throughput:.4f}",
        ),
        ScenarioResult(
            "benchmark-mitigation",
            _bounded_score(mitigation_throughput, 50.0),
            "healthy" if mitigation_throughput >= 10.0 else "degraded",
            f"mitigation_throughput={mitigation_throughput:.4f}",
        ),
        ScenarioResult(
            "benchmark-streaming",
            _bounded_score(streaming_throughput, target),
            "healthy" if sources.dashboard_health != "failed" else "degraded",
            f"streaming_throughput={streaming_throughput:.4f}",
        ),
        ScenarioResult(
            "benchmark-cluster",
            _bounded_score(cluster_throughput, 100.0),
            "healthy" if sources.cluster_health == "healthy" else "degraded",
            f"cluster_throughput={cluster_throughput:.4f}",
        ),
    )
    benchmark_score = round(sum(item.score for item in scenarios) / len(scenarios), 4)
    return BenchmarkResult(
        detection_throughput=detection_throughput,
        mitigation_throughput=mitigation_throughput,
        streaming_throughput=streaming_throughput,
        cluster_throughput=cluster_throughput,
        benchmark_score=benchmark_score,
        scenarios=scenarios,
    )
