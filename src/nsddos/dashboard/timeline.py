"""Dashboard timeline construction."""

from __future__ import annotations

from nsddos.dashboard.contracts import DashboardSourceBundle, TimelineEvent


def build_timeline(sources: DashboardSourceBundle) -> tuple[TimelineEvent, ...]:
    """Build deterministic chronological events."""
    events: list[TimelineEvent] = []
    detection = sources.detection
    if detection.get("telemetry_timestamp"):
        events.append(
            TimelineEvent(
                event_id="event-detection",
                event_type="attack_detection",
                severity=str(detection.get("risk_level", "LOW")).lower(),
                detail=str(detection.get("attack_type", "normal")),
                timestamp=str(detection.get("telemetry_timestamp", "")),
            )
        )
    mitigation = sources.mitigation
    if mitigation.get("mitigation_generation"):
        events.append(
            TimelineEvent(
                event_id="event-mitigation",
                event_type="mitigation",
                severity=str(mitigation.get("risk_level", "LOW")).lower(),
                detail=str(mitigation.get("mitigation_action", "alert_only")),
                timestamp=str(mitigation.get("created_at", mitigation.get("timestamp", ""))),
            )
        )
    for index, item in enumerate(sources.policy_history[:10]):
        events.append(
            TimelineEvent(
                event_id=f"event-policy-{index}",
                event_type="policy_change",
                severity="warning" if int(item.get("escalation_level", 0)) > 0 else "info",
                detail=str(item.get("recommended_action", "alert_only")),
                timestamp=str(item.get("timestamp", "")),
            )
        )
    if sources.ml.get("timestamp"):
        events.append(
            TimelineEvent(
                event_id="event-ml",
                event_type="ml_retraining" if sources.ml.get("retraining_required", False) else "ml_inference",
                severity="warning" if sources.ml.get("retraining_required", False) else "info",
                detail=str(sources.ml.get("model_version", "")),
                timestamp=str(sources.ml.get("timestamp", "")),
            )
        )
    return tuple(sorted(events, key=lambda item: (item.timestamp, item.event_id)))
