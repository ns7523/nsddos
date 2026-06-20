"""Mitigation evidence generation."""

from __future__ import annotations

import hashlib

from nsddos.runtime.domain.serialization import to_canonical_json
from nsddos.runtime.mitigation.models import MitigationActionPayload, MitigationControllerPayload, MitigationEvidence, MitigationPolicyDecision, MitigationStrategySelection


def build_mitigation_evidence(
    *,
    action: MitigationActionPayload,
    policy: MitigationPolicyDecision,
    strategy: MitigationStrategySelection,
    controller_payload: MitigationControllerPayload | None,
    confidence_score: float,
    attack_type: str,
    risk_level: str,
    detection_evidence_hash: str,
    timestamp: str,
) -> MitigationEvidence:
    action_seed = {
        "action": action.to_dict(),
        "policy": policy.to_dict(),
        "strategy": strategy.to_dict(),
        "confidence_score": confidence_score,
        "attack_type": attack_type,
        "risk_level": risk_level,
        "detection_evidence_hash": detection_evidence_hash,
        "timestamp": timestamp,
    }
    if controller_payload is not None:
        action_seed["controller_payload"] = controller_payload.to_dict()
    mitigation_hash = hashlib.sha256(to_canonical_json(action_seed).encode("utf-8")).hexdigest()
    generation_seed = {
        "mitigation_hash": mitigation_hash,
        "action_type": action.action_type,
        "target_ip": action.target_ip,
        "target_subnet": action.target_subnet,
    }
    mitigation_generation = hashlib.sha256(to_canonical_json(generation_seed).encode("utf-8")).hexdigest()
    return MitigationEvidence(
        mitigation_hash=mitigation_hash,
        mitigation_generation=mitigation_generation,
        action_type=action.action_type,
        target_ip=action.target_ip,
        timestamp=timestamp,
    )
