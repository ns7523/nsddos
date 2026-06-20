"""Runtime flow-path correlation."""

from __future__ import annotations

from nsddos.runtime.interfaces import correlate_interfaces
from nsddos.runtime.models import PathCorrelation, PathRecord
from nsddos.runtime.openflow import correlate_openflow_ports
from nsddos.runtime.topology import correlate_topology
from nsddos.runtime.controller_state import controller_history_summary


def correlate_paths(config: dict) -> PathCorrelation:
    """Correlate expected single,3 host paths with telemetry/controller visibility."""
    topology = correlate_topology(config)
    interfaces = correlate_interfaces(config)
    openflow = correlate_openflow_ports(config)

    iface_by_name = {item.ovs_name: item for item in interfaces.interfaces if item.ovs_name}
    port_by_ovs = {item.ovs_name: item for item in openflow.ports if item.ovs_name}

    observed: list[PathRecord] = []
    missing: list[str] = []
    orphan: list[str] = []
    inconsistent: list[str] = []

    for host in topology.expected_hosts:
        iface_name = f"s1-eth{host[-1]}"
        iface = iface_by_name.get(iface_name)
        port = port_by_ovs.get(iface_name)
        canonical_id = f"path:s1->{host}"
        record = PathRecord(
            canonical_id=canonical_id,
            source_id="switch:s1",
            target_id=f"host:{host}",
            interface_id=iface.canonical_id if iface else None,
            port_id=port.canonical_id if port else None,
            visible_in_topology=canonical_id.replace("path:", "").replace("->", "-") in topology.graph_links,
            visible_in_controller=bool(port and port.visible_in_controller),
            visible_in_telemetry=bool((iface and iface.visible_in_sflow) or (port and port.visible_in_sflow)),
        )
        if not record.visible_in_topology or not record.visible_in_controller:
            missing.append(canonical_id)
        if record.visible_in_telemetry and not record.visible_in_controller:
            inconsistent.append(canonical_id)
        observed.append(record)

    known_path_ids = {item.canonical_id for item in observed}
    for port in openflow.ports:
        if port.ovs_name and port.ovs_name.startswith("s1-eth"):
            host_index = port.ovs_name.split("eth")[-1]
            path_id = f"path:s1->h{host_index}"
            if path_id not in known_path_ids:
                orphan.append(path_id)

    detail = (
        f"observed={len(observed)} missing={len(missing)} "
        f"orphan={len(orphan)} inconsistent={len(inconsistent)}"
    )
    history = controller_history_summary(config)
    stability = "unstable" if history.get("topology_changed") else ("stable" if not missing and not inconsistent and not orphan else "partial")
    return PathCorrelation(
        observed_paths=observed,
        missing_paths=sorted(set(missing)),
        orphan_paths=sorted(set(orphan)),
        inconsistent_paths=sorted(set(inconsistent)),
        stability=stability,
        detail=detail,
    )
