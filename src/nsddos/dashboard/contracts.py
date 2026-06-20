"""Typed deterministic dashboard contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from nsddos.runtime.models import SCHEMA_VERSION

ALERT_LEVELS = {"info", "warning", "critical"}
DASHBOARD_HEALTH_STATES = {"healthy", "degraded", "failed"}


@dataclass(frozen=True)
class TimelineEvent:
    """Chronological dashboard event."""

    event_id: str
    event_type: str
    severity: str
    detail: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AlertRecord:
    """Dashboard alert record."""

    alert_id: str
    level: str
    alert_type: str
    message: str
    source: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MetricsState:
    """Aggregated metrics state."""

    packet_throughput: float
    byte_throughput: float
    attack_frequency: int
    detection_frequency: int
    mitigation_frequency: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StreamState:
    """Aggregated stream state."""

    active_streams: int
    stream_latency_ms: float
    event_throughput: float
    queue_depth: int
    dropped_events: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AttackState:
    """Aggregated attack state."""

    active_attacks: int
    attack_types: tuple[tuple[str, int], ...]
    source_ips: tuple[tuple[str, int], ...]
    attack_severities: tuple[tuple[str, int], ...]
    attack_frequency_history: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["attack_types"] = [list(item) for item in self.attack_types]
        payload["source_ips"] = [list(item) for item in self.source_ips]
        payload["attack_severities"] = [list(item) for item in self.attack_severities]
        return payload


@dataclass(frozen=True)
class VisualizationSeries:
    """Structured chart payload."""

    chart_id: str
    title: str
    points: tuple[tuple[str, float], ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["points"] = [list(item) for item in self.points]
        return payload


@dataclass(frozen=True)
class PolicyAnalytics:
    """Policy analytics summary."""

    policy_events: int
    escalation_frequency: int
    rollback_frequency: int
    threshold_evolution: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MLMetricsState:
    """ML metrics summary."""

    ml_confidence: float
    drift_trend: tuple[float, ...]
    retraining_frequency: int
    anomaly_trend: tuple[float, ...]
    false_positive_trend: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThreatIntelState:
    """Threat intelligence summary."""

    repeated_attacker_ips: tuple[tuple[str, int], ...]
    recurrence_frequency: int
    high_risk_subnets: tuple[str, ...]
    suspicious_protocol_concentration: tuple[tuple[str, float], ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["repeated_attacker_ips"] = [list(item) for item in self.repeated_attacker_ips]
        payload["suspicious_protocol_concentration"] = [list(item) for item in self.suspicious_protocol_concentration]
        return payload


@dataclass(frozen=True)
class DashboardReport:
    """Structured report payload."""

    report_id: str
    report_type: str
    summary: str
    sections: tuple[tuple[str, str], ...]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sections"] = [list(item) for item in self.sections]
        return payload


@dataclass(frozen=True)
class DashboardDiagnostics:
    """Dashboard diagnostics summary."""

    dashboard_latency_ms: float
    visualization_errors: tuple[str, ...]
    stale_telemetry_warnings: tuple[str, ...]
    missing_data_warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DashboardSourceBundle:
    """Typed read-only source bundle."""

    detection: dict[str, Any]
    mitigation: dict[str, Any]
    policy: dict[str, Any]
    policy_history: tuple[dict[str, Any], ...]
    ml: dict[str, Any]
    distributed: dict[str, Any]
    deployment: dict[str, Any]
    streaming: dict[str, Any]
    verification: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class DashboardEvaluation:
    """Deterministic dashboard evaluation."""

    dashboard_id: str
    active_attacks: int
    active_alerts: int
    stream_throughput: float
    cluster_nodes: int
    ml_confidence: float
    mitigation_events: int
    policy_events: int
    dashboard_health: str
    timestamp: datetime
    schema_version: str = SCHEMA_VERSION
    environment: str = "ops"
    metrics: MetricsState = field(default_factory=lambda: MetricsState(0.0, 0.0, 0, 0, 0))
    streams: StreamState = field(default_factory=lambda: StreamState(0, 0.0, 0.0, 0, 0))
    attacks: AttackState = field(default_factory=lambda: AttackState(0, (), (), (), ()))
    timeline: tuple[TimelineEvent, ...] = field(default_factory=tuple)
    alerts: tuple[AlertRecord, ...] = field(default_factory=tuple)
    visualizations: tuple[VisualizationSeries, ...] = field(default_factory=tuple)
    policy_analytics: PolicyAnalytics = field(default_factory=lambda: PolicyAnalytics(0, 0, 0, ()))
    ml_metrics: MLMetricsState = field(default_factory=lambda: MLMetricsState(0.0, (), 0, (), ()))
    threat_intel: ThreatIntelState = field(default_factory=lambda: ThreatIntelState((), 0, (), ()))
    reports: tuple[DashboardReport, ...] = field(default_factory=tuple)
    diagnostics: DashboardDiagnostics = field(default_factory=lambda: DashboardDiagnostics(0.0, (), (), ()))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        payload["metrics"] = self.metrics.to_dict()
        payload["streams"] = self.streams.to_dict()
        payload["attacks"] = self.attacks.to_dict()
        payload["timeline"] = [item.to_dict() for item in self.timeline]
        payload["alerts"] = [item.to_dict() for item in self.alerts]
        payload["visualizations"] = [item.to_dict() for item in self.visualizations]
        payload["policy_analytics"] = self.policy_analytics.to_dict()
        payload["ml_metrics"] = self.ml_metrics.to_dict()
        payload["threat_intel"] = self.threat_intel.to_dict()
        payload["reports"] = [item.to_dict() for item in self.reports]
        payload["diagnostics"] = self.diagnostics.to_dict()
        return payload
