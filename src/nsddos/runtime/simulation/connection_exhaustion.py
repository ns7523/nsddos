"""Connection exhaustion profile."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import AttackGeneratorProfile


def build_connection_exhaustion_profile(
    intensity_level: str, duration_seconds: int
) -> AttackGeneratorProfile:
    packet_rate = {"low": 200.0, "medium": 500.0, "high": 1000.0}[intensity_level]
    source_pool = tuple(f"10.0.6.{index}" for index in range(1, 11))
    return AttackGeneratorProfile(
        "connection_exhaustion",
        "tcp",
        packet_rate,
        packet_rate * 72.0,
        packet_rate * 0.9,
        duration_seconds,
        source_pool,
        (22, 80, 443),
        intensity_level,
        "exponential_ramp_up",
        72,
    )
