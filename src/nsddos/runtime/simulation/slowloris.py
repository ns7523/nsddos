"""Slowloris profile."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import AttackGeneratorProfile


def build_slowloris_profile(intensity_level: str, duration_seconds: int) -> AttackGeneratorProfile:
    packet_rate = {"low": 30.0, "medium": 80.0, "high": 160.0}[intensity_level]
    source_pool = tuple(f"10.0.5.{index}" for index in range(1, 5))
    return AttackGeneratorProfile("slowloris", "tcp", packet_rate, packet_rate * 96.0, packet_rate * 1.5, duration_seconds, source_pool, (80,), intensity_level, "sustained", 96)
