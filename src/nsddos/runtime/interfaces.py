"""Runtime interface correlation."""

from __future__ import annotations

from typing import Any

from nsddos.providers.mininet.provider import MininetProvider
from nsddos.providers.docker_helper import helper_link_index_map, helper_running
from nsddos.providers.ovs.provider import OVSProvider
from nsddos.providers.sflow.provider import SFlowProvider, resolve_sflowrt_api_url
from nsddos.runtime.controller_state import controller_history_summary
from nsddos.runtime.identity import build_identity_map
from nsddos.runtime.models import InterfaceCorrelation, InterfaceRecord


def _expected_switch_interfaces(metadata: Any) -> list[tuple[str, str]]:
    """Return expected switch-side interfaces for single,3 topology."""
    pairs: list[tuple[str, str]] = []
    for index, host in enumerate(metadata.hosts, start=1):
        pairs.append((f"s1-eth{index}", f"s1-{host}"))
    return pairs


def _extract_sflow_interfaces(payload: Any) -> list[str]:
    """Extract interface-like identifiers from sFlow topology."""
    names: set[str] = set()
    helper_links = helper_link_index_map() if helper_running() else {}
    items = (
        payload
        if isinstance(payload, list)
        else payload.values() if isinstance(payload, dict) else []
    )
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in ("ifname", "portName", "name", "dataSource"):
            value = item.get(key)
            if value:
                text = str(value)
                names.add(helper_links.get(text, text))
    return sorted(names)


def correlate_interfaces(config: dict[str, Any]) -> InterfaceCorrelation:
    """Correlate interfaces across runtime providers."""
    mininet = MininetProvider(
        controller_port=config.get("lab", {}).get("controller_port", 6653),
        topology=config.get("lab", {}).get("mininet_topology", "single,3"),
    )
    ovs = OVSProvider(
        collector_target=config.get("lab", {}).get(
            "ovs_sflow_target", "127.0.0.1:6343"
        ),
        agent_interface=config.get("lab", {}).get("ovs_agent_interface", "lo"),
        sampling=config.get("lab", {}).get("ovs_sampling", 10),
        polling=config.get("lab", {}).get("ovs_polling", 20),
    )
    sflow = SFlowProvider(api_url=resolve_sflowrt_api_url(config))

    metadata = mininet.topology_metadata()
    identity_map = build_identity_map(config)
    sflow_reachable = sflow.is_reachable()
    sflow_ifaces = _extract_sflow_interfaces(
        sflow.topology() if sflow_reachable else None
    )
    if not sflow_ifaces and sflow_reachable:
        sflow_ifaces = _extract_sflow_interfaces(sflow.flows())
    if helper_running():
        helper_ifaces = [
            name
            for name in helper_link_index_map().values()
            if name.startswith("s1-eth")
        ]
        sflow_ifaces = sorted(set(sflow_ifaces) | set(helper_ifaces))
    ovs_bridges = {bridge.name: bridge for bridge in ovs.ovs_state().bridges}
    records: list[InterfaceRecord] = []
    missing: list[str] = []
    duplicates: list[str] = []

    for ovs_name, link_name in _expected_switch_interfaces(metadata):
        record = InterfaceRecord(
            canonical_id=f"iface:{ovs_name}",
            switch_id=(
                identity_map.switches[0].canonical_id if identity_map.switches else None
            ),
            ovs_name=ovs_name,
            mininet_link=link_name,
            sflow_name=next(
                (
                    name
                    for name in sflow_ifaces
                    if ovs_name in name or link_name in name
                ),
                None,
            ),
            controller_port=None,
            visible_in_ovs=ovs_name
            in ovs_bridges.get("s1", type("B", (), {"interfaces": []})()).interfaces,
            visible_in_sflow=any(
                ovs_name in name or link_name in name for name in sflow_ifaces
            ),
            visible_in_controller=False,
        )
        if not record.visible_in_ovs or not record.visible_in_sflow:
            missing.append(record.canonical_id)
        records.append(record)

    seen: set[str] = set()
    for record in records:
        if record.sflow_name and record.sflow_name in seen:
            duplicates.append(record.sflow_name)
        if record.sflow_name:
            seen.add(record.sflow_name)

    expected_ovs_names = {item.ovs_name for item in records if item.ovs_name}
    live_ovs_names = set(
        ovs_bridges.get("s1", type("B", (), {"interfaces": []})()).interfaces
    )
    orphan = sorted(live_ovs_names - expected_ovs_names)

    detail = (
        f"expected={len(records)} visible_ovs={sum(1 for item in records if item.visible_in_ovs)} "
        f"visible_sflow={sum(1 for item in records if item.visible_in_sflow)}"
    )
    history = controller_history_summary(config)
    stability = (
        "unstable"
        if history.get("topology_changed")
        else ("stable" if not missing and not duplicates and not orphan else "partial")
    )
    return InterfaceCorrelation(
        interfaces=records,
        missing_interfaces=sorted(set(missing)),
        orphan_interfaces=orphan,
        duplicate_mappings=sorted(set(duplicates)),
        stability=stability,
        detail=detail,
    )
