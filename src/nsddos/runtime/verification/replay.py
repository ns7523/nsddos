"""Verification replay persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import atomic_write_json, read_json_checked

VERIFICATION_DIR = RUNTIME_DIR / "verification"


def persist_verification_execution(payload: dict[str, Any]) -> str:
    """Persist verification execution for replay."""
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = str(payload.get("run_id", "unknown")).replace("/", "_")
    path = VERIFICATION_DIR / f"verification-{stamp}-{run_id}.json"
    atomic_write_json(path, payload)
    return str(path)


def replay_verification_runs(limit: int = 10) -> dict[str, Any]:
    """Load recent verification executions."""
    files = sorted(VERIFICATION_DIR.glob("verification-*.json")) if VERIFICATION_DIR.exists() else []
    runs = [read_json_checked(path) for path in files[-limit:]]
    transitions = []
    for previous, current in zip(runs, runs[1:]):
        transitions.append(
            {
                "from": previous.get("severity", "unknown"),
                "to": current.get("severity", "unknown"),
                "from_run": previous.get("run_id", ""),
                "to_run": current.get("run_id", ""),
            }
        )
    repeated_failures: dict[str, int] = {}
    for run in runs:
        for result in run.get("results", []):
            if result.get("status") in {"fail", "stale"}:
                key = result.get("name", "unknown")
                repeated_failures[key] = repeated_failures.get(key, 0) + 1
    return {
        "run_count": len(runs),
        "runs": runs,
        "transitions": transitions,
        "repeated_failures": repeated_failures,
    }
