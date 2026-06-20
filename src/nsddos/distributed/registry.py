"""Distributed persistence registry."""

from __future__ import annotations

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import read_json_checked

DISTRIBUTED_DIR = RUNTIME_DIR / "distributed"


def latest_distributed_evaluation() -> dict:
    """Load latest distributed evaluation payload."""
    path = DISTRIBUTED_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def latest_registry_payload() -> dict:
    """Load latest distributed registry payload."""
    path = DISTRIBUTED_DIR / "registry.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def latest_diagnostics_payload() -> dict:
    """Load latest distributed diagnostics payload."""
    path = DISTRIBUTED_DIR / "diagnostics.json"
    if not path.exists():
        return {}
    return read_json_checked(path)
