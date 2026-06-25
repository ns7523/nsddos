"""Deterministic stream windows."""

from __future__ import annotations

from datetime import timedelta

from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.streaming.contracts import (
    StreamEvent,
    StreamWindow,
    StreamWindowState,
)


def build_window_state(
    events: tuple[StreamEvent, ...],
    *,
    window_kind: str,
    window_seconds: int,
) -> StreamWindowState:
    if not events:
        return StreamWindowState(
            window_kind=window_kind,
            window_seconds=window_seconds,
            windows=(),
            active_events=0,
        )
    ordered = tuple(
        sorted(
            events,
            key=lambda item: (
                item.timestamp.isoformat(),
                item.sequence_number,
                item.event_id,
            ),
        )
    )
    if window_kind == "tumbling":
        windows = []
        current = []
        current_start = ordered[0].timestamp
        for item in ordered:
            if (
                item.timestamp - current_start
            ).total_seconds() >= window_seconds and current:
                start = current[0].timestamp
                end = current[-1].timestamp
                windows.append(
                    StreamWindow(
                        window_id=deterministic_id(
                            "stream-window",
                            f"tumbling:{start.isoformat()}:{len(current)}",
                        ),
                        start_timestamp=start.isoformat(),
                        end_timestamp=end.isoformat(),
                        events=tuple(current),
                    )
                )
                current = []
                current_start = item.timestamp
            current.append(item)
        if current:
            start = current[0].timestamp
            end = current[-1].timestamp
            windows.append(
                StreamWindow(
                    window_id=deterministic_id(
                        "stream-window", f"tumbling:{start.isoformat()}:{len(current)}"
                    ),
                    start_timestamp=start.isoformat(),
                    end_timestamp=end.isoformat(),
                    events=tuple(current),
                )
            )
        return StreamWindowState(
            window_kind=window_kind,
            window_seconds=window_seconds,
            windows=tuple(windows),
            active_events=len(ordered),
        )
    if window_kind == "fixed_time":
        anchor = ordered[0].timestamp.replace(microsecond=0)
        windows = []
        for index, item in enumerate(ordered, start=1):
            end = anchor + timedelta(seconds=window_seconds)
            windows.append(
                StreamWindow(
                    window_id=deterministic_id(
                        "stream-window", f"fixed:{index}:{anchor.isoformat()}"
                    ),
                    start_timestamp=anchor.isoformat(),
                    end_timestamp=end.isoformat(),
                    events=(item,),
                )
            )
        return StreamWindowState(
            window_kind=window_kind,
            window_seconds=window_seconds,
            windows=tuple(windows),
            active_events=len(ordered),
        )
    windows = []
    for index, item in enumerate(ordered, start=1):
        start = item.timestamp - timedelta(seconds=window_seconds)
        windows.append(
            StreamWindow(
                window_id=deterministic_id(
                    "stream-window", f"sliding:{index}:{item.timestamp.isoformat()}"
                ),
                start_timestamp=start.isoformat(),
                end_timestamp=item.timestamp.isoformat(),
                events=tuple(
                    candidate
                    for candidate in ordered
                    if start <= candidate.timestamp <= item.timestamp
                ),
            )
        )
    return StreamWindowState(
        window_kind=window_kind,
        window_seconds=window_seconds,
        windows=tuple(windows),
        active_events=len(ordered),
    )
