"""Typed API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from nsddos.runtime.models import SCHEMA_VERSION


class ApiEvidenceRef(BaseModel):
    """Stable evidence reference."""

    kind: str
    reference: str
    detail: str = ""


class ApiPagination(BaseModel):
    """Replay-safe pagination."""

    limit: int = Field(default=25, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ApiFilter(BaseModel):
    """Typed runtime query filter."""

    field: str
    value: Any
    operator: str = "contains"


class ApiQueryRequest(BaseModel):
    """Runtime query request."""

    name: str
    scope: str
    filters: list[ApiFilter] = Field(default_factory=list)
    pagination: ApiPagination = Field(default_factory=ApiPagination)
    replay_safe: bool = True
    schema_version: str = SCHEMA_VERSION


class ApiQueryResponse(BaseModel):
    """Runtime query response."""

    schema_version: str = SCHEMA_VERSION
    request_id: str
    query: dict[str, Any]
    items: list[dict[str, Any]]
    total: int
    evidence: list[ApiEvidenceRef]
    plan: dict[str, Any]
    cache: dict[str, Any]
    performance: dict[str, float]
    freshness: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float
    replay_safe: bool = True
    timestamp: str


class ApiExplainResponse(BaseModel):
    """Explainability response."""

    schema_version: str = SCHEMA_VERSION
    subject: str
    detail: dict[str, Any]
    evidence: list[ApiEvidenceRef] = Field(default_factory=list)
    replay_safe: bool = True


class ApiHealthResponse(BaseModel):
    """API health response."""

    schema_version: str = SCHEMA_VERSION
    status: str
    checks: dict[str, bool]
    evidence: list[ApiEvidenceRef] = Field(default_factory=list)


class ApiRouteInfo(BaseModel):
    """Registered API route."""

    path: str
    methods: list[str]
    name: str
    readonly: bool = True
    query_backed: bool = True


class ApiRouteSummary(BaseModel):
    """API route summary."""

    schema_version: str = SCHEMA_VERSION
    routes: list[ApiRouteInfo]
    endpoint_count: int


class DetectionResponse(BaseModel):
    """Typed detection response."""

    schema_version: str = SCHEMA_VERSION
    attack_detected: bool
    attack_type: str
    confidence: float
    risk_level: str
    evidence_hash: str
    classification_generation: str


class MitigationResponse(BaseModel):
    """Typed mitigation response."""

    schema_version: str = SCHEMA_VERSION
    mitigation_required: bool
    mitigation_action: str
    target_ip: str
    execution_result: str
    mitigation_hash: str
    mitigation_generation: str


class LiveTelemetryResponse(BaseModel):
    """Typed live telemetry response."""

    schema_version: str = SCHEMA_VERSION
    provider_source: str
    packet_rate: float
    byte_rate: float
    active_flows: int
    health_state: str
    controller_status: str
    timestamp: str


class SimulationResponse(BaseModel):
    """Typed simulation response."""

    schema_version: str = SCHEMA_VERSION
    attack_type: str
    target_ip: str
    packet_rate: float
    byte_rate: float
    duration_seconds: int
    intensity_level: str
    timestamp: str


class StreamingResponse(BaseModel):
    """Typed streaming response."""

    schema_version: str = SCHEMA_VERSION
    session_id: str
    active_events: int
    queue_depth: int
    dropped_events: int
    throughput: float
    stream_state: str
    timestamp: str


class PolicyResponse(BaseModel):
    """Typed policy response."""

    schema_version: str = SCHEMA_VERSION
    policy_id: str
    recommended_action: str
    escalation_level: int
    threshold_score: float
    attack_frequency: int
    timestamp: str


class MLDetectionResponse(BaseModel):
    """Typed ML detection response."""

    schema_version: str = SCHEMA_VERSION
    attack_probability: float
    predicted_attack_type: str
    confidence_score: float
    anomaly_score: float
    drift_score: float
    model_version: str
    retraining_required: bool


class DeploymentResponse(BaseModel):
    """Typed deployment response."""

    schema_version: str = SCHEMA_VERSION
    deployment_id: str
    environment: str
    container_count: int
    service_health: str
    deployment_state: str
    rollback_available: bool


class DistributedResponse(BaseModel):
    """Typed distributed response."""

    schema_version: str = SCHEMA_VERSION
    cluster_id: str
    active_nodes: int
    leader_node: str
    worker_count: int
    replication_factor: int
    partition_count: int
    cluster_health: str
    failover_available: bool
    checkpoint_state: str
    timestamp: str


class DashboardResponse(BaseModel):
    """Typed dashboard response."""

    schema_version: str = SCHEMA_VERSION
    dashboard_id: str
    active_attacks: int
    active_alerts: int
    stream_throughput: float
    cluster_nodes: int
    ml_confidence: float
    mitigation_events: int
    policy_events: int
    dashboard_health: str
    timestamp: str


class ReleaseResponse(BaseModel):
    """Typed release response."""

    schema_version: str = SCHEMA_VERSION
    release_version: str
    benchmark_score: float
    load_test_score: float
    stress_test_score: float
    security_score: float
    release_state: str
