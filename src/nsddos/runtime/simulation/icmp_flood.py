"""ICMP flood profile."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import AttackGeneratorProfile


def build_icmp_flood_profile(
    intensity_level: str, duration_seconds: int
) -> AttackGeneratorProfile:
    packet_rate = {"low": 300.0, "medium": 900.0, "high": 1800.0}[intensity_level]
    source_pool = tuple(f"10.0.3.{index}" for index in range(1, 9))
    return AttackGeneratorProfile(
        "icmp_flood",
        "icmp",
        packet_rate,
        packet_rate * 84.0,
        packet_rate / 6.0,
        duration_seconds,
        source_pool,
        (0,),
        intensity_level,
        "sustained",
        84,
    )
