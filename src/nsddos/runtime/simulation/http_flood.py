"""HTTP flood profile."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import AttackGeneratorProfile


def build_http_flood_profile(
    intensity_level: str, duration_seconds: int
) -> AttackGeneratorProfile:
    packet_rate = {"low": 120.0, "medium": 300.0, "high": 600.0}[intensity_level]
    source_pool = tuple(f"10.0.4.{index}" for index in range(1, 7))
    return AttackGeneratorProfile(
        "http_flood",
        "tcp",
        packet_rate,
        packet_rate * 512.0,
        packet_rate / 8.0,
        duration_seconds,
        source_pool,
        (80, 8080),
        intensity_level,
        "random_burst",
        512,
    )
