"""Mitigation query adapter."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.mitigation import evaluate_mitigation
from nsddos.runtime.query.models import RuntimeQuery


def query_mitigation(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    evaluation = evaluate_mitigation(config)
    payload = evaluation.to_dict()
    return {
        "items": [
            {
                "id": "mitigation",
                "type": "mitigation",
                "mitigation_required": payload["mitigation_required"],
                "mitigation_action": payload["mitigation_action"],
                "target_ip": payload["target_ip"],
                "target_subnet": payload.get("target_subnet", ""),
                "confidence_score": payload["confidence_score"],
                "mitigation_status": payload["mitigation_status"],
                "execution_result": payload["execution_result"],
                "controller_mutation_status": payload.get("controller_mutation_status", "not_attempted"),
                "ovs_insertion_status": payload.get("ovs_insertion_status", "not_attempted"),
                "flow_verification_status": payload.get("flow_verification_status", "not_attempted"),
                "traffic_block_status": payload.get("traffic_block_status", "not_attempted"),
                "mitigation_hash": payload["mitigation_hash"],
                "mitigation_generation": payload["mitigation_generation"],
                "attack_type": payload["attack_type"],
                "risk_level": payload["risk_level"],
                "timestamp": payload["timestamp"],
            }
        ],
        "evaluation": payload,
    }
