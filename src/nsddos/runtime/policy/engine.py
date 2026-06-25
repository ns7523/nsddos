"""Deterministic dynamic policy engine."""

from __future__ import annotations

import ipaddress
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.detection import evaluate_detection
from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.ml import evaluate_ml_detection
from nsddos.runtime.ml.models import MLDetectionEvaluation
from nsddos.runtime.persistence import (
    atomic_write_json,
    locked_persistence_scope,
    read_json_checked,
)
from nsddos.runtime.policy.adaptive import adaptive_action
from nsddos.runtime.policy.conditions import evaluate_conditions
from nsddos.runtime.policy.conflicts import resolve_conflicts
from nsddos.runtime.policy.contracts_models import (
    PolicyEvaluation,
    PolicyHistoryEntry,
    PolicyLearningState,
    PolicyRollbackState,
    PolicyThresholdState,
)
from nsddos.runtime.policy.diagnostics import build_policy_diagnostics
from nsddos.runtime.policy.evaluation import build_policy_evaluation
from nsddos.runtime.policy.history import load_history, save_history
from nsddos.runtime.policy.learning import load_learning_state, save_learning_state
from nsddos.runtime.policy.priorities import priority_for_action
from nsddos.runtime.policy.rollback import save_rollback_state
from nsddos.runtime.policy.rules import baseline_rule
from nsddos.runtime.policy.thresholds import calculate_thresholds
from nsddos.runtime.policy.validation import (
    validate_policy_evaluation,
    validate_policy_history,
    validate_policy_rollback,
)

POLICY_DIR = RUNTIME_DIR / "policy"


def _derive_source_ip(telemetry: dict[str, Any]) -> str:
    flows = telemetry.get("flows", [])
    scored: dict[str, float] = {}
    for flow in flows:
        if not isinstance(flow, dict):
            continue
        source = str(
            flow.get("source_ip") or flow.get("source") or flow.get("src_ip") or ""
        )
        if not source:
            continue
        try:
            ipaddress.ip_address(source)
        except ValueError:
            continue
        score = (
            float(flow.get("packets", 0.0))
            + float(flow.get("bytes", 0.0)) / 1000.0
            + float(flow.get("connections", 0.0))
        )
        scored[source] = scored.get(source, 0.0) + score
    if not scored:
        return ""
    return sorted(scored.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _derive_subnet(source_ip: str) -> str:
    if not source_ip:
        return ""
    network = ipaddress.ip_network(f"{source_ip}/24", strict=False)
    return str(network)


def _telemetry_flags(telemetry: dict[str, Any]) -> tuple[bool, bool]:
    freshness_degraded = bool(telemetry.get("freshness_state", {}).get("stale", False))
    replay_mode = bool(telemetry.get("replay_mode", False))
    return freshness_degraded, replay_mode


def _persist_evaluation(evaluation: PolicyEvaluation, *, lock_scope=None) -> None:
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    payload = evaluation.to_dict()
    stamp = evaluation.timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    atomic_write_json(
        POLICY_DIR / f"policy-{stamp}.json", payload, lock_scope=lock_scope
    )
    atomic_write_json(POLICY_DIR / "latest.json", payload, lock_scope=lock_scope)


def latest_policy_evaluation() -> dict[str, Any]:
    path = POLICY_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def evaluate_dynamic_policy(
    config: dict[str, Any],
    detection: DetectionEvaluation | None = None,
    ml: MLDetectionEvaluation | None = None,
    telemetry: dict[str, Any] | None = None,
    reference_at: str | None = None,
) -> PolicyEvaluation:
    start = monotonic()
    detection_evaluation = detection or evaluate_detection(
        config, telemetry=telemetry, reference_at=reference_at
    )
    ml_evaluation = ml or evaluate_ml_detection(
        config,
        detection=detection_evaluation,
        telemetry=telemetry,
        reference_at=reference_at,
    )
    payload = telemetry or {
        "flows": [],
        "freshness_state": {"stale": False},
        "replay_mode": False,
    }
    source_ip = _derive_source_ip(payload)
    source_subnet = _derive_subnet(source_ip)
    with locked_persistence_scope(POLICY_DIR) as policy_lock:
        history = load_history(lock_scope=policy_lock)
        learning_state = load_learning_state(lock_scope=policy_lock)
        history_errors = validate_policy_history(history)
        if history_errors:
            raise ValueError(f"policy history invalid: {','.join(history_errors)}")
        rule = baseline_rule(detection_evaluation)
        freshness_degraded, replay_mode = _telemetry_flags(payload)
        conditions = evaluate_conditions(
            attack_type=detection_evaluation.attack_type,
            source_ip=source_ip,
            source_subnet=source_subnet,
            confidence_score=detection_evaluation.confidence_score,
            freshness_degraded=freshness_degraded,
            replay_mode=replay_mode,
            history=history,
        )
        threshold_state = calculate_thresholds(
            attack_frequency=conditions.repeated_attack_frequency,
            source_ip=source_ip,
            attack_type=detection_evaluation.attack_type,
            confidence_score=detection_evaluation.confidence_score,
            learning_state=learning_state,
        )
        adjusted_threshold = max(
            0.0,
            min(
                1.0,
                threshold_state.threshold_score
                + (ml_evaluation.attack_probability * 0.10)
                - (ml_evaluation.false_positive_score * 0.15)
                - (ml_evaluation.drift_score * 0.05),
            ),
        )
        threshold_state = PolicyThresholdState(
            attack_frequency=threshold_state.attack_frequency,
            source_reputation_score=threshold_state.source_reputation_score,
            historical_confidence_score=threshold_state.historical_confidence_score,
            mitigation_success_rate=threshold_state.mitigation_success_rate,
            threshold_score=adjusted_threshold,
        )
        adaptive_recommendation, escalation_level = adaptive_action(
            rule.recommended_action,
            conditions=conditions,
            threshold_state=threshold_state,
        )
        candidates = tuple(
            item
            for item in (
                rule.recommended_action,
                adaptive_recommendation,
                (
                    "alert_only"
                    if ml_evaluation.false_positive_score
                    >= config.get("runtime", {})
                    .get("ml", {})
                    .get("false_positive_threshold", 0.20)
                    and ml_evaluation.inference.classification_state
                    in {"benign", "suspicious"}
                    else ""
                ),
                "alert_only" if freshness_degraded or replay_mode else "",
            )
            if item
        )
        conflict_resolution = resolve_conflicts(candidates)
        selected_action = conflict_resolution.selected_action
        priority = priority_for_action(selected_action)
        previous_threshold = history[-1].confidence_score if history else 0.0
        diagnostics = build_policy_diagnostics(
            history=history,
            escalation_level=escalation_level,
            threshold_score=threshold_state.threshold_score,
            previous_threshold_score=previous_threshold,
            decision_latency_ms=(monotonic() - start) * 1000,
            conflict_count=max(0, len(conflict_resolution.candidates) - 1),
        )
        timestamp = datetime.fromisoformat(
            (reference_at or detection_evaluation.telemetry_timestamp).replace(
                "Z", "+00:00"
            )
        )
        evaluation = build_policy_evaluation(
            attack_type=detection_evaluation.attack_type,
            source_ip=source_ip,
            source_subnet=source_subnet,
            confidence_score=detection_evaluation.confidence_score,
            risk_level=detection_evaluation.risk_level,
            recommended_action=selected_action,
            escalation_level=escalation_level,
            threshold_state=threshold_state,
            priority=priority,
            rule=rule,
            conditions=conditions,
            conflict_resolution=conflict_resolution,
            diagnostics=diagnostics,
            timestamp=timestamp,
        )
        errors = validate_policy_evaluation(evaluation)
        if errors:
            raise ValueError(f"policy evaluation invalid: {','.join(errors)}")
        entry = PolicyHistoryEntry(
            policy_id=evaluation.policy_id,
            attack_type=evaluation.attack_type,
            source_ip=evaluation.source_ip,
            source_subnet=evaluation.source_subnet,
            recommended_action=evaluation.recommended_action,
            confidence_score=evaluation.confidence_score,
            escalation_level=evaluation.escalation_level,
            timestamp=evaluation.timestamp.isoformat(),
        )
        next_history = history + (entry,)
        save_history(next_history, lock_scope=policy_lock)
        next_learning = PolicyLearningState(
            attack_signature_counts={
                **learning_state.attack_signature_counts,
                evaluation.attack_type: learning_state.attack_signature_counts.get(
                    evaluation.attack_type, 0
                )
                + 1,
            },
            source_ip_counts={
                **learning_state.source_ip_counts,
                source_ip: learning_state.source_ip_counts.get(source_ip, 0) + 1,
            },
            subnet_counts={
                **learning_state.subnet_counts,
                source_subnet: learning_state.subnet_counts.get(source_subnet, 0) + 1,
            },
            mitigation_success_rate={
                **learning_state.mitigation_success_rate,
                evaluation.attack_type: learning_state.mitigation_success_rate.get(
                    evaluation.attack_type, 1.0
                ),
            },
        )
        save_learning_state(next_learning, lock_scope=policy_lock)
        _persist_evaluation(evaluation, lock_scope=policy_lock)
        return evaluation


def rollback_dynamic_policy(config: dict[str, Any]) -> PolicyRollbackState:
    with locked_persistence_scope(POLICY_DIR) as policy_lock:
        history = load_history(lock_scope=policy_lock)
        if len(history) < 2:
            state = PolicyRollbackState(
                rollback_id=deterministic_id("policy-rollback", "noop"),
                restored_policy_id=history[-1].policy_id if history else "",
                restored_action=(
                    history[-1].recommended_action if history else "alert_only"
                ),
                restored_escalation_level=(
                    history[-1].escalation_level if history else 0
                ),
                restored_threshold_score=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                restored=False,
            )
            save_rollback_state(state, lock_scope=policy_lock)
            return state
        restored_entry = history[-2]
        save_history(history[:-1], lock_scope=policy_lock)
        latest_payload = latest_policy_evaluation()
        threshold_score = float(latest_payload.get("threshold_score", 0.0))
        state = PolicyRollbackState(
            rollback_id=deterministic_id(
                "policy-rollback",
                f"{restored_entry.policy_id}:{restored_entry.timestamp}",
            ),
            restored_policy_id=restored_entry.policy_id,
            restored_action=restored_entry.recommended_action,
            restored_escalation_level=restored_entry.escalation_level,
            restored_threshold_score=threshold_score,
            timestamp=datetime.now(timezone.utc).isoformat(),
            restored=True,
        )
        errors = validate_policy_rollback(state)
        if errors:
            raise ValueError(f"policy rollback invalid: {','.join(errors)}")
        save_rollback_state(state, lock_scope=policy_lock)
        return state
