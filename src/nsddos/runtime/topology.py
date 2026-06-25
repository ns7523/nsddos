"""Topology truth correlation across providers."""

from __future__ import annotations

from typing import Any

from nsddos.providers.mininet.provider import MininetProvider
from nsddos.runtime.identity import build_identity_map
from nsddos.runtime.interfaces import correlate_interfaces
from nsddos.runtime.models import TopologyCorrelation


def _expected_graph_links(hosts: list[str]) -> list[str]:
    """Return deterministic single,3 graph links."""
    return [f"s1-{host}" for host in hosts]


def correlate_topology(config: dict[str, Any]) -> TopologyCorrelation:
    """Correlate normalized runtime topology for supported lab topology."""
    mininet = MininetProvider(
        controller_port=config.get("lab", {}).get("controller_port", 6653),
        topology=config.get("lab", {}).get("mininet_topology", "single,3"),
    )
    metadata = mininet.topology_metadata()
    identity = build_identity_map(config)
    interfaces = correlate_interfaces(config)

    controller_switches = [
        item.controller_dpid or "" for item in identity.switches if item.controller_dpid
    ]
    ovs_bridges = [
        item.ovs_bridge or "" for item in identity.switches if item.ovs_bridge
    ]
    sflow_interfaces = [
        item.sflow_name or "" for item in interfaces.interfaces if item.sflow_name
    ]
    ovs_interfaces = [
        item.ovs_name or "" for item in interfaces.interfaces if item.ovs_name
    ]
    normalized_switches = [item.canonical_id for item in identity.switches]

    missing_in_controller = [
        item.mininet_name
        for item in identity.switches
        if item.mininet_name and not item.controller_dpid
    ]
    missing_in_ovs = [
        item.mininet_name
        for item in identity.switches
        if item.mininet_name and not item.ovs_bridge
    ]
    missing_in_sflow = [
        item.ovs_name
        for item in interfaces.interfaces
        if item.ovs_name and not item.visible_in_sflow
    ]
    provider_agreement = []
    if missing_in_controller:
        provider_agreement.append("controller_missing_switches")
    if missing_in_ovs:
        provider_agreement.append("ovs_missing_switches")
    if missing_in_sflow:
        provider_agreement.append("sflow_missing_interfaces")
    if identity.conflicts:
        provider_agreement.extend(identity.conflicts)

    graph_links = _expected_graph_links(metadata.hosts)
    consistent = not provider_agreement and not interfaces.orphan_interfaces
    detail = (
        f"switches={len(normalized_switches)} controller={len(controller_switches)} "
        f"ovs={len(ovs_bridges)} sflow_ifaces={len(sflow_interfaces)} "
        f"orphans={len(interfaces.orphan_interfaces)}"
    )

    return TopologyCorrelation(
        expected_switches=metadata.switches,
        expected_hosts=metadata.hosts,
        controller_switches=controller_switches,
        ovs_bridges=ovs_bridges,
        ovs_interfaces=ovs_interfaces,
        sflow_interfaces=sflow_interfaces,
        missing_in_controller=sorted(item for item in missing_in_controller if item),
        missing_in_ovs=sorted(item for item in missing_in_ovs if item),
        missing_in_sflow=sorted(item for item in missing_in_sflow if item),
        normalized_switches=normalized_switches,
        provider_agreement=sorted(set(provider_agreement)),
        graph_links=graph_links,
        consistent=consistent,
        detail=detail,
    )
