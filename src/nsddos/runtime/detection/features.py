"""Deterministic telemetry feature extraction."""

from __future__ import annotations

import math
from collections import Counter
from statistics import pvariance
from typing import Any

from nsddos.runtime.detection.models import FeatureVector


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _pick_number(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if key in row and row[key] is not None:
            return _number(row[key])
    return 0.0


def _port_value(flow: dict[str, Any]) -> int:
    for key in ("destination_port", "dst_port", "destinationPort", "port", "dstport"):
        if key in flow and flow[key] not in {None, ""}:
            return int(_number(flow[key]))
    return 0


def _source_value(flow: dict[str, Any]) -> str:
    for key in ("source", "src_ip", "src", "source_ip", "ipsource"):
        value = flow.get(key)
        if value:
            return str(value)
    return "unknown"


def _duration_value(flow: dict[str, Any]) -> float:
    return _pick_number(flow, "duration", "flow_duration", "duration_ms", "elapsed")


def _packet_count(flow: dict[str, Any]) -> float:
    return _pick_number(flow, "packets", "frames", "packet_count", "sampledPacketSize")


def _byte_count(flow: dict[str, Any]) -> float:
    return _pick_number(flow, "bytes", "octets", "byte_count", "value")


def _connection_count(flow: dict[str, Any]) -> float:
    return _pick_number(flow, "connections", "flows", "connection_count", "new_connections")


def _flag_rate(flow: dict[str, Any], preferred: str, fallback_flag: str) -> float:
    direct = _pick_number(flow, preferred, f"{preferred}_rate", f"{preferred}_count")
    if direct > 0:
        return direct
    flags = str(flow.get("tcpFlags", flow.get("flags", ""))).upper()
    return _packet_count(flow) if fallback_flag in flags else 0.0


def _protocol_rate(flow: dict[str, Any], protocol: str, *keys: str) -> float:
    direct = _pick_number(flow, *keys)
    if direct > 0:
        return direct
    proto_value = str(flow.get("protocol", flow.get("ipProtocol", ""))).lower()
    if proto_value in {protocol, protocol.upper()}:
        return _packet_count(flow)
    return 0.0


def _http_rate(flow: dict[str, Any]) -> float:
    direct = _pick_number(flow, "http_rate", "request_rate", "request_count")
    if direct > 0:
        return direct
    protocol = str(flow.get("protocol", flow.get("ipProtocol", ""))).lower()
    if protocol in {"http", "https", "slowloris"}:
        return _packet_count(flow)
    if any(flow.get(key) for key in ("http_method", "method", "url", "uri", "host", "user_agent")):
        return _packet_count(flow)
    return 0.0


def _partial_connection_rate(flow: dict[str, Any]) -> float:
    direct = _pick_number(flow, "partial_connection_rate", "partial_requests", "incomplete_requests")
    if direct > 0:
        return direct
    protocol = str(flow.get("protocol", flow.get("ipProtocol", ""))).lower()
    if protocol == "slowloris":
        return _connection_count(flow) or _packet_count(flow)
    return _connection_count(flow) if bool(flow.get("partial_headers")) else 0.0


def _entropy(counter: Counter[str]) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    score = 0.0
    for count in counter.values():
        probability = count / total
        score -= probability * math.log(probability, 2)
    return score


def extract_feature_vector(telemetry: dict[str, Any]) -> FeatureVector:
    """Extract deterministic feature vector from telemetry payload."""
    flows = [item for item in telemetry.get("flows", []) if isinstance(item, dict)]
    flow_state = telemetry.get("flow_state", {})
    sample_seconds = max(1.0, _number(telemetry.get("sample_window_seconds", 1.0), 1.0))
    packet_total = sum(_packet_count(flow) for flow in flows)
    byte_total = sum(_byte_count(flow) for flow in flows)
    connection_total = sum(_connection_count(flow) for flow in flows) or float(flow_state.get("flow_count", len(flows)))
    syn_total = sum(_flag_rate(flow, "syn_rate", "S") for flow in flows)
    ack_total = sum(_flag_rate(flow, "ack_rate", "A") for flow in flows)
    udp_total = sum(_protocol_rate(flow, "udp", "udp_rate", "udp_packets") for flow in flows)
    icmp_total = sum(_protocol_rate(flow, "icmp", "icmp_rate", "icmp_packets") for flow in flows)
    http_total = sum(_http_rate(flow) for flow in flows)
    partial_connection_total = sum(_partial_connection_rate(flow) for flow in flows)
    durations = [_duration_value(flow) for flow in flows if _duration_value(flow) > 0]
    sources = Counter(_source_value(flow) for flow in flows)
    ports = Counter(_port_value(flow) for flow in flows if _port_value(flow) > 0)
    packet_sizes = [(_byte_count(flow) / max(_packet_count(flow), 1.0)) for flow in flows if _byte_count(flow) > 0]
    flow_duration = sum(durations) / len(durations) if durations else 0.0
    packet_rate = packet_total / sample_seconds
    byte_rate = byte_total / sample_seconds
    connection_rate = connection_total / sample_seconds
    syn_rate = syn_total / sample_seconds
    ack_rate = ack_total / sample_seconds
    udp_rate = udp_total / sample_seconds
    icmp_rate = icmp_total / sample_seconds
    http_rate = http_total / sample_seconds
    partial_connection_rate = partial_connection_total / sample_seconds
    connection_burst_factor = connection_rate / max(flow_duration, 1.0)
    packet_size_variance = pvariance(packet_sizes) if len(packet_sizes) > 1 else 0.0
    return FeatureVector(
        packet_rate=packet_rate,
        byte_rate=byte_rate,
        connection_rate=connection_rate,
        syn_rate=syn_rate,
        ack_rate=ack_rate,
        udp_rate=udp_rate,
        icmp_rate=icmp_rate,
        entropy_score=_entropy(sources),
        source_ip_cardinality=len(sources),
        destination_port_distribution=tuple(sorted((int(port), count) for port, count in ports.items())),
        connection_burst_factor=connection_burst_factor,
        packet_size_variance=packet_size_variance,
        flow_duration=flow_duration,
        http_rate=http_rate,
        partial_connection_rate=partial_connection_rate,
    )
