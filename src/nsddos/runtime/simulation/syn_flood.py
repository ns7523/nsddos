"""SYN flood profile."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import AttackGeneratorProfile


def build_syn_flood_profile(intensity_level: str, duration_seconds: int) -> AttackGeneratorProfile:
    packet_rate = {"low": 400.0, "medium": 1200.0, "high": 2400.0}[intensity_level]
    source_pool = tuple(f"10.0.1.{index}" for index in range(1, 17))
    return AttackGeneratorProfile("syn_flood", "tcp", packet_rate, packet_rate * 64.0, packet_rate / 3.0, duration_seconds, source_pool, (80, 443), intensity_level, "burst", 64)
