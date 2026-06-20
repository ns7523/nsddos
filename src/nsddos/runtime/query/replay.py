"""Runtime replay querying."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.query.models import RuntimeQuery
from nsddos.runtime.replay import replay_execution_history
from nsddos.runtime.verification.replay import replay_verification_runs


def query_replay(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query orchestration and verification replay."""
    execution = replay_execution_history()
    verification = replay_verification_runs()
    items = [
        {"id": "execution", "kind": "execution", **execution},
        {"id": "verification", "kind": "verification", **verification},
    ]
    transitions = list(verification.get("transitions", []))
    return {"items": items, "transitions": transitions}
