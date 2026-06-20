"""Runtime drift detection."""

from __future__ import annotations

from datetime import datetime, timezone
import json

from nsddos.constants import SNAPSHOT_DIR
from nsddos.runtime.controller import normalize_controller_topology
from nsddos.runtime.convergence import validate_convergence
from nsddos.runtime.models import DriftRecord
from nsddos.runtime.openflow import correlate_openflow_ports
from nsddos.runtime.paths import correlate_paths
from nsddos.runtime.reconcile import reconcile_runtime
from nsddos.runtime.transitions import list_snapshots, load_transition_history
from nsddos.runtime.verification.replay import replay_verification_runs


def detect_runtime_drift(config: dict) -> list[DriftRecord]:
    """Detect runtime drift from reconciliation state."""
    reconciliation = reconcile_runtime(config)
    controller = normalize_controller_topology(config)
    convergence = validate_convergence(config)
    openflow = correlate_openflow_ports(config)
    paths = correlate_paths(config)
    transitions = load_transition_history()
    timestamp = datetime.now(timezone.utc).isoformat()
    drift: list[DriftRecord] = []

    for item in reconciliation.missing_entities:
        drift.append(DriftRecord("topology_drift", "high", item, timestamp))
    for item in reconciliation.stale_entities:
        drift.append(DriftRecord("telemetry_drift", "medium", item, timestamp))
    for item in reconciliation.orphan_entities:
        drift.append(DriftRecord("orphan_entity", "medium", item, timestamp))
    for item in reconciliation.inconsistent_entities:
        drift.append(DriftRecord("provider_disagreement", "high", item, timestamp))
    for item in openflow.orphan_ports:
        drift.append(DriftRecord("orphan_openflow_port", "high", item, timestamp))
    for item in openflow.stale_ports:
        drift.append(DriftRecord("stale_datapath_mapping", "medium", item, timestamp))
    for item in paths.inconsistent_paths:
        drift.append(DriftRecord("telemetry_path_divergence", "high", item, timestamp))
    for item in paths.missing_paths:
        drift.append(DriftRecord("missing_runtime_path", "medium", item, timestamp))
    for item in controller.stale_entities:
        drift.append(DriftRecord("controller_stale_entity", "high", item, timestamp))
    for item in convergence.divergence_reasons:
        drift.append(DriftRecord("controller_convergence", "high", item, timestamp))
    recurring = {}
    for item in transitions:
        for entry in item.get("drift", {}).get("recurring", []):
            recurring[str(entry)] = recurring.get(str(entry), 0) + 1
    for key, count in recurring.items():
        if count > 1:
            drift.append(DriftRecord("recurring_drift", "high", f"{key}:{count}", timestamp))
    verification_replay = replay_verification_runs()
    for name, count in verification_replay.get("repeated_failures", {}).items():
        if count > 1:
            drift.append(DriftRecord("verification_instability", "high", f"{name}:{count}", timestamp))
    for transition in verification_replay.get("transitions", []):
        if transition.get("from") != transition.get("to"):
            drift.append(
                DriftRecord(
                    "validation_severity_drift",
                    "medium",
                    f"{transition.get('from')}->{transition.get('to')}",
                    timestamp,
                )
            )

    snapshots = list_snapshots(SNAPSHOT_DIR)
    if len(snapshots) >= 2:
        previous = json.loads(snapshots[-2].read_text(encoding="utf-8"))
        current = json.loads(snapshots[-1].read_text(encoding="utf-8"))
        for field, category, severity in (
            ("capability_map", "environment_capability_drift", "high"),
            ("environment_state", "environment_compatibility_drift", "high"),
            ("runtime_profile", "runtime_profile_drift", "medium"),
            ("execution_plan", "phase_ordering_drift", "high"),
            ("execution_graph", "dependency_drift", "high"),
            ("execution_replay", "orchestration_instability", "medium"),
            ("verification", "validator_dependency_drift", "medium"),
        ):
            if previous.get(field, {}) != current.get(field, {}):
                drift.append(DriftRecord(category, severity, field, timestamp))

    if not drift:
        drift.append(DriftRecord("runtime_drift", "low", "no drift detected", timestamp))
    return drift
