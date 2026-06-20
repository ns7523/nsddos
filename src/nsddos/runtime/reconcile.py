"""Runtime truth reconciliation."""

from __future__ import annotations

from nsddos.config import load_runtime_state
from nsddos.runtime.controller import normalize_controller_topology
from nsddos.runtime.identity import build_identity_map
from nsddos.runtime.interfaces import correlate_interfaces
from nsddos.runtime.openflow import correlate_openflow_ports
from nsddos.runtime.paths import correlate_paths
from nsddos.runtime.models import ReconciliationState
from nsddos.runtime.topology import correlate_topology


def reconcile_runtime(config: dict) -> ReconciliationState:
    """Reconcile expected, observed, telemetry-visible, runtime state truth."""
    runtime_state = load_runtime_state()
    controller = normalize_controller_topology(config)
    identity = build_identity_map(config)
    interfaces = correlate_interfaces(config)
    openflow = correlate_openflow_ports(config)
    paths = correlate_paths(config)
    topology = correlate_topology(config)

    missing = []
    stale = []
    inconsistent = []
    orphan = []
    confidence_reductions = []

    missing.extend(f"switch:{name}" for name in topology.missing_in_ovs)
    missing.extend(f"controller:{name}" for name in topology.missing_in_controller)
    missing.extend(f"interface:{name}" for name in interfaces.missing_interfaces)
    missing.extend(f"port:{name}" for name in openflow.missing_ports)
    missing.extend(f"path:{name}" for name in paths.missing_paths)
    missing.extend(f"controller:{name}" for name in controller.stale_entities if name.startswith("controller:"))

    if runtime_state.stack_running and runtime_state.topology_state != "running":
        inconsistent.append("runtime_state:stack_running_without_topology")
        confidence_reductions.append("runtime_state_mismatch")

    if topology.missing_in_sflow:
        stale.extend(f"sflow:{name}" for name in topology.missing_in_sflow)
        confidence_reductions.append("telemetry_gap")
    stale.extend(f"port:{name}" for name in openflow.stale_ports)
    stale.extend(f"controller:{name}" for name in controller.stale_entities if not name.startswith("controller:"))
    if openflow.stale_ports:
        confidence_reductions.append("stale_datapath_mapping")

    orphan.extend(f"interface:{name}" for name in interfaces.orphan_interfaces)
    orphan.extend(f"port:{name}" for name in openflow.orphan_ports)
    orphan.extend(f"path:{name}" for name in paths.orphan_paths)
    orphan.extend(identity.conflicts)

    if not topology.consistent:
        inconsistent.append("topology:provider_disagreement")
        confidence_reductions.append("topology_disagreement")
    if controller.links and not topology.graph_links:
        inconsistent.append("controller:topology_divergence")
        confidence_reductions.append("controller_topology_divergence")
    if controller.stale_entities:
        confidence_reductions.append("controller_stale_entities")
    if interfaces.duplicate_mappings:
        inconsistent.extend(f"duplicate:{name}" for name in interfaces.duplicate_mappings)
        confidence_reductions.append("duplicate_interface_mapping")
    if openflow.duplicate_ports:
        inconsistent.extend(f"duplicate_port:{name}" for name in openflow.duplicate_ports)
        confidence_reductions.append("duplicate_openflow_port")
    if paths.inconsistent_paths:
        inconsistent.extend(f"path:{name}" for name in paths.inconsistent_paths)
        confidence_reductions.append("telemetry_path_divergence")

    detail = (
        f"missing={len(missing)} stale={len(stale)} "
        f"inconsistent={len(inconsistent)} orphan={len(orphan)}"
    )
    return ReconciliationState(
        missing_entities=sorted(set(missing)),
        stale_entities=sorted(set(stale)),
        inconsistent_entities=sorted(set(inconsistent)),
        orphan_entities=sorted(set(orphan)),
        confidence_reductions=sorted(set(confidence_reductions)),
        detail=detail,
    )
