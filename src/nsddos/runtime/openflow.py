"""OpenFlow datapath port correlation."""

from __future__ import annotations

from nsddos.runtime.controller import normalize_controller_topology
from nsddos.runtime.identity import build_identity_map
from nsddos.runtime.interfaces import correlate_interfaces
from nsddos.runtime.models import OpenFlowCorrelation, OpenFlowPortRecord


def correlate_openflow_ports(config: dict) -> OpenFlowCorrelation:
    """Correlate authoritative controller ports with runtime interfaces."""
    controller = normalize_controller_topology(config)
    identity = build_identity_map(config)
    interfaces = correlate_interfaces(config)

    ports: list[OpenFlowPortRecord] = []
    missing: list[str] = []
    stale: list[str] = []
    orphan: list[str] = []
    duplicates: list[str] = []
    seen_keys: set[str] = set()

    interface_by_ovs = {item.ovs_name: item for item in interfaces.interfaces if item.ovs_name}
    switch_by_dpid = {item.controller_dpid: item for item in identity.switches if item.controller_dpid}
    fallback_switch = identity.switches[0] if identity.switches else None

    for switch in controller.switches:
        runtime_switch = switch_by_dpid.get(switch.datapath_id, fallback_switch)
        switch_id = runtime_switch.canonical_id if runtime_switch else f"switch:{switch.datapath_id or 'unknown'}"

        if not switch.ports:
            if runtime_switch:
                for iface in [item for item in interfaces.interfaces if item.switch_id == runtime_switch.canonical_id]:
                    port_suffix = iface.ovs_name.split("eth")[-1] if iface.ovs_name and "eth" in iface.ovs_name else "unknown"
                    port_id = f"{switch_id}:{port_suffix}"
                    ports.append(
                        OpenFlowPortRecord(
                            canonical_id=port_id,
                            switch_id=switch_id,
                            datapath_id=switch.datapath_id,
                            port_no=port_suffix if port_suffix.isdigit() else None,
                            controller_name=iface.ovs_name,
                            ovs_name=iface.ovs_name,
                            mininet_interface=iface.ovs_name,
                            sflow_name=iface.sflow_name,
                            visible_in_controller=bool(switch.connected),
                            visible_in_ovs=iface.visible_in_ovs,
                            visible_in_sflow=iface.visible_in_sflow,
                        )
                    )
            continue

        for port in switch.ports:
            iface = None
            if port.name:
                iface = interface_by_ovs.get(port.name)
            if iface is None and port.port_no and port.port_no.isdigit():
                iface = interface_by_ovs.get(f"s1-eth{port.port_no}")

            canonical_id = f"{switch_id}:{port.port_no or 'unknown'}"
            key = f"{switch.datapath_id}:{port.port_no}"
            if key in seen_keys:
                duplicates.append(canonical_id)
            seen_keys.add(key)

            record = OpenFlowPortRecord(
                canonical_id=canonical_id,
                switch_id=switch_id,
                datapath_id=switch.datapath_id,
                port_no=port.port_no,
                controller_name=port.name,
                ovs_name=iface.ovs_name if iface else port.name,
                mininet_interface=iface.ovs_name if iface else None,
                sflow_name=iface.sflow_name if iface else None,
                visible_in_controller=True,
                visible_in_ovs=iface.visible_in_ovs if iface else False,
                visible_in_sflow=iface.visible_in_sflow if iface else False,
            )
            if not record.visible_in_ovs:
                stale.append(canonical_id)
            if iface is None:
                orphan.append(canonical_id)
            ports.append(record)

    # Expected runtime interfaces without controller match -> missing controller ports.
    live_ovs = {item.ovs_name for item in interfaces.interfaces if item.ovs_name}
    mapped_ovs = {item.ovs_name for item in ports if item.ovs_name}
    for ovs_name in sorted(name for name in live_ovs if name and name not in mapped_ovs):
        switch_id = fallback_switch.canonical_id if fallback_switch else "switch:unknown"
        port_id = f"{switch_id}:unknown:{ovs_name}"
        missing.append(port_id)

    detail = (
        f"ports={len(ports)} missing={len(set(missing))} "
        f"stale={len(set(stale))} orphan={len(set(orphan))}"
    )
    return OpenFlowCorrelation(
        ports=ports,
        missing_ports=sorted(set(missing)),
        stale_ports=sorted(set(stale)),
        orphan_ports=sorted(set(orphan)),
        duplicate_ports=sorted(set(duplicates)),
        detail=detail,
    )
