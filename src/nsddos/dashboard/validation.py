"""Dashboard validation."""

from __future__ import annotations

from nsddos.dashboard.contracts import (
    ALERT_LEVELS,
    DASHBOARD_HEALTH_STATES,
    DashboardEvaluation,
)


def validate_dashboard_evaluation(evaluation: DashboardEvaluation) -> list[str]:
    """Validate dashboard state."""
    errors: list[str] = []
    if evaluation.dashboard_health not in DASHBOARD_HEALTH_STATES:
        errors.append("dashboard_corruption")
    if evaluation.active_attacks < 0 or evaluation.active_alerts < 0:
        errors.append("invalid_dashboard_counts")
    if any(alert.level not in ALERT_LEVELS for alert in evaluation.alerts):
        errors.append("alert_corruption")
    if any(not chart.points for chart in evaluation.visualizations):
        errors.append("invalid_visualization_payload")
    if any(not report.report_id or not report.summary for report in evaluation.reports):
        errors.append("report_corruption")
    if any(
        "stale" in warning and not warning
        for warning in evaluation.diagnostics.stale_telemetry_warnings
    ):
        errors.append("stale_dashboard_telemetry")
    if not evaluation.timeline and evaluation.active_attacks:
        errors.append("historical_dashboard_corruption")
    return errors
