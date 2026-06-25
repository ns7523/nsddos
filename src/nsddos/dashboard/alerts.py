"""Dashboard alerts."""

from __future__ import annotations

from nsddos.dashboard.contracts import (
    AlertRecord,
    AttackState,
    DashboardSourceBundle,
    MLMetricsState,
)


def build_alerts(
    sources: DashboardSourceBundle,
    attacks: AttackState,
    ml_metrics: MLMetricsState,
) -> tuple[AlertRecord, ...]:
    """Generate deterministic alerts."""
    alerts: list[AlertRecord] = []
    timestamp = str(
        sources.detection.get("telemetry_timestamp")
        or sources.ml.get("timestamp")
        or sources.distributed.get("timestamp")
        or ""
    )
    if attacks.active_attacks:
        level = (
            "critical"
            if str(sources.detection.get("risk_level", "LOW")) in {"HIGH", "CRITICAL"}
            else "warning"
        )
        alerts.append(
            AlertRecord(
                "alert-attack",
                level,
                "attack_threshold",
                f"active_attacks={attacks.active_attacks}",
                "detection",
                timestamp,
            )
        )
    if str(sources.distributed.get("cluster_health", "healthy")) != "healthy":
        alerts.append(
            AlertRecord(
                "alert-cluster",
                "warning",
                "cluster_failure",
                str(sources.distributed.get("cluster_health", "degraded")),
                "distributed",
                str(sources.distributed.get("timestamp", timestamp)),
            )
        )
    if float(sources.ml.get("drift_score", 0.0)) >= 0.3:
        alerts.append(
            AlertRecord(
                "alert-ml-drift",
                "warning",
                "ml_drift",
                f"drift_score={ml_metrics.drift_trend[0]:.4f}",
                "ml",
                str(sources.ml.get("timestamp", timestamp)),
            )
        )
    if str(sources.mitigation.get("execution_result", "")) not in {
        "",
        "alert_only",
        "controller_payload_generated",
        "controller_rule_enforced",
        "flow_rule_verified",
        "traffic_blocked_verified",
        "traffic_probe_unavailable",
    }:
        alerts.append(
            AlertRecord(
                "alert-mitigation",
                "critical",
                "mitigation_failure",
                str(sources.mitigation.get("execution_result", "")),
                "mitigation",
                str(sources.mitigation.get("timestamp", timestamp)),
            )
        )
    provider_outage = any(
        result.get("status") in {"fail", "warn"}
        and result.get("category") in {"live", "telemetry"}
        for result in sources.verification
    )
    if provider_outage:
        alerts.append(
            AlertRecord(
                "alert-provider",
                "warning",
                "provider_outage",
                "provider visibility degraded",
                "verification",
                timestamp,
            )
        )
    return tuple(alerts)
