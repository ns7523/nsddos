"""Typed deterministic release engineering contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from nsddos.runtime.models import SCHEMA_VERSION

DEPENDENCY_HEALTH_STATES = {"healthy", "degraded", "failed"}
HARDENING_STATES = {"strict", "degraded", "failed"}
COMPLIANCE_STATES = {"compliant", "degraded", "failed"}
RELEASE_STATES = {"release_ready", "release_review", "release_blocked"}


@dataclass(frozen=True)
class ReleaseSourceBundle:
    """Typed source bundle extracted from persisted subsystem state."""

    active_nodes: int
    cluster_health: str
    dashboard_health: str
    active_alerts: int
    stream_throughput: float
    ml_confidence: float
    policy_events: int
    mitigation_events: int
    deployment_state: str
    service_health: str
    rollback_available: bool
    missing_secret_count: int
    warning_count: int
    failure_count: int
    runtime_profile: str
    provider_burst_supported: bool
    package_dependencies: tuple[str, ...]
    optional_dependencies: tuple[str, ...]
    manifests: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioResult:
    """Deterministic scenario result."""

    scenario_id: str
    score: float
    status: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkResult:
    """Benchmark summary."""

    detection_throughput: float
    mitigation_throughput: float
    streaming_throughput: float
    cluster_throughput: float
    benchmark_score: float
    scenarios: tuple[ScenarioResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scenarios"] = [item.to_dict() for item in self.scenarios]
        return payload


@dataclass(frozen=True)
class LoadTestResult:
    """Load-test summary."""

    event_workload: int
    api_burst_count: int
    stream_burst_count: int
    provider_burst_count: int
    load_test_score: float
    scenarios: tuple[ScenarioResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scenarios"] = [item.to_dict() for item in self.scenarios]
        return payload


@dataclass(frozen=True)
class StressTestResult:
    """Stress-test summary."""

    cpu_pressure_score: float
    memory_pressure_score: float
    queue_overflow_score: float
    distributed_saturation_score: float
    stress_test_score: float
    scenarios: tuple[ScenarioResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scenarios"] = [item.to_dict() for item in self.scenarios]
        return payload


@dataclass(frozen=True)
class ChaosResult:
    """Chaos readiness summary."""

    readiness_score: float
    scenarios: tuple[ScenarioResult, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scenarios"] = [item.to_dict() for item in self.scenarios]
        return payload


@dataclass(frozen=True)
class FaultInjectionResult:
    """Fault injection coverage summary."""

    coverage_score: float
    scenarios: tuple[ScenarioResult, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scenarios"] = [item.to_dict() for item in self.scenarios]
        return payload


@dataclass(frozen=True)
class DependencyAuditResult:
    """Offline dependency audit result."""

    dependency_health: str
    package_count: int
    pinned_count: int
    bounded_count: int
    conflict_count: int
    vulnerable_pattern_count: int
    findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SecurityAuditResult:
    """Security audit result."""

    security_score: float
    exposed_secret_count: int
    insecure_config_count: int
    unsafe_dependency_patterns: int
    weak_deployment_config_count: int
    findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfilingResult:
    """Performance profiling summary."""

    memory_usage_score: float
    cpu_usage_score: float
    slow_function_score: float
    io_bottleneck_score: float
    performance_score: float
    hotspots: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HardeningResult:
    """Hardening validation summary."""

    hardening_state: str
    production_config_ready: bool
    strict_runtime_config: bool
    secret_enforcement: bool
    deployment_integrity: bool
    findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ComplianceResult:
    """Compliance validation summary."""

    compliance_state: str
    deployment_policy_ok: bool
    runtime_policy_ok: bool
    release_integrity_ok: bool
    findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PackageMetadata:
    """Release package metadata."""

    package_id: str
    release_version: str
    bundle_name: str
    deployment_bundle: tuple[str, ...]
    archive_name: str
    ready: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactMetadata:
    """Release artifact metadata."""

    artifact_id: str
    path: str
    checksum: str
    signature: str
    artifact_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseNotesPayload:
    """Structured release notes payload."""

    title: str
    summary: str
    benchmark_summary: str
    security_summary: str
    deployment_summary: str
    known_limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseDiagnostics:
    """Release diagnostics payload."""

    release_latency_ms: float
    benchmark_diagnostics: tuple[str, ...] = ()
    stress_diagnostics: tuple[str, ...] = ()
    dependency_diagnostics: tuple[str, ...] = ()
    security_diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseCandidateEvaluation:
    """Deterministic release candidate evaluation."""

    release_id: str
    release_version: str
    benchmark_score: float
    load_test_score: float
    stress_test_score: float
    security_score: float
    dependency_health: str
    performance_score: float
    hardening_state: str
    compliance_state: str
    release_state: str
    timestamp: datetime
    schema_version: str = SCHEMA_VERSION
    environment: str = "prod"
    benchmark: BenchmarkResult = field(
        default_factory=lambda: BenchmarkResult(0.0, 0.0, 0.0, 0.0, 0.0)
    )
    load_test: LoadTestResult = field(
        default_factory=lambda: LoadTestResult(0, 0, 0, 0, 0.0)
    )
    stress_test: StressTestResult = field(
        default_factory=lambda: StressTestResult(0.0, 0.0, 0.0, 0.0, 0.0)
    )
    chaos: ChaosResult = field(default_factory=lambda: ChaosResult(0.0, ()))
    fault_injection: FaultInjectionResult = field(
        default_factory=lambda: FaultInjectionResult(0.0, ())
    )
    dependencies: DependencyAuditResult = field(
        default_factory=lambda: DependencyAuditResult("failed", 0, 0, 0, 0, 0)
    )
    security_audit: SecurityAuditResult = field(
        default_factory=lambda: SecurityAuditResult(0.0, 0, 0, 0, 0)
    )
    profiling: ProfilingResult = field(
        default_factory=lambda: ProfilingResult(0.0, 0.0, 0.0, 0.0, 0.0)
    )
    hardening: HardeningResult = field(
        default_factory=lambda: HardeningResult("failed", False, False, False, False)
    )
    compliance: ComplianceResult = field(
        default_factory=lambda: ComplianceResult("failed", False, False, False)
    )
    package_metadata: PackageMetadata = field(
        default_factory=lambda: PackageMetadata("", "", "", (), "", False)
    )
    artifacts: tuple[ArtifactMetadata, ...] = field(default_factory=tuple)
    release_notes: ReleaseNotesPayload = field(
        default_factory=lambda: ReleaseNotesPayload("", "", "", "", "")
    )
    diagnostics: ReleaseDiagnostics = field(
        default_factory=lambda: ReleaseDiagnostics(0.0)
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        payload["benchmark"] = self.benchmark.to_dict()
        payload["load_test"] = self.load_test.to_dict()
        payload["stress_test"] = self.stress_test.to_dict()
        payload["chaos"] = self.chaos.to_dict()
        payload["fault_injection"] = self.fault_injection.to_dict()
        payload["dependencies"] = self.dependencies.to_dict()
        payload["security_audit"] = self.security_audit.to_dict()
        payload["profiling"] = self.profiling.to_dict()
        payload["hardening"] = self.hardening.to_dict()
        payload["compliance"] = self.compliance.to_dict()
        payload["package_metadata"] = self.package_metadata.to_dict()
        payload["artifacts"] = [item.to_dict() for item in self.artifacts]
        payload["release_notes"] = self.release_notes.to_dict()
        payload["diagnostics"] = self.diagnostics.to_dict()
        return payload
