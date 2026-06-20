"""Evidence freshness checks."""

from __future__ import annotations

from nsddos.runtime.freshness.engine import evaluate_freshness


def validate_evidence_freshness(payload: dict[str, object]) -> dict[str, object]:
    evaluation = evaluate_freshness("evidence", payload)
    return {
        "validity_state": evaluation.freshness.validity_state,
        "freshness_status": evaluation.freshness.freshness_status,
    }
