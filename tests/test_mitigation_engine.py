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
    severity: str = "attack",
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
        severity=severity if attack_type != "normal" else "normal",
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
        signatures=(SignatureMatch(attack_type, attack_detected, 1.0),) if attack_type != "normal" else (),
        anomalies=(AnomalyResult("burst", attack_detected, 2.0, 1.0, 1.5, 1.0),) if attack_detected else (),
        baseline_source="fixture",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
    )


def _evaluate(
    tmp_path: Path,
    monkeypatch,
    detection: DetectionEvaluation,
    telemetry: dict | None = None,
):
    from nsddos.runtime.mitigation import engine as mitigation_engine
    from nsddos.runtime.policy import engine as policy_engine
    from nsddos.runtime.policy import history as policy_history
    from nsddos.runtime.policy import learning as policy_learning
    from nsddos.runtime.policy import rollback as policy_rollback

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    monkeypatch.setattr(policy_engine, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(policy_history, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(policy_history, "HISTORY_PATH", tmp_path / "policy" / "history.json")
    monkeypatch.setattr(policy_learning, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(policy_learning, "LEARNING_PATH", tmp_path / "policy" / "learning.json")
    monkeypatch.setattr(policy_rollback, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(policy_rollback, "ROLLBACK_PATH", tmp_path / "policy" / "rollback.json")
    return evaluate_mitigation({}, detection=detection, telemetry=telemetry or _telemetry())


def test_syn_flood_blocking(tmp_path: Path, monkeypatch) -> None:
    result = _evaluate(tmp_path, monkeypatch, _detection("syn_flood", "HIGH", 0.91))
    assert result.mitigation_action == "rate_limit"
    assert result.target_ip == "10.0.0.8"


def test_udp_flood_rate_limiting(tmp_path: Path, monkeypatch) -> None:
    result = _evaluate(
        tmp_path,
        monkeypatch,
        _detection("udp_flood", "MEDIUM", 0.76),
        _telemetry(protocol="udp", udp_rate=1500, syn_rate=0),
    )
    assert result.mitigation_action == "drop_traffic"
    assert result.action_payload.action_type == "drop_traffic"


def test_icmp_traffic_dropping(tmp_path: Path, monkeypatch) -> None:
    result = _evaluate(
        tmp_path,
        monkeypatch,
        _detection("icmp_flood", "HIGH", 0.84),
        _telemetry(protocol="icmp", icmp_rate=1800, syn_rate=0),
    )
    assert result.mitigation_action == "block_ip"


def test_quarantine_host_action(tmp_path: Path, monkeypatch) -> None:
    result = _evaluate(tmp_path, monkeypatch, _detection("connection_exhaustion", "HIGH", 0.87))
    assert result.mitigation_action == "quarantine_host"
    assert result.action_payload.duration_seconds == 1800


def test_subnet_isolation_action(tmp_path: Path, monkeypatch) -> None:
    policy = type("PolicyEval", (), {"recommended_action": "isolate_subnet", "escalation_level": 3})()
    from nsddos.runtime.mitigation import engine as mitigation_engine

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    result = evaluate_mitigation(
        {},
        detection=_detection("syn_flood", "CRITICAL", 0.97, severity="critical_attack"),
        policy=policy,
        telemetry=_telemetry(),
    )
    assert result.mitigation_action == "isolate_subnet"
    assert result.target_subnet == "10.0.0.0/24"


def test_low_confidence_alert_only(tmp_path: Path, monkeypatch) -> None:
    result = _evaluate(tmp_path, monkeypatch, _detection("syn_flood", "HIGH", 0.42))
    assert result.mitigation_action == "alert_only"
    assert result.mitigation_required is False


def test_invalid_policy_rejection(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.mitigation import engine as mitigation_engine

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    monkeypatch.setattr(mitigation_engine, "evaluate_dynamic_policy", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(
        mitigation_engine,
        "evaluate_policy",
        lambda detection: type("BadPolicy", (), {"selected_action": "not-real", "reason": "bad", "policy_name": "policy_block_ip", "mitigation_required": True})(),
    )
    try:
        evaluate_mitigation({}, detection=_detection("syn_flood", "HIGH", 0.91), telemetry=_telemetry())
    except KeyError as exc:
        assert "not-real" in str(exc)
    else:
        raise AssertionError("invalid policy must fail")


def test_mitigation_hash_determinism(tmp_path: Path, monkeypatch) -> None:
    detection = _detection("syn_flood", "HIGH", 0.91)
    telemetry = _telemetry(timestamp="2026-01-01T00:00:00+00:00")
    policy = type("PolicyEval", (), {"recommended_action": "rate_limit", "escalation_level": 1})()
    from nsddos.runtime.mitigation import engine as mitigation_engine

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    first = evaluate_mitigation({}, detection=detection, policy=policy, telemetry=telemetry)
    second = evaluate_mitigation({}, detection=detection, policy=policy, telemetry=telemetry)
    assert first.mitigation_hash == second.mitigation_hash
    assert first.mitigation_generation == second.mitigation_generation


def test_controller_payload_determinism(tmp_path: Path, monkeypatch) -> None:
    detection = _detection("syn_flood", "HIGH", 0.91)
    policy = type("PolicyEval", (), {"recommended_action": "rate_limit", "escalation_level": 1})()
    from nsddos.runtime.mitigation import engine as mitigation_engine

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    first = evaluate_mitigation({}, detection=detection, policy=policy, telemetry=_telemetry())
    second = evaluate_mitigation({}, detection=detection, policy=policy, telemetry=_telemetry())
    assert first.controller_payload is not None
    assert second.controller_payload is not None
    assert first.controller_payload.payload_hash == second.controller_payload.payload_hash
    assert first.controller_payload.command == second.controller_payload.command
    assert first.controller_payload.controller_type == "floodlight-ovs-lab"
    assert "nw_src=10.0.0.8" in first.controller_payload.ovs_flow
    assert first.controller_payload.floodlight_payload["src-ip"] == "10.0.0.8"


def test_malformed_ip_rejection(tmp_path: Path, monkeypatch) -> None:
    try:
        _evaluate(
            tmp_path,
            monkeypatch,
            _detection("syn_flood", "HIGH", 0.91),
            _telemetry(source="bad-ip"),
        )
    except ValueError as exc:
        assert "missing_target_ip" in str(exc)
    else:
        raise AssertionError("malformed IP must fail")


def test_latest_history_persistence(tmp_path: Path, monkeypatch) -> None:
    _evaluate(tmp_path, monkeypatch, _detection("syn_flood", "HIGH", 0.91))
    mitigation_dir = tmp_path / "mitigation"
    files = sorted(item.name for item in mitigation_dir.iterdir())
    assert "latest.json" in files


def test_alert_only_enforcement_is_noop(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.mitigation import enforcement as enforcement_module
    from nsddos.runtime.mitigation import engine as mitigation_engine

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    evaluation = evaluate_mitigation(
        {},
        detection=_detection("syn_flood", "HIGH", 0.42),
        telemetry=_telemetry(),
    )

    class _Guard:
        def __getattr__(self, _name: str):
            raise AssertionError("provider mutation should not run for alert_only")

    registry = type("Registry", (), {"floodlight": _Guard(), "ovs": _Guard(), "mininet": _Guard()})()
    monkeypatch.setattr(enforcement_module, "build_live_provider_registry", lambda config: registry)

    enforced = enforcement_module.enforce_mitigation({}, evaluation)

    assert enforced.mitigation_status == "planned"
    assert enforced.execution_result == "alert_only"
    assert enforced.controller_mutation_status == "not_attempted"
    assert enforced.ovs_insertion_status == "not_attempted"
    assert enforced.flow_verification_status == "not_attempted"
    assert enforced.traffic_block_status == "not_attempted"


def test_enforcement_success_updates_verification_state(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.mitigation import enforcement as enforcement_module
    from nsddos.runtime.mitigation import engine as mitigation_engine

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    evaluation = evaluate_mitigation(
        {},
        detection=_detection("syn_flood", "HIGH", 0.91),
        telemetry=_telemetry(source="10.0.0.1"),
    )

    class _Floodlight:
        def push_static_flow(self, payload):
            return {"status": "ok", "payload": payload}

        def static_flow_exists(self, rule_id: str) -> bool:
            return rule_id == evaluation.controller_payload.flow_rule.rule_id

        def switches(self):
            return [{"switchDPID": "00:00:00:00:00:00:00:01"}]

    class _Ovs:
        def install_drop_flow(self, bridge: str, flow: str) -> bool:
            return bridge == "s1" and "nw_src=10.0.0.1" in flow

        def has_flow(self, bridge: str, match_fields: dict[str, str]) -> bool:
            return bridge == "s1" and match_fields["nw_src"] == "10.0.0.1"

    class _Mininet:
        def probe_traffic_drop(self, source_host: str, destination_ip: str) -> dict:
            return {
                "attempted": True,
                "blocked": source_host == "h1" and destination_ip == "10.0.0.2",
                "detail": "100% packet loss",
            }

    registry = type("Registry", (), {"floodlight": _Floodlight(), "ovs": _Ovs(), "mininet": _Mininet()})()
    monkeypatch.setattr(enforcement_module, "build_live_provider_registry", lambda config: registry)

    enforced = enforcement_module.enforce_mitigation({"lab": {"ovs_bridge": "s1"}}, evaluation)

    assert enforced.mitigation_status == "verified"
    assert enforced.execution_result == "traffic_blocked_verified"
    assert enforced.controller_mutation_status == "applied"
    assert enforced.ovs_insertion_status == "applied"
    assert enforced.flow_verification_status == "verified"
    assert enforced.traffic_block_status == "blocked"
    assert enforced.enforcement_evidence["traffic_probe"]["blocked"] is True


def test_enforcement_ovs_failure_sets_failed_result(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.mitigation import enforcement as enforcement_module
    from nsddos.runtime.mitigation import engine as mitigation_engine

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    evaluation = evaluate_mitigation(
        {},
        detection=_detection("syn_flood", "HIGH", 0.91),
        telemetry=_telemetry(source="10.0.0.1"),
    )

    class _Floodlight:
        def push_static_flow(self, payload):
            return {"status": "ok", "payload": payload}

        def static_flow_exists(self, _rule_id: str) -> bool:
            return True

        def switches(self):
            return [{"switchDPID": "00:00:00:00:00:00:00:01"}]

    class _Ovs:
        def install_drop_flow(self, bridge: str, flow: str) -> bool:
            return False

        def has_flow(self, bridge: str, match_fields: dict[str, str]) -> bool:
            return False

    class _Mininet:
        def probe_traffic_drop(self, source_host: str, destination_ip: str) -> dict:
            raise AssertionError("traffic probe must not run after ovs install failure")

    registry = type("Registry", (), {"floodlight": _Floodlight(), "ovs": _Ovs(), "mininet": _Mininet()})()
    monkeypatch.setattr(enforcement_module, "build_live_provider_registry", lambda config: registry)

    enforced = enforcement_module.enforce_mitigation({"lab": {"ovs_bridge": "s1"}}, evaluation)

    assert enforced.mitigation_status == "enforcement_failed"
    assert enforced.execution_result == "ovs_flow_insert_failed"
    assert enforced.controller_mutation_status == "applied"
    assert enforced.ovs_insertion_status == "failed"
    assert enforced.flow_verification_status == "not_attempted"
    assert enforced.traffic_block_status == "not_attempted"


def test_dynamic_policy_feeds_mitigation_recommendation(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.mitigation import engine as mitigation_engine
    from nsddos.runtime.policy import engine as policy_engine
    from nsddos.runtime.policy import history as policy_history
    from nsddos.runtime.policy import learning as policy_learning
    from nsddos.runtime.policy import rollback as policy_rollback

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    monkeypatch.setattr(policy_engine, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(policy_history, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(policy_history, "HISTORY_PATH", tmp_path / "policy" / "history.json")
    monkeypatch.setattr(policy_learning, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(policy_learning, "LEARNING_PATH", tmp_path / "policy" / "learning.json")
    monkeypatch.setattr(policy_rollback, "POLICY_DIR", tmp_path / "policy")
    monkeypatch.setattr(policy_rollback, "ROLLBACK_PATH", tmp_path / "policy" / "rollback.json")
    policy = policy_engine.evaluate_dynamic_policy(
        {"runtime": {"policy": {"enabled": True}}},
        detection=_detection("syn_flood", "HIGH", 0.91),
        telemetry=_telemetry(),
    )
    result = evaluate_mitigation(
        {},
        detection=_detection("syn_flood", "HIGH", 0.91),
        policy=policy,
        telemetry=_telemetry(),
    )
    assert result.mitigation_action == policy.recommended_action


def test_static_mitigation_policy_fallback_when_dynamic_policy_unavailable(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.mitigation import engine as mitigation_engine

    monkeypatch.setattr(mitigation_engine, "MITIGATION_DIR", tmp_path / "mitigation")
    monkeypatch.setattr(mitigation_engine, "evaluate_dynamic_policy", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    result = evaluate_mitigation(
        {},
        detection=_detection("udp_flood", "MEDIUM", 0.76),
        telemetry=_telemetry(protocol="udp", udp_rate=1500, syn_rate=0),
    )
    assert result.mitigation_action == "rate_limit"
