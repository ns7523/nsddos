"""Dashboard history persistence."""

from __future__ import annotations

from nsddos.constants import RUNTIME_DIR
from nsddos.dashboard.contracts import DashboardEvaluation
from nsddos.runtime.persistence import atomic_write_json, locked_persistence_scope, read_json_checked

DASHBOARD_DIR = RUNTIME_DIR / "dashboard"


def persist_dashboard_history(evaluation: DashboardEvaluation) -> None:
    """Persist latest and historical dashboard state."""
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    payload = evaluation.to_dict()
    stamp = evaluation.timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    with locked_persistence_scope(DASHBOARD_DIR) as lock_scope:
        atomic_write_json(DASHBOARD_DIR / f"dashboard-{stamp}.json", payload, lock_scope=lock_scope)
        atomic_write_json(DASHBOARD_DIR / "latest.json", payload, lock_scope=lock_scope)
        atomic_write_json(
            DASHBOARD_DIR / "history.json",
            {
                "attack_history": [item.to_dict() for item in evaluation.timeline if item.event_type == "attack_detection"],
                "mitigation_history": [item.to_dict() for item in evaluation.timeline if item.event_type == "mitigation"],
                "cluster_history": [item.to_dict() for item in evaluation.timeline if item.event_type in {"policy_change", "ml_retraining", "ml_inference"}],
            },
            lock_scope=lock_scope,
        )
        atomic_write_json(DASHBOARD_DIR / "alerts.json", {"alerts": [item.to_dict() for item in evaluation.alerts]}, lock_scope=lock_scope)
        atomic_write_json(DASHBOARD_DIR / "reports.json", {"reports": [item.to_dict() for item in evaluation.reports]}, lock_scope=lock_scope)
        atomic_write_json(DASHBOARD_DIR / "diagnostics.json", evaluation.diagnostics.to_dict(), lock_scope=lock_scope)


def latest_history_payload() -> dict:
    """Load latest dashboard history payload."""
    path = DASHBOARD_DIR / "history.json"
    if not path.exists():
        return {}
    return read_json_checked(path)
