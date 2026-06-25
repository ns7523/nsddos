"""Deterministic simulation patterns."""

from __future__ import annotations


def _count(packet_rate: float, duration_seconds: int) -> int:
    return max(1, int(packet_rate * duration_seconds))


def burst_pattern(packet_rate: float, duration_seconds: int) -> tuple[int, ...]:
    total = _count(packet_rate, duration_seconds)
    return tuple(
        0 if index < max(1, total // 4) else int((index - total // 4) * 2)
        for index in range(total)
    )


def sustained_pattern(packet_rate: float, duration_seconds: int) -> tuple[int, ...]:
    total = _count(packet_rate, duration_seconds)
    interval_ms = max(1, int((duration_seconds * 1000) / total))
    return tuple(index * interval_ms for index in range(total))


def exponential_ramp_up_pattern(
    packet_rate: float, duration_seconds: int
) -> tuple[int, ...]:
    total = _count(packet_rate, duration_seconds)
    return tuple(
        int((index * index) / max(total, 1) * (duration_seconds * 10))
        for index in range(total)
    )


def random_burst_pattern(packet_rate: float, duration_seconds: int) -> tuple[int, ...]:
    total = _count(packet_rate, duration_seconds)
    return tuple(((index * 37) % max(total, 1)) * 3 for index in range(total))


def wave_attack_pattern(packet_rate: float, duration_seconds: int) -> tuple[int, ...]:
    total = _count(packet_rate, duration_seconds)
    half = max(1, total // 2)
    leading = [index * 2 for index in range(half)]
    trailing = [leading[-1] + (index * 4) for index in range(total - half)]
    return tuple(leading + trailing)
