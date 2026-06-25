from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from nsddos.runtime.detection.models import (
    AnomalyResult,
    AttackClassification,
    DetectionEvidence,
    DetectionEvaluation,
    FeatureVector,
    RiskAssessment,
    SignatureMatch,
)
from nsddos.runtime.mitigation.engine import evaluate_mitigation
from nsddos.runtime.policy.conflicts import resolve_conflicts
from nsddos.runtime.policy.engine import (
    evaluate_dynamic_policy,
    rollback_dynamic_policy,
)


def _telemetry(source: str = "10.0.0.8") -> dict:
    return {
        "provider_source": "test-fixture",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "sample_window_seconds": 1.0,
        "flows": [
            {
                "source": source,
                "destination_port": 80,
                "packets": 1200,
                "bytes": 600000,
                "connections": 200,
                "duration": 2,
                "syn_rate": 1200,
                "udp_rate": 0,
                "icmp_rate": 0,
                "protocol": "tcp",
            }
        ],
        "flow_state": {"flow_count": 1, "telemetry_present": True},
        "telemetry_state": {"active_flow_count": 1, "collector_reachable": True},
        "freshness_state": {"sample_interval_seconds": 1.0, "stale": False},
        "replay_mode": False,
    }


def _detection(
    attack_type: str,
    risk_level: str,
    confidence_score: float,
    *,
    telemetry_timestamp: str = "2026-01-01T00:00:00+00:00",
) -> DetectionEvaluation:
    features = FeatureVector(
        packet_rate=1200.0,
        byte_rate=600000.0,
        connection_rate=200.0,
        syn_rate=1200.0 if attack_type == "syn_flood" else 0.0,
        ack_rate=20.0,
        udp_rate=1500.0 if attack_type == "udp_flood" else 0.0,
        icmp_rate=1800.0 if attack_type == "icmp_flood" else 0.0,
        entropy_score=0.2,
        source_ip_cardinality=1,
    )
    classification = AttackClassification(
        attack_type=attack_type,
        severity="attack",
        attack_detected=True,
        confidence_score=confidence_score,
        signature_score=3.0,
        anomaly_score=2.0,
        traffic_intensity_score=2.0,
        matched_signatures=(attack_type,),
        triggered_anomalies=("burst",),
    )
    risk = RiskAssessment(
        risk_score=7.0,
        risk_level=risk_level,
        confidence_score=confidence_score,
        signature_score=3.0,
        anomaly_score=2.0,
        traffic_intensity_score=2.0,
    )
    evidence = DetectionEvidence(
        evidence_hash=f"det-{attack_type}-{risk_level}",
        classification_generation=f"gen-{attack_type}",
        provider_source="test-fixture",
        timestamp=telemetry_timestamp,
    )
    return DetectionEvaluation(
        attack_detected=True,
        attack_type=attack_type,
        confidence_score=confidence_score,
        risk_level=risk_level,
        evidence_hash=evidence.evidence_hash,
        classification_generation=evidence.classification_generation,
        detection_status="detected",
        telemetry_timestamp=telemetry_timestamp,
        feature_vector=features,
        classification=classification,
        risk=risk,
        evidence=evidence,
        signatures=(SignatureMatch(attack_type, True, 1.0),),
        anomalies=(AnomalyResult("burst", True, 2.0, 1.0, 1.5, 1.0),),
        baseline_source="fixture",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
    )


def _patch_policy_dirs(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.policy import engine as policy_engine
    from nsddos.runtime.policy import history as policy_history
    from nsddos.runtime.policy import learning as policy_learning
    from nsddos.runtime.policy import rollback as policy_rollback

    monkeypatch.setattr(policy_engine, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(policy_history, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(
        policy_history, "HISTORY_PATH", tmp_path / "policy" / "history.json"
    )
    monkeypatch.setattr(policy_learning, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(
        policy_learning, "LEARNING_PATH", tmp_path / "policy" / "learning.json"
    )
    monkeypatch.setattr(policy_rollback, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(
        policy_rollback, "ROLLBACK_PATH", tmp_path / "policy" / "rollback.json"
    )


def test_first_attack_policy_selection(tmp_path: Path, monkeypatch) -> None:
    _patch_policy_dirs(tmp_path, monkeypatch)
    result = evaluate_dynamic_policy(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    assert result.recommended_action == "rate_limit"
    assert result.escalation_level == 1


def test_repeated_source_ip_escalation(tmp_path: Path, monkeypatch) -> None:
    _patch_policy_dirs(tmp_path, monkeypatch)
    evaluate_dynamic_policy(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    result = evaluate_dynamic_policy(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    assert result.recommended_action == "block_ip"
    assert result.escalation_level == 2


def test_repeated_subnet_escalation(tmp_path: Path, monkeypatch) -> None:
    _patch_policy_dirs(tmp_path, monkeypatch)
    evaluate_dynamic_policy(
        {},
        detection=_detection("syn_flood", "HIGH", 0.91),
        telemetry=_telemetry(source="10.0.0.8"),
    )
    evaluate_dynamic_policy(
        {},
        detection=_detection("syn_flood", "HIGH", 0.91),
        telemetry=_telemetry(source="10.0.0.8"),
    )
    result = evaluate_dynamic_policy(
        {},
        detection=_detection("syn_flood", "HIGH", 0.91),
        telemetry=_telemetry(source="10.0.0.9"),
    )
    assert result.recommended_action == "isolate_subnet"
    assert result.source_subnet == "10.0.0.0/24"


def test_permanent_ban_escalation(tmp_path: Path, monkeypatch) -> None:
    _patch_policy_dirs(tmp_path, monkeypatch)
    for _ in range(3):
        evaluate_dynamic_policy(
            {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
        )
    result = evaluate_dynamic_policy(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    assert result.recommended_action == "permanent_ban"
    assert result.escalation_level == 4


def test_conflict_resolution_determinism() -> None:
    result = resolve_conflicts(("rate_limit", "block_ip", "rate_limit", "alert_only"))
    assert result.selected_action == "block_ip"
    assert result.candidates == ("block_ip", "rate_limit", "alert_only")


def test_rollback_restoration(tmp_path: Path, monkeypatch) -> None:
    _patch_policy_dirs(tmp_path, monkeypatch)
    first = evaluate_dynamic_policy(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    evaluate_dynamic_policy(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    rollback = rollback_dynamic_policy({})
    assert rollback.restored is True
    assert rollback.restored_policy_id == first.policy_id
    assert rollback.restored_action == first.recommended_action


def test_threshold_adaptation(tmp_path: Path, monkeypatch) -> None:
    _patch_policy_dirs(tmp_path, monkeypatch)
    first = evaluate_dynamic_policy(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    second = evaluate_dynamic_policy(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    assert second.threshold_score >= first.threshold_score


def test_malformed_history_rejection(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.persistence import atomic_write_json

    _patch_policy_dirs(tmp_path, monkeypatch)
    atomic_write_json(
        tmp_path / "policy" / "history.json",
        {
            "entries": [
                {
                    "policy_id": "bad",
                    "attack_type": "syn_flood",
                    "source_ip": "10.0.0.8",
                    "source_subnet": "10.0.0.0/24",
                    "recommended_action": "not-real",
                    "confidence_score": 0.9,
                    "escalation_level": 1,
                    "timestamp": "2026-01-01T00:00:00+00:00",
                }
            ]
        },
    )
    try:
        evaluate_dynamic_policy(
            {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
        )
    except ValueError as exc:
        assert "malformed_policy_history" in str(exc)
    else:
        raise AssertionError("malformed history must fail")


def test_dynamic_policy_feeds_mitigation_recommendation(
    tmp_path: Path, monkeypatch
) -> None:
    from nsddos.runtime.mitigation import engine as mitigation_engine

    _patch_policy_dirs(tmp_path, monkeypatch)
    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    policy = evaluate_dynamic_policy(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    result = evaluate_mitigation(
        {},
        detection=_detection("syn_flood", "HIGH", 0.91),
        policy=policy,
        telemetry=_telemetry(),
    )
    assert result.mitigation_action == "rate_limit"
