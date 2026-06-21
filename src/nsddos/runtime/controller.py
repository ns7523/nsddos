"""Authoritative Floodlight payload normalization."""

from __future__ import annotations

from typing import Any

from nsddos.providers.floodlight.provider import FloodlightProvider
from nsddos.runtime.models import (
    ControllerPathVisibility,
    ControllerPort,
    ControllerSwitch,
    ControllerTopology,
    DatapathRelationship,
)


def _normalize_port(payload: dict[str, Any]) -> ControllerPort:
    """Normalize raw controller port payload."""
    return ControllerPort(
        port_no=next((str(payload.get(key)) for key in ("portNumber", "portNo", "port", "number") if payload.get(key) is not None), None),
        name=next((str(payload.get(key)) for key in ("name", "portName", "interfaceName") if payload.get(key)), None),
        state=next((str(payload.get(key)) for key in ("state", "linkState") if payload.get(key) is not None), None),
        hardware_address=next((str(payload.get(key)) for key in ("hardwareAddress", "hwAddr") if payload.get(key)), None),
        config=next((str(payload.get(key)) for key in ("config", "portConfig") if payload.get(key) is not None), None),
    )


def _normalize_switch(payload: dict[str, Any]) -> ControllerSwitch:
    """Normalize raw controller switch payload."""
    dpid = next((str(payload.get(key)) for key in ("switchDPID", "dpid", "id") if payload.get(key)), None)
    raw_ports = next(
        (
            payload.get(key)
            for key in ("ports", "portDesc", "portDescriptions")
            if isinstance(payload.get(key), list)
        ),
        [],
    )
    ports = [_normalize_port(item) for item in raw_ports if isinstance(item, dict)]
    inet_address = next((str(payload.get(key)) for key in ("inetAddress", "socketAddress") if payload.get(key)), None)
    capabilities = [str(item) for item in payload.get("capabilities", []) if item is not None] if isinstance(payload.get("capabilities"), list) else []
    return ControllerSwitch(
        canonical_id=f"controller:{dpid or 'unknown'}",
        datapath_id=dpid,
        connected=bool(payload.get("connected", True)),
        inet_address=inet_address,
        ports=ports,
        capabilities=capabilities,
    )


def _normalize_link(payload: dict[str, Any]) -> DatapathRelationship:
    """Normalize raw link payload."""
    return DatapathRelationship(
        source_dpid=next((str(payload.get(key)) for key in ("src-switch", "srcSwitch", "src-switch-dpid") if payload.get(key)), None),
        source_port=next((str(payload.get(key)) for key in ("src-port", "srcPort") if payload.get(key) is not None), None),
        target_dpid=next((str(payload.get(key)) for key in ("dst-switch", "dstSwitch", "dst-switch-dpid") if payload.get(key)), None),
        target_port=next((str(payload.get(key)) for key in ("dst-port", "dstPort") if payload.get(key) is not None), None),
        relationship_type="link",
    )


def normalize_controller_topology(config: dict[str, Any]) -> ControllerTopology:
    """Normalize controller-visible runtime truth."""
    provider = FloodlightProvider(
        api_url=f"http://127.0.0.1:{config.get('lab', {}).get('floodlight_port', 8080)}"
    )
    reachable = provider.is_reachable()
    raw_switches = provider.switches() if reachable else []
    raw_links = provider._json_get("/wm/topology/links/json") if reachable else []
    switches = [_normalize_switch(item) for item in raw_switches if isinstance(item, dict)]
    links = [_normalize_link(item) for item in raw_links if isinstance(item, dict)] if isinstance(raw_links, list) else []

    visible_paths = [
        ControllerPathVisibility(
            canonical_id=f"path:{link.source_dpid}->{link.target_dpid}",
            source_dpid=link.source_dpid,
            target_dpid=link.target_dpid,
            visible=True,
            reason="controller_link_visible",
        )
        for link in links
    ]

    stale_entities = []
    for switch in switches:
        if not switch.connected:
            stale_entities.append(switch.canonical_id)
        for port in switch.ports:
            if not port.name or not port.port_no:
                stale_entities.append(f"{switch.canonical_id}:port:{port.port_no or 'unknown'}")

    detail = f"switches={len(switches)} links={len(links)} stale={len(stale_entities)}"
    return ControllerTopology(
        switches=switches,
        links=links,
        visible_paths=visible_paths,
        stale_entities=sorted(set(stale_entities)),
        detail=detail,
    )
