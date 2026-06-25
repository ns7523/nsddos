"""Streaming aggregation."""

from __future__ import annotations

from collections import defaultdict

from nsddos.runtime.streaming.contracts import (
    ProtocolAggregate,
    StreamAggregation,
    StreamEvent,
    StreamWindowState,
)


def aggregate_events(window_state: StreamWindowState) -> StreamAggregation:
    events: tuple[StreamEvent, ...]
    if window_state.windows:
        events = window_state.windows[-1].events
    else:
        events = ()
    packet_total = sum(item.packet_rate for item in events)
    byte_total = sum(item.byte_rate for item in events)
    connection_total = sum(item.connection_rate for item in events)
    grouped: dict[str, dict[str, float]] = defaultdict(
        lambda: {"count": 0, "packet_rate": 0.0, "byte_rate": 0.0}
    )
    for item in events:
        grouped[item.protocol]["count"] += 1
        grouped[item.protocol]["packet_rate"] += item.packet_rate
        grouped[item.protocol]["byte_rate"] += item.byte_rate
    breakdown = tuple(
        ProtocolAggregate(
            protocol=protocol,
            event_count=int(values["count"]),
            packet_rate=float(values["packet_rate"]),
            byte_rate=float(values["byte_rate"]),
        )
        for protocol, values in sorted(grouped.items())
    )
    attack_pattern = "normal"
    if any(item.protocol == "slowloris" for item in events):
        attack_pattern = "slowloris"
    elif any(item.protocol == "udp" for item in events):
        attack_pattern = "udp_flood"
    elif any(item.protocol == "icmp" for item in events):
        attack_pattern = "icmp_flood"
    elif any(item.protocol == "http" for item in events):
        attack_pattern = "http_flood"
    elif any(item.protocol == "tcp" for item in events):
        attack_pattern = "syn_flood"
    target_ip = events[0].destination_ip if events else ""
    return StreamAggregation(
        total_packet_rate=packet_total,
        total_byte_rate=byte_total,
        total_connection_rate=connection_total,
        event_count=len(events),
        protocol_breakdown=breakdown,
        attack_pattern=attack_pattern,
        target_ip=target_ip,
    )
