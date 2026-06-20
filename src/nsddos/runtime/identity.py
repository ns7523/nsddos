"""Runtime identity normalization."""

from __future__ import annotations

from typing import Any

from nsddos.providers.floodlight.provider import FloodlightProvider
from nsddos.providers.mininet.provider import MininetProvider
from nsddos.providers.ovs.provider import OVSProvider
from nsddos.providers.sflow.provider import SFlowProvider
from nsddos.runtime.controller_state import controller_history_summary
from nsddos.runtime.models import IdentityMap, IdentityRecord


def _extract_sflow_agents(payload: Any) -> list[str]:
    """Extract agent-like names from sFlow topology payload."""
    values: set[str] = set()
    items = payload if isinstance(payload, list) else payload.values() if isinstance(payload, dict) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in ("agent", "dataSource", "name"):
            value = item.get(key)
            if value:
                values.add(str(value))
    return sorted(values)


def build_identity_map(config: dict[str, Any]) -> IdentityMap:
    """Normalize switch identities across providers."""
    mininet = MininetProvider(
        controller_port=config.get("lab", {}).get("controller_port", 6653),
        topology=config.get("lab", {}).get("mininet_topology", "single,3"),
    )
    ovs = OVSProvider(
        collector_target=config.get("lab", {}).get("ovs_sflow_target", "127.0.0.1:6343"),
        agent_interface=config.get("lab", {}).get("ovs_agent_interface", "lo"),
        sampling=config.get("lab", {}).get("ovs_sampling", 10),
        polling=config.get("lab", {}).get("ovs_polling", 20),
    )
    floodlight = FloodlightProvider(
        api_url=f"http://127.0.0.1:{config.get('lab', {}).get('floodlight_port', 8080)}"
    )
    sflow = SFlowProvider(api_url=f"http://127.0.0.1:{config.get('api_port', 8008)}")

    metadata = mininet.topology_metadata()
    ovs_bridges = ovs.list_bridges() if ovs.is_installed() else []
    controller_switches = floodlight.switches()
    sflow_agents = _extract_sflow_agents(sflow.topology() if sflow.is_reachable() else None)

    records: list[IdentityRecord] = []
    conflicts: list[str] = []
    aliases: dict[str, list[str]] = {}

    for index, switch_name in enumerate(metadata.switches):
        canonical_id = f"switch:{switch_name}"
        ovs_bridge = switch_name if switch_name in ovs_bridges else None
        controller_dpid = None
        if index < len(controller_switches):
            controller_dpid = str(controller_switches[index].get("switchDPID", ""))
        sflow_agent = next((agent for agent in sflow_agents if switch_name in agent), None)
        record_aliases = [value for value in (switch_name, ovs_bridge, controller_dpid, sflow_agent) if value]
        records.append(
            IdentityRecord(
                canonical_id=canonical_id,
                mininet_name=switch_name,
                ovs_bridge=ovs_bridge,
                controller_dpid=controller_dpid,
                sflow_agent=sflow_agent,
                aliases=sorted(set(record_aliases)),
            )
        )
        aliases[canonical_id] = sorted(set(record_aliases))
        if controller_dpid and any(item.controller_dpid == controller_dpid for item in records[:-1]):
            conflicts.append(f"duplicate_controller_dpid:{controller_dpid}")

    if len(controller_switches) > len(metadata.switches):
        for extra in controller_switches[len(metadata.switches):]:
            conflicts.append(f"orphan_controller_switch:{extra.get('switchDPID', 'unknown')}")

    detail = (
        f"mininet={len(metadata.switches)} ovs={len(ovs_bridges)} "
        f"controller={len(controller_switches)} sflow_agents={len(sflow_agents)}"
    )
    history = controller_history_summary(config)
    stability = "unstable" if history.get("topology_changed") else ("stable" if not conflicts else "partial")
    return IdentityMap(
        switches=records,
        controller_endpoint=f"127.0.0.1:{config.get('lab', {}).get('controller_port', 6653)}",
        provider_aliases=aliases,
        conflicts=conflicts,
        stability=stability,
        detail=detail,
    )
