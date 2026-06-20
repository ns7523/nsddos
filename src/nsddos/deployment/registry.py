"""Deployment registry lookups."""

from __future__ import annotations

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import read_json_checked

DEPLOYMENT_DIR = RUNTIME_DIR / "deployment"


def latest_deployment_payload() -> dict:
    """Load latest deployment payload."""
    path = DEPLOYMENT_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def latest_diagnostics_payload() -> dict:
    """Load latest deployment diagnostics payload."""
    path = DEPLOYMENT_DIR / "diagnostics.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def latest_backup_payload() -> dict:
    """Load latest backup payload."""
    path = DEPLOYMENT_DIR / "backup.json"
    if not path.exists():
        return {}
    return read_json_checked(path)
