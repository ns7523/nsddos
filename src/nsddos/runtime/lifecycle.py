"""Deterministic runtime lifecycle sequencing."""

from __future__ import annotations

from typing import Any

from nsddos.config import load_runtime_state, write_runtime_state
from nsddos.docker_manager import DockerManager
from nsddos.providers.floodlight.provider import FloodlightProvider
from nsddos.providers.mininet.provider import MininetProvider
from nsddos.providers.ovs.provider import OVSProvider
from nsddos.providers.sflow.provider import SFlowProvider, resolve_sflowrt_api_url
from nsddos.runtime.events import emit_runtime_event
from nsddos.runtime.readiness import wait_for_check, wait_for_http
from nsddos.runtime.telemetry import (
    build_telemetry_state,
    collect_provider_status,
)
from nsddos.runtime.verification.engine import execute_runtime_verification
from nsddos.runtime.controller import normalize_controller_topology
from nsddos.runtime.confidence import runtime_confidence_summary
from nsddos.runtime.convergence import validate_convergence
from nsddos.runtime.flows import sample_flow_visibility, telemetry_freshness
from nsddos.runtime.identity import build_identity_map
from nsddos.runtime.interfaces import correlate_interfaces
from nsddos.runtime.openflow import correlate_openflow_ports
from nsddos.runtime.paths import correlate_paths
from nsddos.runtime.reconcile import reconcile_runtime
from nsddos.runtime.topology import correlate_topology


def _restart_mininet_datapath(
    config: dict[str, Any],
    mininet: MininetProvider,
    ovs: OVSProvider,
    bridge_name: str,
) -> None:
    """Restart Mininet datapath and wait for bridge/controller recovery."""
    mininet.stop()
    mininet.start()
    bridge_ready = wait_for_check(
        "ovs_bridge",
        lambda: ovs.bridge_exists(bridge_name),
        f"bridge {bridge_name} exists",
        timeout=60,
    )
    if not bridge_ready.ok:
        raise RuntimeError(bridge_ready.detail)
    controller_ready = wait_for_check(
        "ovs_controller",
        ovs.any_controller_connected,
        "OVS controller connected",
        timeout=60,
    )
    if not controller_ready.ok:
        raise RuntimeError(controller_ready.detail)


def _validate_baseline_datapath(
    config: dict[str, Any],
    mininet: MininetProvider,
    ovs: OVSProvider,
    floodlight: FloodlightProvider,
    bridge_name: str,
) -> dict[str, Any]:
    """Validate baseline forwarding and recover once if the datapath is misconfigured."""
    expected_protocol = config.get("lab", {}).get("ovs_protocol", "OpenFlow13")
    target_ip = config.get("lab", {}).get("victim_ip", "10.0.0.2")
    probes = (
        ("h1", target_ip),
        ("h3", target_ip),
    )
    last_result: dict[str, Any] = {}

    for attempt in range(2):
        connectivity = [mininet.probe_connectivity(source, destination) for source, destination in probes]
        forwarding_programmed = ovs.forwarding_programmed(bridge_name)
        protocol_ready = ovs.bridge_has_protocol(bridge_name, expected_protocol)
        flow_stats_accessible = floodlight.flow_stats_accessible()
        fallback_applied = False
        if protocol_ready and not forwarding_programmed:
            fallback_applied = ovs.install_normal_flow(bridge_name)
            if fallback_applied:
                connectivity = [mininet.probe_connectivity(source, destination) for source, destination in probes]
                forwarding_programmed = ovs.forwarding_programmed(bridge_name)
        forwarding_ready = forwarding_programmed or floodlight.forwarding_programmed()
        baseline_ok = protocol_ready and forwarding_ready and all(
            probe.get("reachable", False) for probe in connectivity
        )
        last_result = {
            "attempt": attempt + 1,
            "expected_protocol": expected_protocol,
            "protocol_ready": protocol_ready,
            "flow_stats_accessible": flow_stats_accessible,
            "forwarding_programmed": forwarding_programmed,
            "fallback_applied": fallback_applied,
            "connectivity": connectivity,
            "baseline_ok": baseline_ok,
        }
        if baseline_ok:
            return last_result
        if attempt == 0:
            emit_runtime_event(
                "provider.datapath",
                "recovering",
                "Baseline datapath invalid; recreating Mininet bridge.",
                last_result,
            )
            _restart_mininet_datapath(config, mininet, ovs, bridge_name)

    return last_result


def start_lab_runtime(config: dict[str, Any]) -> Any:
    """Start runtime in deterministic order."""
    manager = DockerManager()
    floodlight = FloodlightProvider(
        api_url=f"http://127.0.0.1:{config.get('lab', {}).get('floodlight_port', 8080)}"
    )
    sflow = SFlowProvider(api_url=resolve_sflowrt_api_url(config))
    ovs = OVSProvider(
        collector_target=config.get("lab", {}).get("ovs_sflow_target", "127.0.0.1:6343"),
        agent_interface=config.get("lab", {}).get("ovs_agent_interface", "lo"),
        sampling=config.get("lab", {}).get("ovs_sampling", 10),
        polling=config.get("lab", {}).get("ovs_polling", 20),
        expected_protocol=config.get("lab", {}).get("ovs_protocol", "OpenFlow13"),
    )
    mininet = MininetProvider(
        controller_port=config.get("lab", {}).get("controller_port", 6653),
        topology=config.get("lab", {}).get("mininet_topology", "single,3"),
        ovs_protocol=config.get("lab", {}).get("ovs_protocol", "OpenFlow13"),
    )
    bridge_name = config.get("lab", {}).get("ovs_bridge", "s1")

    emit_runtime_event("lab.start", "started", "Starting lab runtime.")
    floodlight.start()
    sflow.start()

    emit_runtime_event("provider.floodlight", "started", "Starting Floodlight container.")
    manager.start_services(["floodlight"])
    floodlight_ready = wait_for_http(
        "floodlight",
        f"http://127.0.0.1:{config.get('lab', {}).get('floodlight_port', 8080)}/wm/core/health/json",
        timeout=60,
    )
    if not floodlight_ready.ok:
        emit_runtime_event("lab.start", "failed", "Floodlight readiness failed.", {"detail": floodlight_ready.detail})
        raise RuntimeError(floodlight_ready.detail)

    emit_runtime_event("provider.labhost", "started", "Starting Mininet/OVS helper container.")
    manager.start_services(["labhost"])

    ovs.start()
    emit_runtime_event("provider.ovs", "validated", "OVS base readiness validated.")
    emit_runtime_event("provider.sflowrt", "started", "Starting sFlow-RT and detector containers.")
    manager.start_services(["sflowrt", "detector"])
    sflow_ready = wait_for_http("sflowrt", resolve_sflowrt_api_url(config), timeout=60)
    if not sflow_ready.ok:
        emit_runtime_event("lab.start", "failed", "sFlow-RT readiness failed.", {"detail": sflow_ready.detail})
        raise RuntimeError(sflow_ready.detail)

    detector_ready = wait_for_http(
        "detector",
        f"http://127.0.0.1:{config.get('lab', {}).get('detector_port', 9000)}",
        timeout=30,
    )
    if not detector_ready.ok:
        emit_runtime_event("lab.start", "failed", "Detector readiness failed.", {"detail": detector_ready.detail})
        raise RuntimeError(detector_ready.detail)

    if config.get("simulation", {}).get("enabled", True):
        emit_runtime_event("provider.mininet", "started", "Starting Mininet topology.")
        mininet.start()

    topology_ready = wait_for_check(
        "ovs_bridge",
        lambda: ovs.bridge_exists(bridge_name),
        f"bridge {bridge_name} exists",
        timeout=60,
    )
    if not topology_ready.ok:
        emit_runtime_event("lab.start", "failed", "OVS bridge readiness failed.", {"detail": topology_ready.detail})
        raise RuntimeError(topology_ready.detail)

    controller_ready = wait_for_check(
        "ovs_controller",
        ovs.any_controller_connected,
        "OVS controller connected",
        timeout=60,
    )
    if not controller_ready.ok:
        emit_runtime_event("lab.start", "failed", "Controller connectivity failed.", {"detail": controller_ready.detail})
        raise RuntimeError(controller_ready.detail)

    datapath_ready = _validate_baseline_datapath(config, mininet, ovs, floodlight, bridge_name)
    if not datapath_ready.get("baseline_ok"):
        emit_runtime_event("lab.start", "failed", "Baseline datapath validation failed.", datapath_ready)
        raise RuntimeError(
            "baseline datapath validation failed: "
            f"protocol_ready={datapath_ready.get('protocol_ready')} "
            f"flow_stats_accessible={datapath_ready.get('flow_stats_accessible')} "
            f"forwarding_programmed={datapath_ready.get('forwarding_programmed')}"
        )
    emit_runtime_event("provider.datapath", "validated", "Baseline datapath validated.", datapath_ready)

    if not ovs.attach_sflow(bridge_name):
        emit_runtime_event("lab.start", "failed", "sFlow attachment failed.", {"bridge": bridge_name})
        raise RuntimeError(f"sFlow attachment failed for bridge {bridge_name}")
    emit_runtime_event("provider.ovs", "configured", "sFlow attached to OVS bridge.", {"bridge": bridge_name})

    telemetry_ready = wait_for_check(
        "sflow_topology",
        lambda: bool(sflow.status().get("topology_accessible")),
        "sFlow topology API available",
        timeout=30,
    )
    if not telemetry_ready.ok:
        emit_runtime_event("lab.start", "failed", "Telemetry validation failed.", {"detail": telemetry_ready.detail})
        raise RuntimeError(telemetry_ready.detail)

    telemetry = build_telemetry_state(config)
    flows = sample_flow_visibility(config, interval=1.0)
    freshness = telemetry_freshness(config, interval=1.0)
    identity = build_identity_map(config)
    interfaces = correlate_interfaces(config)
    controller = normalize_controller_topology(config)
    convergence = validate_convergence(config)
    openflow = correlate_openflow_ports(config)
    paths = correlate_paths(config)
    topology = correlate_topology(config)
    reconciliation = reconcile_runtime(config)
    provider_status = collect_provider_status(config)
    confidence = runtime_confidence_summary(topology, flows, freshness, execute_runtime_verification(config), reconciliation)
    state = load_runtime_state()
    state.provider_status = provider_status
    state.ovs_state = provider_status["ovs"]
    state.telemetry_state = telemetry.to_dict()
    state.flow_state = flows.to_dict()
    state.identity_map = identity.to_dict()
    state.interface_state = interfaces.to_dict()
    state.openflow_state = openflow.to_dict()
    state.path_state = paths.to_dict()
    state.controller_state = controller.to_dict()
    state.convergence_state = convergence.to_dict()
    state.topology_correlation = topology.to_dict()
    state.reconciliation_state = reconciliation.to_dict()
    state.confidence_summary = confidence
    state.topology_metadata = provider_status["mininet"].get("metadata", {})
    state.controller_connected = bool(provider_status["floodlight"].get("controller_port_open"))
    state.last_error = None
    write_runtime_state(state)
    emit_runtime_event("lab.start", "completed", "Lab runtime started.", {"bridge": bridge_name})
    return state


def stop_lab_runtime(config: dict[str, Any]) -> Any:
    """Stop runtime cleanly."""
    emit_runtime_event("lab.stop", "started", "Stopping lab runtime.")
    mininet = MininetProvider(
        controller_port=config.get("lab", {}).get("controller_port", 6653),
        topology=config.get("lab", {}).get("mininet_topology", "single,3"),
    )
    try:
        mininet.stop()
    except RuntimeError:
        pass
    manager = DockerManager()
    manager.stop_stack()
    state = load_runtime_state()
    emit_runtime_event("lab.stop", "completed", "Lab runtime stopped.")
    return state
