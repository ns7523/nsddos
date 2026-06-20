"""Evidence view model builder."""

from __future__ import annotations

from nsddos.ui.models import UiPagePayload


def build_evidence_payload(data: dict) -> UiPagePayload:
    payload = data.get("payload", {})
    items = sorted(payload.get("items", []), key=lambda item: str(item.get("id", "")))
    return UiPagePayload(
        name="evidence",
        title="Evidence Explorer",
        items=items,
        summary={"total": payload.get("total", 0), "lineage": True, "replay_safe": payload.get("replay_safe", True)},
        timings={"api_ms": float(data.get("duration_ms", 0.0))},
    )
