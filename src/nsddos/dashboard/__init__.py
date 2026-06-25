"""Read-only security analytics dashboard subsystem."""

from nsddos.dashboard.registry import (
    latest_alerts_payload,
    latest_dashboard_evaluation,
    latest_diagnostics_payload,
    latest_history_payload,
    latest_reports_payload,
)
from nsddos.dashboard.server import (
    dashboard_alerts,
    dashboard_diagnostics,
    dashboard_report,
    generate_dashboard_state,
)
from nsddos.dashboard.validation import validate_dashboard_evaluation

__all__ = [
    "generate_dashboard_state",
    "dashboard_alerts",
    "dashboard_report",
    "dashboard_diagnostics",
    "latest_dashboard_evaluation",
    "latest_alerts_payload",
    "latest_reports_payload",
    "latest_diagnostics_payload",
    "latest_history_payload",
    "validate_dashboard_evaluation",
]
