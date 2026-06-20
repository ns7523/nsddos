"""Deterministic simulation scheduling."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import PacketScheduleEntry


def build_schedule(
    pattern_offsets_ms: tuple[int, ...],
    *,
    start_delay_seconds: int,
    repeat_interval_seconds: int,
) -> tuple[PacketScheduleEntry, ...]:
    start_delay_ms = max(0, start_delay_seconds) * 1000
    repeat_offset_ms = max(0, repeat_interval_seconds) * 1000
    return tuple(
        PacketScheduleEntry(
            sequence_id=index,
            emit_at_ms=start_delay_ms + offset + repeat_offset_ms,
            repeat_index=0,
        )
        for index, offset in enumerate(pattern_offsets_ms)
    )
