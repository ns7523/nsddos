"""Dispatch streaming aggregates into runtime engines."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.detection import evaluate_detection
from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.ml import evaluate_ml_detection
from nsddos.runtime.ml.models import MLDetectionEvaluation
from nsddos.runtime.mitigation import enforce_mitigation, evaluate_mitigation
from nsddos.runtime.mitigation.models import MitigationEvaluation
from nsddos.runtime.policy import evaluate_dynamic_policy
from nsddos.runtime.policy.contracts_models import PolicyEvaluation
from nsddos.runtime.streaming.contracts import StreamAggregation, StreamEvent


def build_detection_telemetry(aggregation: StreamAggregation, events: tuple[StreamEvent, ...]) -> dict[str, Any]:
    timestamp = events[-1].timestamp.isoformat() if events else datetime.now(timezone.utc).isoformat()
    flows = [
        {
            "source_ip": item.source_ip,
            "source": item.source_ip,
            "destination_ip": item.destination_ip,
            "protocol": item.protocol,
            "destination_port": item.destination_port,
            "packets": item.packet_rate,
            "bytes": item.byte_rate,
            "connections": item.connection_rate,
            "duration": item.duration_seconds,
            "flags": item.flags,
            "http_rate": float(item.metadata.get("http_rate", 0.0)),
            "partial_connection_rate": float(item.metadata.get("partial_connection_rate", 0.0)),
        }
        for item in events
    ]
    stale = any(item.freshness_state in {"stale", "expired"} for item in events)
    return {
        "provider_source": f"streaming:{events[0].source_type}" if events else "streaming:unknown",
        "timestamp": timestamp,
        "sample_window_seconds": 1.0,
        "flows": flows,
        "flow_state": {
            "collector_reachable": True,
            "telemetry_present": bool(events),
            "flow_count": len(events),
            "detail": f"streamed_events={len(events)}",
        },
        "telemetry_state": {
            "collector_reachable": True,
            "flow_api_ready": True,
            "metrics_available": True,
            "topology_published": True,
            "active_flow_count": len(events),
            "last_flow_timestamp": timestamp,
            "stale": stale,
        },
        "freshness_state": {
            "last_flow_timestamp": timestamp,
            "sample_interval_seconds": 1.0,
            "stale": stale,
            "detail": f"stream_state={events[0].source_type}" if events else "stream_state=empty",
        },
        "replay_mode": any(item.freshness_state == "replay_only" for item in events),
        "stream_aggregation": aggregation.to_dict(),
    }


def dispatch_detection(config: dict[str, Any], aggregation: StreamAggregation, events: tuple[StreamEvent, ...]) -> tuple[DetectionEvaluation, dict[str, Any]]:
    telemetry = build_detection_telemetry(aggregation, events)
    evaluation = evaluate_detection(config, telemetry=telemetry, reference_at=telemetry["timestamp"])
    return evaluation, telemetry


def dispatch_mitigation(
    config: dict[str, Any],
    detection: DetectionEvaluation,
    policy: PolicyEvaluation,
    telemetry: dict[str, Any],
) -> MitigationEvaluation:
    evaluation = evaluate_mitigation(config, detection=detection, policy=policy, telemetry=telemetry, reference_at=telemetry["timestamp"])
    if not hasattr(evaluation, "mitigation_required") or not hasattr(evaluation, "controller_payload"):
        return evaluation
    if not evaluation.mitigation_required:
        return evaluation
    return enforce_mitigation(config, evaluation, telemetry=telemetry)


def dispatch_ml(
    config: dict[str, Any],
    detection: DetectionEvaluation,
    telemetry: dict[str, Any],
) -> MLDetectionEvaluation:
    return evaluate_ml_detection(config, detection=detection, telemetry=telemetry, reference_at=telemetry["timestamp"])


def dispatch_policy(
    config: dict[str, Any],
    detection: DetectionEvaluation,
    ml: MLDetectionEvaluation,
    telemetry: dict[str, Any],
) -> PolicyEvaluation:
    return evaluate_dynamic_policy(config, detection=detection, ml=ml, telemetry=telemetry, reference_at=telemetry["timestamp"])
