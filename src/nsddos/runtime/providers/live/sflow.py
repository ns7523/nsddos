"""Live sFlow telemetry adapter."""

from __future__ import annotations

from collections import Counter
from typing import Any

from nsddos.providers.docker_helper import helper_link_index_map, helper_running
from nsddos.providers.sflow.provider import SFlowProvider
from nsddos.runtime.providers.live.connection_pool import DeterministicConnectionPool
from nsddos.runtime.providers.live.contracts import DistributionPoint


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def collect_sflow_telemetry(
    provider: SFlowProvider,
    pool: DeterministicConnectionPool,
) -> dict[str, object]:
    flows_result = pool.get_json(f"{provider.api_url}/flows/json?maxFlows=20&timeout=1")
    metrics_result = pool.get_json(f"{provider.api_url}/metric/ALL/json")
    topology_result = pool.get_json(f"{provider.api_url}/topology/json")
    flows = flows_result.payload if isinstance(flows_result.payload, list) else []
    metrics = metrics_result.payload if metrics_result.ok else None
    helper_links = helper_link_index_map() if helper_running() else {}
    packet_rate = sum(
        _number(item.get("packets", item.get("frames", 0))) for item in flows
    )
    byte_rate = sum(_number(item.get("bytes", item.get("octets", 0))) for item in flows)
    connection_rate = sum(
        _number(item.get("connections", item.get("flows", 0))) for item in flows
    )
    syn_rate = sum(_number(item.get("syn_rate", 0)) for item in flows)
    udp_rate = sum(_number(item.get("udp_rate", 0)) for item in flows)
    icmp_rate = sum(_number(item.get("icmp_rate", 0)) for item in flows)
    dropped_packets = 0
    if isinstance(metrics, list):
        dropped_packets = int(sum(_number(item.get("drops", 0)) for item in metrics))
    source_counter = Counter(
        str(item.get("source", item.get("src_ip", "unknown")))
        for item in flows
        if item.get("source") or item.get("src_ip")
    )
    port_counter = Counter(
        str(item.get("destination_port", item.get("dst_port", 0)))
        for item in flows
        if item.get("destination_port") or item.get("dst_port")
    )
    topology_interfaces = {
        str(item.get("ifname", "")) for item in flows if item.get("ifname")
    }
    for item in flows:
        data_source = item.get("dataSource")
        if data_source is not None:
            mapped = helper_links.get(str(data_source))
            if mapped:
                topology_interfaces.add(mapped)
    if not topology_interfaces and helper_links:
        topology_interfaces = {
            name for name in helper_links.values() if name.startswith("s1-eth")
        }
    return {
        "reachable": provider.is_reachable(),
        "latency_ms": max(
            flows_result.latency_ms,
            metrics_result.latency_ms,
            topology_result.latency_ms,
        ),
        "packet_rate": packet_rate,
        "byte_rate": byte_rate,
        "connection_rate": connection_rate,
        "syn_rate": syn_rate,
        "udp_rate": udp_rate,
        "icmp_rate": icmp_rate,
        "active_flows": len(flows),
        "dropped_packets": dropped_packets,
        "source_ip_distribution": tuple(
            DistributionPoint(key=key, value=float(value))
            for key, value in sorted(source_counter.items())
        ),
        "destination_port_distribution": tuple(
            DistributionPoint(key=key, value=float(value))
            for key, value in sorted(port_counter.items())
        ),
        "interfaces": tuple(sorted(name for name in topology_interfaces if name)),
        "raw_topology": topology_result.payload,
        "malformed": not flows_result.ok or not isinstance(flows, list),
    }
