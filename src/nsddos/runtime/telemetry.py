"""Runtime observability aggregation."""

from __future__ import annotations

import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nsddos.config import ensure_runtime_directories, load_runtime_state
from nsddos.constants import APP_DIR, COMPOSE_FILE, CONFIG_PATH, SNAPSHOT_DIR
from nsddos.docker_manager import DockerManager
from nsddos.runtime.dependencies import dependency_validation
from nsddos.runtime.environment import validate_bootstrap
from nsddos.runtime.execution_graph import build_execution_graph
from nsddos.runtime.graph import build_runtime_graph
from nsddos.runtime.models import (
    RuntimeAggregationResult,
    SCHEMA_VERSION,
    TelemetryState,
    VerificationResult,
)
from nsddos.runtime.pipeline import build_execution_plan
from nsddos.runtime.collection_layer import collect_runtime_bundle
from nsddos.runtime.analysis_layer import aggregate_runtime
from nsddos.runtime.providers_registry import build_provider_registry, collect_provider_status_from_registry
from nsddos.runtime.replay import replay_execution_history
from nsddos.runtime.transitions import analyze_snapshot_transitions


def _socket_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check TCP reachability."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _stack_running() -> bool:
    """Return persisted runtime state flag."""
    return load_runtime_state().stack_running


def _result(name: str, status: str, detail: str, category: str) -> VerificationResult:
    """Short helper for verification results."""
    return VerificationResult(name=name, status=status, detail=detail, category=category)


def collect_provider_status(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Collect provider statuses."""
    return collect_provider_status_from_registry(build_provider_registry(config))


def build_telemetry_state(config: dict[str, Any]) -> TelemetryState:
    """Build normalized telemetry state."""
    return TelemetryState(**collect_runtime_bundle(config).telemetry_state)


def runtime_aggregation(config: dict[str, Any], persist_collection: bool = False) -> RuntimeAggregationResult:
    """Collect + analyze runtime without tuple aggregation."""
    collection = collect_runtime_bundle(config, persist=persist_collection)
    return aggregate_runtime(config, collection)


def verify_runtime(config: dict[str, Any]) -> list[VerificationResult]:
    """Execute authoritative runtime verification."""
    from nsddos.runtime.verification.engine import execute_runtime_verification

    return execute_runtime_verification(config)


def doctor_runtime(config: dict[str, Any], deep: bool = False) -> list[VerificationResult]:
    """Collect environment diagnostics."""
    aggregation = runtime_aggregation(config)
    collection = aggregation.collection
    analysis = aggregation.analysis
    provider_status = collection.provider_status
    flows = collection.flow_state
    topology = analysis.topology
    controller = collection.controller_state
    convergence = analysis.convergence
    profile = collection.profile
    capabilities = collection.capabilities
    environment = collection.environment
    reproducibility = collection.reproducibility
    freshness = collection.freshness_state
    temporal = analysis.temporal
    identity = analysis.identity
    openflow = analysis.openflow
    paths = analysis.paths
    reconciliation = analysis.reconciliation
    drift = analysis.drift
    confidence = analysis.confidence
    runtime_state = load_runtime_state()
    docker = DockerManager()
    checks = [
        _result("python", "pass", sys.version.split()[0], "env"),
        _result("config_path", "pass", str(CONFIG_PATH), "env"),
        _result("compose_path", "pass" if COMPOSE_FILE.exists() else "fail", str(COMPOSE_FILE), "env"),
        _result("runtime_home", "pass", str(APP_DIR), "env"),
        _result("docker_cli", "pass" if docker.is_docker_installed() else "fail", "docker CLI", "env"),
        _result("docker_daemon", "pass" if docker.is_daemon_running() else "warn", "docker daemon", "env"),
        _result("runtime_profile", "pass", profile.get("name", "unknown"), "env"),
        _result("runtime_environment", "pass" if environment.get("status") == "compatible" else "warn", environment.get("detail", ""), "env"),
        _result("reproducibility", "pass" if reproducibility.get("status") == "reproducible" else "warn", reproducibility.get("detail", ""), "env"),
        _result("dependency_graph", "pass" if dependency_validation().get("valid") else "fail", json.dumps(dependency_validation(), sort_keys=True), "pipeline"),
        _result("runtime_dirs", "pass", ", ".join(str(path) for path in ensure_runtime_directories()), "env"),
        _result(
            "runtime_state",
            "pass",
            json.dumps(
                {
                    "stack_running": runtime_state.stack_running,
                    "topology_state": runtime_state.topology_state,
                    "controller_connected": runtime_state.controller_connected,
                },
                sort_keys=True,
            ),
            "state",
        ),
    ]

    try:
        java = __import__("subprocess").run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
        java_detail = (java.stderr or java.stdout).splitlines()[0] if java.returncode == 0 else "java missing"
        checks.append(_result("java", "pass" if java.returncode == 0 else "fail", java_detail, "env"))
    except OSError:
        checks.append(_result("java", "fail", "java missing", "env"))

    for name, status in provider_status.items():
        checks.append(
            _result(
                f"{name}_provider",
                "pass" if status.get("ready") or status.get("installed") or status.get("artifact_exists") else "warn",
                json.dumps(status, sort_keys=True),
                "provider",
            )
        )

    checks.append(
        _result(
            "host_permissions",
            "pass" if provider_status["mininet"].get("passwordless_sudo") else "warn",
            "root or passwordless sudo needed for Mininet/OVS control",
            "permission",
        )
    )

    for port_name, port in {
        "floodlight_rest": config.get("lab", {}).get("floodlight_port", 8080),
        "controller": config.get("lab", {}).get("controller_port", 6653),
        "sflowrt": config.get("api_port", 8008),
        "sflow_udp": config.get("sflow_port", 6343),
    }.items():
        checks.append(
            _result(
                f"port_{port_name}",
                "pass" if _socket_reachable("127.0.0.1", int(port)) else "warn",
                f"127.0.0.1:{port}",
                "port",
            )
        )

    if deep:
        running = _stack_running()
        checks.extend(
            [
                _result(
                    "deep_flow_visibility",
                    "pass" if flows.get("telemetry_present") else ("warn" if not running else "fail"),
                    flows.get("detail", ""),
                    "deep",
                ),
                _result(
                    "deep_telemetry_freshness",
                    "stale" if freshness.get("stale") else "pass",
                    freshness.get("detail", ""),
                    "deep",
                ),
                _result(
                    "deep_topology_consistency",
                    "pass" if topology.get("consistent") else ("warn" if not running else "fail"),
                    topology.get("detail", ""),
                    "deep",
                ),
                _result(
                    "deep_bridge_interface_correlation",
                    "pass" if not topology.get("missing_in_sflow") else ("warn" if not running else "fail"),
                    f"missing_in_sflow={topology.get('missing_in_sflow', [])}",
                    "deep",
                ),
                _result(
                    "deep_provider_agreement",
                    "pass" if confidence.get("provider_agreement") == "aligned" else ("warn" if not running else "fail"),
                    json.dumps(confidence, sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_identity_consistency",
                    "pass" if not identity.get("conflicts") else ("warn" if not running else "fail"),
                    json.dumps(identity, sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_runtime_reconciliation",
                    "pass"
                    if not reconciliation.get("missing_entities") and not reconciliation.get("inconsistent_entities")
                    else ("warn" if not running else "fail"),
                    json.dumps(reconciliation, sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_runtime_drift",
                    "pass"
                    if all(item.get("severity") == "low" for item in drift)
                    else ("warn" if not running else "fail"),
                    json.dumps(drift, sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_openflow_reconciliation",
                    "pass"
                    if not openflow.get("missing_ports") and not openflow.get("duplicate_ports")
                    else ("warn" if not running else "fail"),
                    json.dumps(openflow, sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_path_validation",
                    "pass"
                    if not paths.get("missing_paths") and not paths.get("inconsistent_paths")
                    else ("warn" if not running else "fail"),
                    json.dumps(paths, sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_controller_normalization",
                    "pass" if controller.get("switches") or not running else ("warn" if not running else "fail"),
                    json.dumps(controller, sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_convergence_validation",
                    "pass"
                    if convergence.get("status") == "converged"
                    else ("warn" if not running else "fail"),
                    json.dumps(convergence, sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_capability_validation",
                    "pass" if environment.get("status") == "compatible" else "warn",
                    json.dumps(capabilities, sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_bootstrap_validation",
                    "pass" if validate_bootstrap(config).get("bootstrap_ready") else "warn",
                    json.dumps(validate_bootstrap(config), sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_stability_analysis",
                    "pass" if temporal.get("stability", {}).get("classification") == "stable" else ("warn" if not running else "fail"),
                    json.dumps(temporal.get("stability", {}), sort_keys=True),
                    "deep",
                ),
                _result(
                    "deep_transition_diagnostics",
                    "pass",
                    json.dumps(temporal.get("transitions", []), sort_keys=True),
                    "deep",
                ),
            ]
        )

    return checks


def build_runtime_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    """Build runtime snapshot payload."""
    runtime_state = load_runtime_state()
    aggregation = runtime_aggregation(config, persist_collection=True)
    collection = aggregation.collection
    analysis = aggregation.analysis
    verification = [result.to_dict() for result in verify_runtime(config)]
    graph = build_runtime_graph(config)
    active_preset = runtime_state.preset_state.get("active", "minimal-lab") if runtime_state.preset_state else "minimal-lab"
    execution_plan = build_execution_plan(config, preset=active_preset)
    execution_graph = build_execution_graph(config, preset=active_preset)
    execution_replay = replay_execution_history()
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "runtime_state": runtime_state.to_dict(),
        "collection_state": collection.to_dict(),
        "analysis_state": analysis.to_dict(),
        "aggregation_state": aggregation.to_dict(),
        "provider_status": collection.provider_status,
        "telemetry_state": collection.telemetry_state,
        "flow_state": collection.flow_state,
        "telemetry_freshness": collection.freshness_state,
        "controller_state": collection.controller_state,
        "controller_history": collection.controller_history,
        "runtime_profile": collection.profile,
        "capability_map": collection.capabilities,
        "environment_state": collection.environment,
        "reproducibility_state": collection.reproducibility,
        "execution_plan": execution_plan.to_dict(),
        "execution_graph": execution_graph,
        "execution_replay": execution_replay,
        "dependency_state": dependency_validation(),
        "convergence_state": analysis.convergence,
        "timeline_state": analysis.timeline,
        "transition_state": {"transitions": analysis.temporal.get("transitions", [])},
        "correlation_state": analysis.temporal.get("correlation", {}),
        "stability_state": analysis.temporal.get("stability", {}),
        "identity_map": analysis.identity,
        "interface_state": analysis.interfaces,
        "openflow_state": analysis.openflow,
        "path_state": analysis.paths,
        "topology_correlation": analysis.topology,
        "reconciliation_state": analysis.reconciliation,
        "drift_state": analysis.drift,
        "runtime_graph": graph,
        "confidence_summary": analysis.confidence,
        "verification": verification,
    }


def compare_snapshots(path_a: Path, path_b: Path) -> dict[str, Any]:
    """Compare two runtime snapshot files."""
    file_a = path_a
    file_b = path_b
    snapshot_a = json.loads(file_a.read_text(encoding="utf-8"))
    snapshot_b = json.loads(file_b.read_text(encoding="utf-8"))

    topology_a = snapshot_a.get("topology_correlation", {})
    topology_b = snapshot_b.get("topology_correlation", {})
    telemetry_a = snapshot_a.get("telemetry_state", {})
    telemetry_b = snapshot_b.get("telemetry_state", {})
    flow_a = snapshot_a.get("flow_state", {})
    flow_b = snapshot_b.get("flow_state", {})
    controller_a = snapshot_a.get("controller_state", {})
    controller_b = snapshot_b.get("controller_state", {})
    convergence_a = snapshot_a.get("convergence_state", {})
    convergence_b = snapshot_b.get("convergence_state", {})
    profile_a = snapshot_a.get("runtime_profile", {})
    profile_b = snapshot_b.get("runtime_profile", {})
    caps_a = snapshot_a.get("capability_map", {})
    caps_b = snapshot_b.get("capability_map", {})
    env_a = snapshot_a.get("environment_state", {})
    env_b = snapshot_b.get("environment_state", {})
    repro_a = snapshot_a.get("reproducibility_state", {})
    repro_b = snapshot_b.get("reproducibility_state", {})
    plan_a = snapshot_a.get("execution_plan", {})
    plan_b = snapshot_b.get("execution_plan", {})
    graph_a = snapshot_a.get("execution_graph", {})
    graph_b = snapshot_b.get("execution_graph", {})
    replay_a = snapshot_a.get("execution_replay", {})
    replay_b = snapshot_b.get("execution_replay", {})
    timeline_state_a = snapshot_a.get("timeline_state", {})
    timeline_state_b = snapshot_b.get("timeline_state", {})
    stability_a = snapshot_a.get("stability_state", {})
    stability_b = snapshot_b.get("stability_state", {})
    transition_a = snapshot_a.get("transition_state", {})
    transition_b = snapshot_b.get("transition_state", {})
    identity_a = snapshot_a.get("identity_map", {})
    identity_b = snapshot_b.get("identity_map", {})
    openflow_a = snapshot_a.get("openflow_state", {})
    openflow_b = snapshot_b.get("openflow_state", {})
    path_state_a = snapshot_a.get("path_state", {})
    path_state_b = snapshot_b.get("path_state", {})
    reconciliation_a = snapshot_a.get("reconciliation_state", {})
    reconciliation_b = snapshot_b.get("reconciliation_state", {})
    drift_a = snapshot_a.get("drift_state", {})
    drift_b = snapshot_b.get("drift_state", {})
    confidence_a = snapshot_a.get("confidence_summary", {})
    confidence_b = snapshot_b.get("confidence_summary", {})
    providers_a = snapshot_a.get("provider_status", {})
    providers_b = snapshot_b.get("provider_status", {})

    return {
        "snapshot_a": str(file_a),
        "snapshot_b": str(file_b),
        "topology_changed": topology_a != topology_b,
        "controller_drift": controller_a != controller_b,
        "convergence_drift": convergence_a != convergence_b,
        "profile_drift": profile_a != profile_b,
        "capability_drift": caps_a != caps_b,
        "environment_drift": env_a != env_b,
        "reproducibility_drift": repro_a != repro_b,
        "execution_plan_drift": plan_a != plan_b,
        "execution_graph_drift": graph_a != graph_b,
        "execution_replay_drift": replay_a != replay_b,
        "stability_drift": stability_a != stability_b,
        "timeline_drift": timeline_state_a != timeline_state_b,
        "identity_drift": identity_a != identity_b,
        "datapath_drift": openflow_a != openflow_b,
        "path_drift": path_state_a != path_state_b,
        "provider_drift": providers_a != providers_b,
        "telemetry_changed": telemetry_a != telemetry_b,
        "flow_visibility_changed": flow_a != flow_b,
        "reconciliation_changed": reconciliation_a != reconciliation_b,
        "drift_changed": _normalize_drift(drift_a) != _normalize_drift(drift_b),
        "confidence_changed": confidence_a != confidence_b,
        "transition_summary": analyze_snapshot_transitions(snapshot_a, snapshot_b),
        "topology_a": topology_a,
        "topology_b": topology_b,
        "telemetry_a": telemetry_a,
        "telemetry_b": telemetry_b,
        "flow_a": flow_a,
        "flow_b": flow_b,
        "identity_a": identity_a,
        "identity_b": identity_b,
        "controller_a": controller_a,
        "controller_b": controller_b,
        "profile_a": profile_a,
        "profile_b": profile_b,
        "capability_a": caps_a,
        "capability_b": caps_b,
        "environment_a": env_a,
        "environment_b": env_b,
        "reproducibility_a": repro_a,
        "reproducibility_b": repro_b,
        "execution_plan_a": plan_a,
        "execution_plan_b": plan_b,
        "execution_graph_a": graph_a,
        "execution_graph_b": graph_b,
        "execution_replay_a": replay_a,
        "execution_replay_b": replay_b,
        "timeline_state_a": timeline_state_a,
        "timeline_state_b": timeline_state_b,
        "stability_a": stability_a,
        "stability_b": stability_b,
        "transition_a": transition_a,
        "transition_b": transition_b,
        "convergence_a": convergence_a,
        "convergence_b": convergence_b,
        "openflow_a": openflow_a,
        "openflow_b": openflow_b,
        "path_a": path_state_a,
        "path_b": path_state_b,
    }


def _normalize_drift(payload: Any) -> Any:
    """Drop per-snapshot drift timestamps for stable comparisons."""
    if not isinstance(payload, list):
        return payload
    normalized = []
    for item in payload:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        normalized.append(
            {
                "category": item.get("category"),
                "severity": item.get("severity"),
                "detail": item.get("detail"),
            }
        )
    return normalized


def snapshot_file_path() -> Path:
    """Return snapshot output path."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return SNAPSHOT_DIR / f"snapshot-{timestamp}.json"
