"""Dynamic policy query adapters."""

from __future__ import annotations

from nsddos.runtime.policy import (
    evaluate_dynamic_policy,
    latest_history_payload,
    latest_policy_evaluation,
    latest_rollback_payload,
)


def query_policy_evaluate(config: dict, query) -> dict[str, object]:
    payload = latest_policy_evaluation()
    if not payload:
        payload = evaluate_dynamic_policy(config).to_dict()
    return {
        "items": [
            {
                "id": payload.get("policy_id", "policy"),
                "type": "policy",
                "policy_id": payload.get("policy_id", ""),
                "recommended_action": payload.get("recommended_action", "alert_only"),
                "escalation_level": payload.get("escalation_level", 0),
                "threshold_score": payload.get("threshold_score", 0.0),
                "attack_frequency": payload.get("attack_frequency", 0),
                "timestamp": payload.get("timestamp", ""),
            }
        ],
        "evaluation": payload,
    }


def query_policy_history(config: dict, query) -> dict[str, object]:
    payload = latest_history_payload()
    items = []
    for index, item in enumerate(payload.get("entries", []), start=1):
        items.append(
            {
                "id": item.get("policy_id", f"policy-history:{index}"),
                "type": "policy_history",
                "attack_type": item.get("attack_type", ""),
                "source_ip": item.get("source_ip", ""),
                "recommended_action": item.get("recommended_action", "alert_only"),
                "escalation_level": item.get("escalation_level", 0),
                "timestamp": item.get("timestamp", ""),
            }
        )
    return {"items": items}


def query_policy_diagnostics(config: dict, query) -> dict[str, object]:
    payload = latest_policy_evaluation()
    if not payload:
        payload = evaluate_dynamic_policy(config).to_dict()
    diagnostics = payload.get("diagnostics", {})
    return {
        "items": [
            {
                "id": "policy-diagnostics",
                "type": "policy_diagnostics",
                "decision_latency_ms": diagnostics.get("decision_latency_ms", 0.0),
                "conflict_count": diagnostics.get("conflict_count", 0),
                "escalation_level": diagnostics.get("escalation_level", 0),
                "rollback_ready": diagnostics.get("rollback_ready", False),
                "threshold_drift": diagnostics.get("threshold_drift", 0.0),
                "timestamp": payload.get("timestamp", ""),
            }
        ]
    }


def query_policy_rollback(config: dict, query) -> dict[str, object]:
    payload = latest_rollback_payload()
    if not payload:
        return {"items": []}
    return {
        "items": [
            {
                "id": payload.get("rollback_id", ""),
                "type": "policy_rollback",
                "restored_policy_id": payload.get("restored_policy_id", ""),
                "restored_action": payload.get("restored_action", "alert_only"),
                "restored_escalation_level": payload.get(
                    "restored_escalation_level", 0
                ),
                "restored": payload.get("restored", False),
                "timestamp": payload.get("timestamp", ""),
            }
        ]
    }
