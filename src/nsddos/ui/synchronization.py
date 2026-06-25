"""UI synchronization metadata."""

from __future__ import annotations

from time import monotonic
from typing import Any

from nsddos.runtime.performance import record_timing


def deterministic_poll(
    payload: dict[str, Any], poll_interval_seconds: int = 5
) -> dict[str, Any]:
    start = monotonic()
    ordered_items = sorted(
        payload.get("items", []), key=lambda item: str(item.get("id", ""))
    )
    sync = {
        "poll_interval_seconds": poll_interval_seconds,
        "stable_ordering": True,
        "replay_safe_updates": True,
        "item_count": len(ordered_items),
        "items": ordered_items,
    }
    record_timing("ui.synchronization", (monotonic() - start) * 1000)
    return sync
