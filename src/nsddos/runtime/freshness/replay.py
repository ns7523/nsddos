"""Replay freshness checks."""

from __future__ import annotations

from nsddos.runtime.freshness.engine import evaluate_freshness


def validate_replay_freshness(payload: dict[str, object]) -> dict[str, object]:
    evaluation = evaluate_freshness("replay", payload)
    return {
        "validity_state": evaluation.freshness.validity_state,
        "replay_validity": evaluation.freshness.replay_validity,
        "consistency_generation": evaluation.freshness.consistency_generation,
    }
