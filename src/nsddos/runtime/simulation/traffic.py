"""Deterministic packet metadata generation."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import (
    AttackGeneratorProfile,
    PacketMetadata,
    TargetSelection,
)


def generate_packet_metadata(
    profile: AttackGeneratorProfile,
    target: TargetSelection,
) -> tuple[PacketMetadata, ...]:
    total_packets = max(1, int(profile.packet_rate * profile.duration_seconds))
    source_pool = profile.source_ip_pool or ("10.0.0.254",)
    target_ports = target.target_ports or profile.target_ports or (80,)
    flags = {
        "syn_flood": "S",
        "udp_flood": "U",
        "icmp_flood": "I",
        "http_flood": "GET",
        "slowloris": "PARTIAL",
        "connection_exhaustion": "CONNECT",
    }.get(profile.attack_type, "")
    return tuple(
        PacketMetadata(
            sequence_id=index,
            protocol=profile.protocol,
            source_ip=source_pool[index % len(source_pool)],
            target_ip=target.target_ip,
            target_port=target_ports[index % len(target_ports)],
            size_bytes=profile.packet_size_bytes,
            flags=flags,
            payload_kind=profile.attack_type,
        )
        for index in range(total_packets)
    )
