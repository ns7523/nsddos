"""Service synchronization layer."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from nsddos.runtime.performance import record_timing
from nsddos.runtime.query.engine import explain_query_system
from nsddos.runtime.verification.replay import replay_verification_runs
from nsddos.service.persistence import load_synchronization, save_synchronization


def _checksum(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def synchronize_service(
    runtime_state: dict[str, Any], evidence_state: dict[str, Any]
) -> dict[str, Any]:
    start = monotonic()
    query = explain_query_system()
    verification_replay = replay_verification_runs()
    runtime_checksum = _checksum(runtime_state)
    query_checksum = _checksum(query)
    evidence_checksum = _checksum(
        {"verification_replay": verification_replay, "evidence": evidence_state}
    )
    synchronized_at = datetime.now(timezone.utc).isoformat()
    state = {
        "state": "synchronized",
        "runtime_checksum": runtime_checksum,
        "query_checksum": query_checksum,
        "evidence_checksum": evidence_checksum,
        "synchronized_at": synchronized_at,
    }
    existing = load_synchronization()
    history = existing.get("history", [])
    history.append(state)
    save_synchronization(
        {"state": state["state"], "history": history[-200:], "latest": state}
    )
    record_timing("service.synchronization", (monotonic() - start) * 1000)
    return state
