"""Replay view model builder."""

from __future__ import annotations

from time import monotonic

from nsddos.runtime.performance import record_timing
from nsddos.ui.models import UiPagePayload


def build_replay_payload(data: dict) -> UiPagePayload:
    start = monotonic()
    payload = data.get("payload", {})
    ordered = sorted(payload.get("items", []), key=lambda item: str(item.get("id", "")))
    timings = {"api_ms": float(data.get("duration_ms", 0.0)), "replay_render_ms": (monotonic() - start) * 1000}
    record_timing("ui.replay.render", timings["replay_render_ms"])
    return UiPagePayload(
        name="replay",
        title="Replay Explorer",
        items=ordered,
        summary={"total": payload.get("total", 0), "replay_safe": payload.get("replay_safe", True)},
        timings=timings,
    )
