"""Graph freshness checks."""

from __future__ import annotations

from nsddos.runtime.freshness.engine import evaluate_freshness


def validate_graph_freshness(payload: dict[str, object]) -> dict[str, object]:
    evaluation = evaluate_freshness("graph", payload)
    return {
        "validity_state": evaluation.freshness.validity_state,
        "freshness_status": evaluation.freshness.freshness_status,
        "consistency_generation": evaluation.freshness.consistency_generation,
    }
