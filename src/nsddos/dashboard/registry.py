"""Dashboard registry lookups."""

from __future__ import annotations

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import read_json_checked

DASHBOARD_DIR = RUNTIME_DIR / "dashboard"


def latest_dashboard_evaluation() -> dict:
    """Load latest dashboard evaluation."""
    path = DASHBOARD_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def latest_alerts_payload() -> dict:
    """Load latest dashboard alerts."""
    path = DASHBOARD_DIR / "alerts.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def latest_reports_payload() -> dict:
    """Load latest dashboard reports."""
    path = DASHBOARD_DIR / "reports.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def latest_diagnostics_payload() -> dict:
    """Load latest dashboard diagnostics."""
    path = DASHBOARD_DIR / "diagnostics.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def latest_history_payload() -> dict:
    """Load latest dashboard history."""
    path = DASHBOARD_DIR / "history.json"
    if not path.exists():
        return {}
    return read_json_checked(path)
