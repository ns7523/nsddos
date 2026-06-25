"""Deterministic replay support."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import (
    PacketMetadata,
    PacketScheduleEntry,
    ReplayTrafficRecord,
)


def build_replay_records(
    packets: tuple[PacketMetadata, ...],
    schedule: tuple[PacketScheduleEntry, ...],
) -> tuple[ReplayTrafficRecord, ...]:
    schedule_by_id = {item.sequence_id: item.emit_at_ms for item in schedule}
    return tuple(
        ReplayTrafficRecord(
            sequence_id=item.sequence_id,
            preserved_timestamp_ms=schedule_by_id.get(item.sequence_id, 0),
            protocol=item.protocol,
            target_ip=item.target_ip,
            target_port=item.target_port,
        )
        for item in packets
    )
