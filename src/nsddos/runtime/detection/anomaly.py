"""Deterministic anomaly detection."""

from __future__ import annotations

from statistics import fmean

from nsddos.constants import SNAPSHOT_DIR
from nsddos.runtime.detection.models import AnomalyResult, FeatureVector
from nsddos.runtime.detection.thresholds import ANOMALY_THRESHOLDS, DEFAULT_BASELINES
from nsddos.runtime.persistence import read_json_checked
from nsddos.runtime.query.evidence import EVIDENCE_DIR


def _history_values() -> dict[str, list[float]]:
    values: dict[str, list[float]] = {
        "packet_rate": [],
        "byte_rate": [],
        "connection_rate": [],
        "latency": [],
        "flow_duration": [],
    }
    for path in sorted(SNAPSHOT_DIR.glob("snapshot-*.json"))[-5:]:
        try:
            payload = read_json_checked(path)
        except Exception:
            continue
        flow_state = payload.get("flow_state", {})
        telemetry_state = payload.get("telemetry_state", {})
        values["packet_rate"].append(float(flow_state.get("flow_count", 0)))
        values["byte_rate"].append(float(telemetry_state.get("active_flow_count", 0)) * 1024.0)
        values["connection_rate"].append(float(flow_state.get("flow_count", 0)))
        values["flow_duration"].append(30.0)
    for path in sorted(EVIDENCE_DIR.glob("*/evidence.json"))[-5:]:
        try:
            payload = read_json_checked(path)
        except Exception:
            continue
        flows = payload.get("flows", {})
        values["packet_rate"].append(float(flows.get("flow_count", 0)))
        values["connection_rate"].append(float(flows.get("flow_count", 0)))
    return values


def build_baseline() -> tuple[dict[str, float], str]:
    """Build deterministic baseline from persisted artifacts when possible."""
    history = _history_values()
    baseline = dict(DEFAULT_BASELINES)
    source = "fallback"
    if any(history.values()):
        source = "history"
        for key, default in DEFAULT_BASELINES.items():
            series = [value for value in history.get(key, []) if value > 0]
            if series:
                baseline[key] = fmean(series)
    return baseline, source


def detect_anomalies(features: FeatureVector, baseline: dict[str, float]) -> tuple[AnomalyResult, ...]:
    """Compute anomaly results from baseline thresholds."""
    checks = (
        ("packet_anomaly", features.packet_rate, baseline["packet_rate"]),
        ("connection_anomaly", features.connection_rate, baseline["connection_rate"]),
        ("bandwidth_anomaly", features.byte_rate, baseline["byte_rate"]),
        ("latency_anomaly", max(features.flow_duration, 0.0), baseline["latency"]),
        ("flow_anomaly", max(features.connection_burst_factor, 0.0), baseline["flow_duration"]),
    )
    anomalies = []
    for name, current, base in checks:
        threshold = ANOMALY_THRESHOLDS[name]
        triggered = current > base * threshold
        score = min((current / max(base * threshold, 1.0)), 2.0) if triggered else 0.0
        anomalies.append(
            AnomalyResult(
                name=name,
                triggered=triggered,
                current=current,
                baseline=base,
                threshold=threshold,
                score=score,
            )
        )
    return tuple(anomalies)
