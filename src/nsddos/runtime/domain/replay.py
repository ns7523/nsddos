"""Typed replay entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic

from nsddos.runtime.domain.base import DomainModel
from nsddos.runtime.performance import record_timing


@dataclass(frozen=True)
class RuntimeReplay(DomainModel):
    replay_id: str = ""
    event_type: str = ""
    timestamp: str = ""
    status: str = ""
    message: str = ""


@dataclass(frozen=True)
class RuntimeReplayCollection(DomainModel):
    events: tuple[RuntimeReplay, ...] = field(default_factory=tuple)


def reconstruct_replay(events: list[dict]) -> RuntimeReplayCollection:
    start = monotonic()
    typed = tuple(
        RuntimeReplay(
            replay_id=str(item.get("replay_id", "")),
            event_type=str(item.get("event_type", "")),
            timestamp=str(item.get("timestamp", "")),
            status=str(item.get("status", "")),
            message=str(item.get("message", "")),
        )
        for item in sorted(
            events,
            key=lambda row: (
                str(row.get("timestamp", "")),
                str(row.get("event_type", "")),
            ),
        )
    )
    record_timing("domain.replay.reconstruct", (monotonic() - start) * 1000)
    return RuntimeReplayCollection(events=typed)


def validate_replay_compatibility(replay: RuntimeReplayCollection) -> list[str]:
    errors: list[str] = []
    for item in replay.events:
        if not item.replay_id:
            errors.append("missing_replay_id")
        if not item.timestamp:
            errors.append("missing_timestamp")
    return errors
