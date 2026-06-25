"""Replay-safe live telemetry buffering."""

from __future__ import annotations

from dataclasses import dataclass, field

from nsddos.runtime.providers.live.contracts import LiveTelemetrySnapshot


@dataclass
class TelemetryStreamBuffer:
    batch_size: int
    items: list[LiveTelemetrySnapshot] = field(default_factory=list)

    def push(
        self, snapshot: LiveTelemetrySnapshot
    ) -> tuple[LiveTelemetrySnapshot, ...]:
        self.items.append(snapshot)
        ordered = tuple(sorted(self.items, key=lambda item: item.timestamp.isoformat()))
        if len(ordered) >= self.batch_size:
            self.items = list(ordered[-self.batch_size :])
        else:
            self.items = list(ordered)
        return tuple(self.items)
