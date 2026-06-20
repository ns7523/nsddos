"""Verification view model builder."""

from __future__ import annotations

from collections import Counter

from nsddos.ui.models import UiPagePayload


def build_verification_payload(data: dict) -> UiPagePayload:
    payload = data.get("payload", {})
    items = sorted(payload.get("items", []), key=lambda item: (str(item.get("category", "")), str(item.get("id", ""))))
    counts = Counter(str(item.get("category", "unknown")) for item in items)
    return UiPagePayload(
        name="verification",
        title="Verification State",
        items=items,
        summary={"total": payload.get("total", 0), "categories": dict(counts), "replay_safe": payload.get("replay_safe", True)},
        timings={"api_ms": float(data.get("duration_ms", 0.0))},
    )
