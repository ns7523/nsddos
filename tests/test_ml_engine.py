from __future__ import annotations

from pathlib import Path

from nsddos.runtime.ml import evaluate_ml_detection, retrain_ml_model
from nsddos.runtime.detection.models import (
    AnomalyResult,
    AttackClassification,
    DetectionEvidence,
    DetectionEvaluation,
    FeatureVector,
    RiskAssessment,
    SignatureMatch,
)


def _telemetry(
    source: str = "10.0.0.8",
    *,
    protocol: str = "tcp",
    packets: int = 1200,
    bytes_value: int = 600000,
    connections: int = 200,
    syn_rate: int = 1200,
    udp_rate: int = 0,
    icmp_rate: int = 0,
    timestamp: str = "2026-01-01T00:00:00+00:00",
) -> dict:
    return {
        "provider_source": "test-fixture",
        "timestamp": timestamp,
        "sample_window_seconds": 1.0,
        "flows": [
            {
                "source": source,
                "destination_port": 80,
                "packets": packets,
                "bytes": bytes_value,
                "connections": connections,
                "duration": 2,
                "syn_rate": syn_rate,
                "udp_rate": udp_rate,
                "icmp_rate": icmp_rate,
                "protocol": protocol,
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
    attack_detected: bool = True,
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
        severity="attack" if attack_type != "normal" else "normal",
        attack_detected=attack_detected,
        confidence_score=confidence_score,
        signature_score=3.0,
        anomaly_score=2.0,
        traffic_intensity_score=2.0,
        matched_signatures=(attack_type,) if attack_type != "normal" else (),
        triggered_anomalies=("burst",) if attack_type != "normal" else (),
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
        attack_detected=attack_detected,
        attack_type=attack_type,
        confidence_score=confidence_score,
        risk_level=risk_level,
        evidence_hash=evidence.evidence_hash,
        classification_generation=evidence.classification_generation,
        detection_status="detected" if attack_detected else "normal",
        telemetry_timestamp=telemetry_timestamp,
        feature_vector=features,
        classification=classification,
        risk=risk,
        evidence=evidence,
        signatures=(
            (SignatureMatch(attack_type, attack_detected, 1.0),)
            if attack_type != "normal"
            else ()
        ),
        anomalies=(
            (AnomalyResult("burst", attack_detected, 2.0, 1.0, 1.5, 1.0),)
            if attack_detected
            else ()
        ),
        baseline_source="fixture",
    )


def _patch_ml_dirs(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.ml import persistence as ml_persistence

    monkeypatch.setattr(ml_persistence, "ML_DIR", tmp_path / "ml")
    monkeypatch.setattr(ml_persistence, "LATEST_PATH", tmp_path / "ml" / "latest.json")
    monkeypatch.setattr(ml_persistence, "MODEL_PATH", tmp_path / "ml" / "model.json")
    monkeypatch.setattr(
        ml_persistence, "DATASET_PATH", tmp_path / "ml" / "dataset.json"
    )
    monkeypatch.setattr(
        ml_persistence, "METRICS_PATH", tmp_path / "ml" / "metrics.json"
    )
    monkeypatch.setattr(
        ml_persistence, "FEEDBACK_PATH", tmp_path / "ml" / "feedback.json"
    )


def _patch_policy_inputs(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.policy import history as policy_history
    from nsddos.runtime.mitigation import engine as mitigation_engine

    monkeypatch.setattr(policy_history, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(
        policy_history, "HISTORY_PATH", tmp_path / "policy" / "history.json"
    )
    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")


def test_dataset_generation(tmp_path: Path, monkeypatch) -> None:
    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    result = evaluate_ml_detection(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    assert result.dataset.row_count == 1


def test_feature_engineering_correctness(tmp_path: Path, monkeypatch) -> None:
    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    result = evaluate_ml_detection(
        {},
        detection=_detection("udp_flood", "HIGH", 0.77),
        telemetry=_telemetry(protocol="udp", udp_rate=1500, syn_rate=0),
    )
    assert result.feature_vector.udp_rate == 1500.0


def test_model_training(tmp_path: Path, monkeypatch) -> None:
    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    result = evaluate_ml_detection(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    assert result.training_state.model_id
    assert result.model_version


def test_deterministic_retraining(tmp_path: Path, monkeypatch) -> None:
    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    evaluate_ml_detection(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    first = retrain_ml_model(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    second = retrain_ml_model(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    assert first.model_version == second.model_version


def test_inference_scoring(tmp_path: Path, monkeypatch) -> None:
    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    result = evaluate_ml_detection(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    assert 0.0 <= result.attack_probability <= 1.0


def test_anomaly_scoring(tmp_path: Path, monkeypatch) -> None:
    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    result = evaluate_ml_detection(
        {},
        detection=_detection("icmp_flood", "HIGH", 0.84),
        telemetry=_telemetry(protocol="icmp", icmp_rate=1800, syn_rate=0),
    )
    assert 0.0 <= result.anomaly_score <= 1.0


def test_drift_detection(tmp_path: Path, monkeypatch) -> None:
    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    evaluate_ml_detection(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    result = evaluate_ml_detection(
        {},
        detection=_detection("syn_flood", "HIGH", 0.91),
        telemetry=_telemetry(packets=5000, bytes_value=2000000),
    )
    assert result.drift_score >= 0.0


def test_false_positive_calculation(tmp_path: Path, monkeypatch) -> None:
    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    result = evaluate_ml_detection(
        {},
        detection=_detection("syn_flood", "HIGH", 0.42, attack_detected=False),
        telemetry=_telemetry(),
    )
    assert 0.0 <= result.false_positive_score <= 1.0


def test_retraining_trigger_logic(tmp_path: Path, monkeypatch) -> None:
    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    result = evaluate_ml_detection(
        {
            "runtime": {
                "ml": {"drift_threshold": 0.01, "false_positive_threshold": 0.01}
            }
        },
        detection=_detection("syn_flood", "HIGH", 0.91),
        telemetry=_telemetry(packets=9000, bytes_value=5000000),
    )
    assert result.retraining_required is True


def test_model_persistence_integrity(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.ml.persistence import latest_ml_evaluation, load_model

    _patch_ml_dirs(tmp_path, monkeypatch)
    _patch_policy_inputs(tmp_path, monkeypatch)
    result = evaluate_ml_detection(
        {}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry()
    )
    assert latest_ml_evaluation()["model_id"] == result.model_id
    assert load_model() is not None
