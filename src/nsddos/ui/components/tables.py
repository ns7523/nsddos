"""Common table renderer."""

from __future__ import annotations


def render_items_table(items: list[dict], limit: int = 25) -> str:
    rows = items[:limit]
    if not rows:
        return "<p>No data.</p>"
    keys = sorted({key for row in rows for key in row.keys()})
    priority = [
        "id",
        "type",
        "attack_type",
        "confidence_score",
        "risk_level",
        "detection_status",
        "evidence_hash",
        "classification_generation",
        "mitigation_required",
        "mitigation_action",
        "target_ip",
        "target_subnet",
        "mitigation_status",
        "execution_result",
        "mitigation_hash",
        "mitigation_generation",
        "provider_source",
        "attack_type",
        "target_ip",
        "packet_rate",
        "byte_rate",
        "duration_seconds",
        "intensity_level",
        "session_id",
        "stream_state",
        "queue_depth",
        "throughput",
        "dropped_events",
        "dashboard_id",
        "active_attacks",
        "active_alerts",
        "stream_throughput",
        "cluster_nodes",
        "ml_confidence",
        "mitigation_events",
        "policy_events",
        "dashboard_health",
        "model_id",
        "attack_probability",
        "predicted_attack_type",
        "anomaly_score",
        "drift_score",
        "false_positive_score",
        "retraining_required",
        "model_version",
        "policy_id",
        "recommended_action",
        "escalation_level",
        "threshold_score",
        "attack_frequency",
        "active_flows",
        "health_state",
        "controller_status",
        "timestamp",
        "validity_state",
        "freshness_status",
        "replay_validity",
        "consistency_generation",
        "observed_at",
        "synchronized_at",
    ]
    keys = [key for key in priority if key in keys] + [key for key in keys if key not in priority]
    header = "".join(f"<th>{key}</th>" for key in keys)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{row.get(key, '')}</td>" for key in keys) + "</tr>"
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"
