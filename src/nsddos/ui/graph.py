"""Graph view model builder."""

from __future__ import annotations

from time import monotonic

from nsddos.runtime.performance import record_timing
from nsddos.ui.models import UiPagePayload


def build_graph_payload(data: dict) -> UiPagePayload:
    start = monotonic()
    payload = data.get("payload", {})
    items = sorted(payload.get("items", []), key=lambda item: (str(item.get("type", "")), str(item.get("id", ""))))
    timings = {"api_ms": float(data.get("duration_ms", 0.0)), "graph_render_ms": (monotonic() - start) * 1000}
    record_timing("ui.graph.render", timings["graph_render_ms"])
    return UiPagePayload(
        name="graph",
        title="Runtime Graph",
        items=items,
        summary={"total": payload.get("total", 0), "replay_safe": payload.get("replay_safe", True)},
        timings=timings,
    )
