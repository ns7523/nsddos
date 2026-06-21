"""Typed runtime state models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0"


@dataclass
class ServiceState:
    """Runtime state for one managed service."""

    name: str
    status: str = "unknown"
    healthy: bool = False
    container_id: str | None = None
    provider: str = "docker"
    endpoint: str | None = None
    detail: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServiceState":
        """Build service state from dict."""
        return cls(
            name=data.get("name", ""),
            status=data.get("status", "unknown"),
            healthy=bool(data.get("healthy", False)),
            container_id=data.get("container_id"),
            provider=data.get("provider", "docker"),
            endpoint=data.get("endpoint"),
            detail=data.get("detail", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize state."""
        return asdict(self)


@dataclass
class RuntimeState:
    """Persisted runtime state."""

    schema_version: str = SCHEMA_VERSION
    stack_running: bool = False
    started_at: str | None = None
    updated_at: str | None = None
    stopped_at: str | None = None
    services: list[ServiceState] = field(default_factory=list)
    provider_status: dict[str, dict[str, Any]] = field(default_factory=dict)
    topology_state: str = "stopped"
    topology_pid: int | None = None
    topology_metadata: dict[str, Any] = field(default_factory=dict)
    ovs_state: dict[str, Any] = field(default_factory=dict)
    telemetry_state: dict[str, Any] = field(default_factory=dict)
    flow_state: dict[str, Any] = field(default_factory=dict)
    identity_map: dict[str, Any] = field(default_factory=dict)
    interface_state: dict[str, Any] = field(default_factory=dict)
    openflow_state: dict[str, Any] = field(default_factory=dict)
    path_state: dict[str, Any] = field(default_factory=dict)
    controller_state: dict[str, Any] = field(default_factory=dict)
    runtime_profile: dict[str, Any] = field(default_factory=dict)
    capability_map: dict[str, Any] = field(default_factory=dict)
    environment_state: dict[str, Any] = field(default_factory=dict)
    reproducibility_state: dict[str, Any] = field(default_factory=dict)
    preset_state: dict[str, Any] = field(default_factory=dict)
    convergence_state: dict[str, Any] = field(default_factory=dict)
    timeline_state: dict[str, Any] = field(default_factory=dict)
    transition_state: dict[str, Any] = field(default_factory=dict)
    correlation_state: dict[str, Any] = field(default_factory=dict)
    stability_state: dict[str, Any] = field(default_factory=dict)
    topology_correlation: dict[str, Any] = field(default_factory=dict)
    reconciliation_state: dict[str, Any] = field(default_factory=dict)
    drift_state: dict[str, Any] = field(default_factory=dict)
    confidence_summary: dict[str, Any] = field(default_factory=dict)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    controller_connected: bool = False
    last_error: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeState":
        """Build runtime state from dict."""
        services = [ServiceState.from_dict(item) for item in data.get("services", [])]
        return cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            stack_running=bool(data.get("stack_running", False)),
            started_at=data.get("started_at"),
            updated_at=data.get("updated_at"),
            stopped_at=data.get("stopped_at"),
            services=services,
            provider_status=data.get("provider_status", {}),
            topology_state=data.get("topology_state", "stopped"),
            topology_pid=data.get("topology_pid"),
            topology_metadata=data.get("topology_metadata", {}),
            ovs_state=data.get("ovs_state", {}),
            telemetry_state=data.get("telemetry_state", {}),
            flow_state=data.get("flow_state", {}),
            identity_map=data.get("identity_map", {}),
            interface_state=data.get("interface_state", {}),
            openflow_state=data.get("openflow_state", {}),
            path_state=data.get("path_state", {}),
            controller_state=data.get("controller_state", {}),
            runtime_profile=data.get("runtime_profile", {}),
            capability_map=data.get("capability_map", {}),
            environment_state=data.get("environment_state", {}),
            reproducibility_state=data.get("reproducibility_state", {}),
            preset_state=data.get("preset_state", {}),
            convergence_state=data.get("convergence_state", {}),
            timeline_state=data.get("timeline_state", {}),
            transition_state=data.get("transition_state", {}),
            correlation_state=data.get("correlation_state", {}),
            stability_state=data.get("stability_state", {}),
            topology_correlation=data.get("topology_correlation", {}),
            reconciliation_state=data.get("reconciliation_state", {}),
            drift_state=data.get("drift_state", {}),
            confidence_summary=data.get("confidence_summary", {}),
            verification_results=data.get("verification_results", []),
            controller_connected=bool(data.get("controller_connected", False)),
            last_error=data.get("last_error"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize state."""
        payload = asdict(self)
        payload["services"] = [service.to_dict() for service in self.services]
        return payload


@dataclass
class HealthResult:
    """One health check result."""

    name: str
    ok: bool
    detail: str
    category: str


@dataclass
class VerificationResult:
    """Verification or diagnostic result."""

    name: str
    status: str
    detail: str
    category: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize verification result."""
        return asdict(self)


@dataclass
class OVSBridgeState:
    """OVS bridge metadata."""

    name: str
    interfaces: list[str] = field(default_factory=list)
    controller_connected: bool = False
    sflow_attached: bool = False
    protocols: list[str] = field(default_factory=list)
    forwarding_programmed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize bridge state."""
        return asdict(self)


@dataclass
class OVSState:
    """Open vSwitch runtime state."""

    installed: bool = False
    service_running: bool = False
    bridges: list[OVSBridgeState] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize OVS state."""
        payload = asdict(self)
        payload["bridges"] = [bridge.to_dict() for bridge in self.bridges]
        return payload


@dataclass
class TopologyMetadata:
    """Mininet topology metadata."""

    topology: str = "single,3"
    switches: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    controller: str = ""
    controller_reachable: bool = False
    switch_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize topology metadata."""
        return asdict(self)


@dataclass
class TelemetryState:
    """Telemetry visibility state."""

    collector_reachable: bool = False
    flow_api_ready: bool = False
    metrics_available: bool = False
    topology_published: bool = False
    active_flow_count: int | None = None
    last_flow_timestamp: str | None = None
    update_interval_seconds: float | None = None
    stale: bool = False
    visible_interfaces: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize telemetry state."""
        return asdict(self)


@dataclass
class FlowState:
    """Normalized flow visibility summary."""

    collector_reachable: bool = False
    telemetry_present: bool = False
    flow_count: int = 0
    switches_visible: list[str] = field(default_factory=list)
    interfaces_visible: list[str] = field(default_factory=list)
    metrics_changed: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize flow state."""
        return asdict(self)


@dataclass
class TelemetryFreshness:
    """Telemetry freshness summary."""

    last_flow_timestamp: str | None = None
    sample_interval_seconds: float | None = None
    stale: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize freshness."""
        return asdict(self)


@dataclass
class TopologyCorrelation:
    """Correlated topology view across providers."""

    expected_switches: list[str] = field(default_factory=list)
    expected_hosts: list[str] = field(default_factory=list)
    controller_switches: list[str] = field(default_factory=list)
    ovs_bridges: list[str] = field(default_factory=list)
    ovs_interfaces: list[str] = field(default_factory=list)
    sflow_interfaces: list[str] = field(default_factory=list)
    missing_in_controller: list[str] = field(default_factory=list)
    missing_in_ovs: list[str] = field(default_factory=list)
    missing_in_sflow: list[str] = field(default_factory=list)
    normalized_switches: list[str] = field(default_factory=list)
    provider_agreement: list[str] = field(default_factory=list)
    graph_links: list[str] = field(default_factory=list)
    consistent: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize topology correlation."""
        return asdict(self)


@dataclass
class EvidenceBundle:
    """Evidence bundle metadata."""

    timestamp: str
    bundle_dir: str
    snapshot_file: str
    summary_file: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize evidence bundle."""
        return asdict(self)


@dataclass
class RuntimeCollectionBundle:
    """Collected runtime/provider state only."""

    schema_version: str = SCHEMA_VERSION
    provider_status: dict[str, dict[str, Any]] = field(default_factory=dict)
    flow_state: dict[str, Any] = field(default_factory=dict)
    freshness_state: dict[str, Any] = field(default_factory=dict)
    telemetry_state: dict[str, Any] = field(default_factory=dict)
    controller_state: dict[str, Any] = field(default_factory=dict)
    controller_history: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    reproducibility: dict[str, Any] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    cache: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize collection bundle."""
        return asdict(self)


@dataclass
class RuntimeAnalysisBundle:
    """Derived runtime analysis state."""

    schema_version: str = SCHEMA_VERSION
    topology: dict[str, Any] = field(default_factory=dict)
    identity: dict[str, Any] = field(default_factory=dict)
    interfaces: dict[str, Any] = field(default_factory=dict)
    openflow: dict[str, Any] = field(default_factory=dict)
    paths: dict[str, Any] = field(default_factory=dict)
    reconciliation: dict[str, Any] = field(default_factory=dict)
    convergence: dict[str, Any] = field(default_factory=dict)
    drift: list[dict[str, Any]] = field(default_factory=list)
    timeline: dict[str, Any] = field(default_factory=dict)
    temporal: dict[str, Any] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, Any] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize analysis bundle."""
        return asdict(self)


@dataclass
class RuntimeAggregationResult:
    """Combined collection + analysis result."""

    schema_version: str = SCHEMA_VERSION
    collection: RuntimeCollectionBundle = field(default_factory=RuntimeCollectionBundle)
    analysis: RuntimeAnalysisBundle = field(default_factory=RuntimeAnalysisBundle)
    performance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize aggregation result."""
        payload = asdict(self)
        payload["collection"] = self.collection.to_dict()
        payload["analysis"] = self.analysis.to_dict()
        return payload


@dataclass
class RuntimeTimelineEvent:
    """Ordered runtime event."""

    timestamp: str
    event_type: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize timeline event."""
        return asdict(self)


@dataclass
class IdentityRecord:
    """Canonical runtime identity for one switch-like entity."""

    canonical_id: str
    mininet_name: str | None = None
    ovs_bridge: str | None = None
    controller_dpid: str | None = None
    sflow_agent: str | None = None
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize identity record."""
        return asdict(self)


@dataclass
class IdentityMap:
    """Normalized identity mapping across providers."""

    switches: list[IdentityRecord] = field(default_factory=list)
    controller_endpoint: str | None = None
    provider_aliases: dict[str, list[str]] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)
    stability: str = "unknown"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize identity map."""
        payload = asdict(self)
        payload["switches"] = [item.to_dict() for item in self.switches]
        return payload


@dataclass
class InterfaceRecord:
    """Normalized interface visibility state."""

    canonical_id: str
    switch_id: str | None = None
    ovs_name: str | None = None
    mininet_link: str | None = None
    sflow_name: str | None = None
    controller_port: str | None = None
    visible_in_ovs: bool = False
    visible_in_sflow: bool = False
    visible_in_controller: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize interface record."""
        return asdict(self)


@dataclass
class InterfaceCorrelation:
    """Correlated interface state across providers."""

    interfaces: list[InterfaceRecord] = field(default_factory=list)
    missing_interfaces: list[str] = field(default_factory=list)
    orphan_interfaces: list[str] = field(default_factory=list)
    duplicate_mappings: list[str] = field(default_factory=list)
    stability: str = "unknown"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize interface correlation."""
        payload = asdict(self)
        payload["interfaces"] = [item.to_dict() for item in self.interfaces]
        return payload


@dataclass
class OpenFlowPortRecord:
    """Canonical OpenFlow port mapping."""

    canonical_id: str
    switch_id: str
    datapath_id: str | None = None
    port_no: str | None = None
    controller_name: str | None = None
    ovs_name: str | None = None
    mininet_interface: str | None = None
    sflow_name: str | None = None
    visible_in_controller: bool = False
    visible_in_ovs: bool = False
    visible_in_sflow: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize OpenFlow port record."""
        return asdict(self)


@dataclass
class OpenFlowCorrelation:
    """Correlated datapath port state."""

    ports: list[OpenFlowPortRecord] = field(default_factory=list)
    missing_ports: list[str] = field(default_factory=list)
    stale_ports: list[str] = field(default_factory=list)
    orphan_ports: list[str] = field(default_factory=list)
    duplicate_ports: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize OpenFlow correlation."""
        payload = asdict(self)
        payload["ports"] = [item.to_dict() for item in self.ports]
        return payload


@dataclass
class PathRecord:
    """Correlated runtime path."""

    canonical_id: str
    source_id: str
    target_id: str
    interface_id: str | None = None
    port_id: str | None = None
    visible_in_topology: bool = False
    visible_in_controller: bool = False
    visible_in_telemetry: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize path record."""
        return asdict(self)


@dataclass
class PathCorrelation:
    """Observed and expected runtime path state."""

    observed_paths: list[PathRecord] = field(default_factory=list)
    missing_paths: list[str] = field(default_factory=list)
    orphan_paths: list[str] = field(default_factory=list)
    inconsistent_paths: list[str] = field(default_factory=list)
    stability: str = "unknown"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize path correlation."""
        payload = asdict(self)
        payload["observed_paths"] = [item.to_dict() for item in self.observed_paths]
        return payload


@dataclass
class ReconciliationState:
    """Runtime truth reconciliation summary."""

    missing_entities: list[str] = field(default_factory=list)
    stale_entities: list[str] = field(default_factory=list)
    inconsistent_entities: list[str] = field(default_factory=list)
    orphan_entities: list[str] = field(default_factory=list)
    confidence_reductions: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize reconciliation state."""
        return asdict(self)


@dataclass
class DriftRecord:
    """Runtime drift summary."""

    category: str
    severity: str
    detail: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize drift record."""
        return asdict(self)


@dataclass
class GraphArtifact:
    """Runtime graph export paths."""

    json_path: str
    mermaid_path: str
    dot_path: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph artifact."""
        return asdict(self)


@dataclass
class TimelineEvent:
    """Deterministic runtime timeline event."""

    timestamp: str
    event_type: str
    affected_entities: list[str] = field(default_factory=list)
    convergence_impact: str = "none"
    drift_impact: str = "none"
    topology_impact: str = "none"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize timeline event."""
        return asdict(self)


@dataclass
class RuntimeTransition:
    """Generic runtime transition."""

    transition_type: str
    from_state: str
    to_state: str
    affected_entities: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize runtime transition."""
        return asdict(self)


@dataclass
class ConvergenceTransition:
    """Convergence state transition."""

    timestamp: str
    from_state: str
    to_state: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize convergence transition."""
        return asdict(self)


@dataclass
class DriftTransition:
    """Drift evolution transition."""

    timestamp: str
    introduced: list[str] = field(default_factory=list)
    recovered: list[str] = field(default_factory=list)
    recurring: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize drift transition."""
        return asdict(self)


@dataclass
class TopologyTransition:
    """Topology evolution transition."""

    timestamp: str
    changed: bool = False
    added_links: list[str] = field(default_factory=list)
    removed_links: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize topology transition."""
        return asdict(self)


@dataclass
class DatapathTransition:
    """Datapath evolution transition."""

    timestamp: str
    added_ports: list[str] = field(default_factory=list)
    removed_ports: list[str] = field(default_factory=list)
    changed_dpids: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize datapath transition."""
        return asdict(self)


@dataclass
class RuntimeProfile:
    """Canonical runtime profile definition."""

    name: str
    platform: str
    description: str
    required_services: list[str] = field(default_factory=list)
    supported_capabilities: list[str] = field(default_factory=list)
    runtime_limitations: list[str] = field(default_factory=list)
    verification_expectations: list[str] = field(default_factory=list)
    provider_availability: dict[str, str] = field(default_factory=dict)
    privilege_requirements: list[str] = field(default_factory=list)
    detected: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize runtime profile."""
        return asdict(self)


@dataclass
class CapabilityMap:
    """Detected runtime capabilities."""

    platform: str
    kernel: str
    docker_installed: bool = False
    docker_daemon: bool = False
    ovs_installed: bool = False
    ovs_service: bool = False
    mininet_supported: bool = False
    linux_kernel: bool = False
    sudo_available: bool = False
    passwordless_sudo: bool = False
    wsl2: bool = False
    container_networking: bool = False
    openflow_compatible: bool = False
    sflow_capable: bool = False
    java_available: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize capability map."""
        return asdict(self)


@dataclass
class EnvironmentCompatibility:
    """Deterministic environment compatibility result."""

    profile: str
    status: str
    supported: list[str] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    provider_support: dict[str, str] = field(default_factory=dict)
    missing_dependencies: list[str] = field(default_factory=list)
    reproducibility_limitations: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize environment compatibility."""
        return asdict(self)


@dataclass
class ReproducibilityAssessment:
    """Deterministic reproducibility assessment."""

    status: str
    deterministic_inputs: list[str] = field(default_factory=list)
    portability_limits: list[str] = field(default_factory=list)
    provider_reproducibility: dict[str, str] = field(default_factory=dict)
    snapshot_portable: bool = False
    profile_stable: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize reproducibility assessment."""
        return asdict(self)


@dataclass
class ControllerPort:
    """Normalized controller-visible port."""

    port_no: str | None = None
    name: str | None = None
    state: str | None = None
    hardware_address: str | None = None
    config: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize controller port."""
        return asdict(self)


@dataclass
class ControllerSwitch:
    """Normalized controller-visible switch."""

    canonical_id: str
    datapath_id: str | None = None
    connected: bool = False
    inet_address: str | None = None
    ports: list[ControllerPort] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize controller switch."""
        payload = asdict(self)
        payload["ports"] = [item.to_dict() for item in self.ports]
        return payload


@dataclass
class DatapathRelationship:
    """Controller-visible datapath relationship."""

    source_dpid: str | None = None
    source_port: str | None = None
    target_dpid: str | None = None
    target_port: str | None = None
    relationship_type: str = "link"

    def to_dict(self) -> dict[str, Any]:
        """Serialize relationship."""
        return asdict(self)


@dataclass
class ControllerPathVisibility:
    """Controller-visible path state."""

    canonical_id: str
    source_dpid: str | None = None
    target_dpid: str | None = None
    visible: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize path visibility."""
        return asdict(self)


@dataclass
class ControllerTopology:
    """Normalized controller topology."""

    switches: list[ControllerSwitch] = field(default_factory=list)
    links: list[DatapathRelationship] = field(default_factory=list)
    visible_paths: list[ControllerPathVisibility] = field(default_factory=list)
    stale_entities: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize controller topology."""
        payload = asdict(self)
        payload["switches"] = [item.to_dict() for item in self.switches]
        payload["links"] = [item.to_dict() for item in self.links]
        payload["visible_paths"] = [item.to_dict() for item in self.visible_paths]
        return payload


@dataclass
class ConvergenceState:
    """Deterministic runtime convergence state."""

    status: str = "diverged"
    topology_agreement: bool = False
    datapath_agreement: bool = False
    controller_agreement: bool = False
    telemetry_agreement: bool = False
    divergence_reasons: list[str] = field(default_factory=list)
    stale_entities: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize convergence state."""
        return asdict(self)


@dataclass
class RuntimeDependency:
    """Runtime phase dependency edge."""

    source: str
    target: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize dependency."""
        return asdict(self)


@dataclass
class RuntimePhase:
    """Canonical runtime pipeline phase."""

    name: str
    dependencies: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    gate: str = ""
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize phase."""
        return asdict(self)


@dataclass
class RuntimePhaseResult:
    """Execution result for one pipeline phase."""

    phase: str
    status: str
    detail: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize phase result."""
        return asdict(self)


@dataclass
class RuntimeExecutionPlan:
    """Canonical runtime execution plan."""

    name: str
    phases: list[RuntimePhase] = field(default_factory=list)
    dependencies: list[RuntimeDependency] = field(default_factory=list)
    preset: str = "minimal-lab"
    profile: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Serialize execution plan."""
        payload = asdict(self)
        payload["phases"] = [item.to_dict() for item in self.phases]
        payload["dependencies"] = [item.to_dict() for item in self.dependencies]
        return payload


@dataclass
class RuntimeExecutionState:
    """Runtime pipeline execution state."""

    plan: str
    status: str = "pending"
    current_phase: str | None = None
    results: list[RuntimePhaseResult] = field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    preset: str = "minimal-lab"
    profile: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Serialize execution state."""
        payload = asdict(self)
        payload["results"] = [item.to_dict() for item in self.results]
        return payload


@dataclass
class RuntimePipelineSnapshot:
    """Persisted runtime pipeline snapshot."""

    timestamp: str
    schema_version: str = SCHEMA_VERSION
    plan: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    execution_graph: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize pipeline snapshot."""
        return asdict(self)
