"""Deterministic release diagnostics."""

from __future__ import annotations

from nsddos.release.contracts import (
    DependencyAuditResult,
    ReleaseDiagnostics,
    SecurityAuditResult,
    StressTestResult,
)


def build_release_diagnostics(
    latency_ms: float,
    benchmark_score: float,
    stress_test: StressTestResult,
    dependencies: DependencyAuditResult,
    security_audit: SecurityAuditResult,
) -> ReleaseDiagnostics:
    """Build release diagnostics payload."""
    return ReleaseDiagnostics(
        release_latency_ms=round(latency_ms, 2),
        benchmark_diagnostics=(f"benchmark_score={benchmark_score:.4f}",),
        stress_diagnostics=tuple(item.detail for item in stress_test.scenarios),
        dependency_diagnostics=(
            f"dependency_health={dependencies.dependency_health}",
            f"conflict_count={dependencies.conflict_count}",
        ),
        security_diagnostics=(
            f"security_score={security_audit.security_score:.4f}",
            f"finding_count={len(security_audit.findings)}",
        ),
    )
