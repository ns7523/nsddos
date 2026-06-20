"""Runtime temporal timeline reconstruction."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.domain.serialization import to_canonical_dict
from nsddos.runtime.domain.timeline import RuntimeTransition
from nsddos.runtime.events import load_runtime_events
from nsddos.runtime.models import TimelineEvent
from nsddos.runtime.transitions import load_transition_history


def build_runtime_history_timeline() -> list[TimelineEvent]:
    """Reconstruct deterministic runtime history timeline."""
    events = load_runtime_events()
    transitions = load_transition_history()
    timeline: list[TimelineEvent] = []

    for event in events:
        details = event.get("details", {}) or {}
        affected = []
        if isinstance(details, dict):
            affected = [f"{key}:{value}" for key, value in details.items()]
        timeline.append(
            TimelineEvent(
                timestamp=str(event.get("timestamp", "")),
                event_type=str(event.get("event_type", "")),
                affected_entities=affected,
                convergence_impact="warning" if event.get("status") in {"warning", "stale"} else str(event.get("status", "none")),
                drift_impact="none",
                topology_impact="none",
                detail=str(event.get("message", "")),
            )
        )

    for item in transitions:
        conv = item.get("convergence", {})
        drift = item.get("drift", {})
        topo = item.get("topology", {})
        runtime = item.get("runtime", {})
        timeline.append(
            TimelineEvent(
                timestamp=str(conv.get("timestamp", "")),
                event_type="snapshot.transition",
                affected_entities=list(runtime.get("affected_entities", [])),
                convergence_impact=f"{conv.get('from_state')}->{conv.get('to_state')}",
                drift_impact=f"+{len(drift.get('introduced', []))}/-{len(drift.get('recovered', []))}",
                topology_impact="changed" if topo.get("changed") else "stable",
                detail=str(runtime.get("detail", "")),
            )
        )

    timeline.sort(key=lambda item: item.timestamp)
    return timeline


def timeline_summary(timeline: list[TimelineEvent] | None = None) -> dict[str, Any]:
    """Summarize timeline."""
    items = timeline or build_runtime_history_timeline()
    instability = [item for item in items if "warning" in item.convergence_impact or "diverged" in item.convergence_impact]
    return {
        "events": len(items),
        "instability_events": len(instability),
        "first_timestamp": items[0].timestamp if items else "",
        "last_timestamp": items[-1].timestamp if items else "",
    }


def typed_timeline_transitions() -> list[dict[str, Any]]:
    """Return typed transition entities."""
    typed: list[dict[str, Any]] = []
    for item in build_runtime_history_timeline():
        transition = RuntimeTransition(
            transition_id=deterministic_id("transition", f"{item.timestamp}:{item.event_type}:{item.detail}"),
            event_type=item.event_type,
            timestamp=item.timestamp,
            affected_entities=tuple(item.affected_entities),
            detail=item.detail,
        )
        typed.append(to_canonical_dict(transition))
    typed.sort(key=lambda row: (str(row.get("timestamp", "")), str(row.get("transition_id", ""))))
    return typed
