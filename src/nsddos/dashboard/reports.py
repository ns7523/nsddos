"""Dashboard report generation."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.dashboard.contracts import (
    AlertRecord,
    AttackState,
    DashboardDiagnostics,
    DashboardReport,
    MLMetricsState,
    PolicyAnalytics,
)


def build_reports(
    attacks: AttackState,
    alerts: tuple[AlertRecord, ...],
    policy_analytics: PolicyAnalytics,
    ml_metrics: MLMetricsState,
    diagnostics: DashboardDiagnostics,
    cluster_nodes: int,
) -> tuple[DashboardReport, ...]:
    """Build deterministic report payloads."""
    timestamp = datetime.now(timezone.utc).isoformat()
    return (
        DashboardReport(
            "report-incident",
            "incident_report",
            f"active_attacks={attacks.active_attacks} active_alerts={len(alerts)}",
            (
                ("attack_summary", str(attacks.attack_types)),
                ("alert_summary", str(len(alerts))),
            ),
            timestamp,
        ),
        DashboardReport(
            "report-daily",
            "daily_security_report",
            f"policy_events={policy_analytics.policy_events} cluster_nodes={cluster_nodes}",
            (
                ("policy_events", str(policy_analytics.policy_events)),
                ("cluster_nodes", str(cluster_nodes)),
            ),
            timestamp,
        ),
        DashboardReport(
            "report-attack-summary",
            "attack_summary_report",
            f"attack_types={len(attacks.attack_types)} recurrence={attacks.attack_frequency_history}",
            (
                ("attack_types", str(attacks.attack_types)),
                ("severity", str(attacks.attack_severities)),
            ),
            timestamp,
        ),
        DashboardReport(
            "report-cluster-health",
            "cluster_health_report",
            f"ml_confidence={ml_metrics.ml_confidence:.4f}",
            (
                ("ml_confidence", f"{ml_metrics.ml_confidence:.4f}"),
                ("warnings", ",".join(diagnostics.missing_data_warnings) or "none"),
            ),
            timestamp,
        ),
    )
