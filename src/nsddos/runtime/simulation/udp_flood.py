"""UDP flood profile."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import AttackGeneratorProfile


def build_udp_flood_profile(
    intensity_level: str, duration_seconds: int
) -> AttackGeneratorProfile:
    packet_rate = {"low": 600.0, "medium": 1500.0, "high": 3000.0}[intensity_level]
    source_pool = tuple(f"10.0.2.{index}" for index in range(1, 13))
    return AttackGeneratorProfile(
        "udp_flood",
        "udp",
        packet_rate,
        packet_rate * 128.0,
        packet_rate / 4.0,
        duration_seconds,
        source_pool,
        (53, 123, 8080),
        intensity_level,
        "wave_attack",
        128,
    )
