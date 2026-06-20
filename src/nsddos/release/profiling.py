"""Deterministic performance profiling summary."""

from __future__ import annotations

from nsddos.release.contracts import BenchmarkResult, LoadTestResult, ProfilingResult, StressTestResult


def build_profiling_result(
    benchmark: BenchmarkResult,
    load_test: LoadTestResult,
    stress_test: StressTestResult,
) -> ProfilingResult:
    """Build deterministic profiling summary from computed release metrics."""
    memory_usage_score = round(max(0.0, 1.0 - stress_test.memory_pressure_score / 1.5), 4)
    cpu_usage_score = round(max(0.0, 1.0 - stress_test.cpu_pressure_score / 1.5), 4)
    slow_function_score = round(min((benchmark.benchmark_score + load_test.load_test_score) / 2.0, 1.0), 4)
    io_bottleneck_score = round(min(max(benchmark.streaming_throughput, 0.1) / max(load_test.stream_burst_count / 10.0, 1.0), 1.0), 4)
    performance_score = round(
        (memory_usage_score + cpu_usage_score + slow_function_score + io_bottleneck_score) / 4.0,
        4,
    )
    hotspots = (
        f"streaming_throughput={benchmark.streaming_throughput:.4f}",
        f"event_workload={load_test.event_workload}",
        f"cpu_pressure_score={stress_test.cpu_pressure_score:.4f}",
    )
    return ProfilingResult(
        memory_usage_score,
        cpu_usage_score,
        slow_function_score,
        io_bottleneck_score,
        performance_score,
        hotspots,
    )
