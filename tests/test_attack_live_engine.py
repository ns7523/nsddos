from __future__ import annotations

from pathlib import Path

from nsddos.runtime.attack import engine as attack_engine
from nsddos.runtime.detection.classifier import classify_attack
from nsddos.runtime.detection.features import extract_feature_vector
from nsddos.runtime.detection.models import RiskAssessment
from nsddos.runtime.detection.signatures import match_signatures
from nsddos.runtime.mitigation.policies import (
    evaluate_policy as evaluate_mitigation_policy,
)
from nsddos.runtime.policy.rules import baseline_rule
from nsddos.runtime.streaming.aggregation import aggregate_events
from nsddos.runtime.streaming.contracts import (
    StreamEvent,
    StreamWindow,
    StreamWindowState,
)


def test_build_attack_script_covers_all_live_types():
    for attack_type in attack_engine.ATTACK_ORDER:
        script = attack_engine._build_attack_script(attack_type, "10.0.0.2", 8081, 15)
        assert script
        if attack_type in {"syn_flood", "udp_flood", "icmp_flood"}:
            assert "hping3" in script
        else:
            assert "python3" in script


def test_http_flood_signature_and_policy_mapping():
    telemetry = {
        "sample_window_seconds": 1.0,
        "flows": [
            {
                "source": "10.0.0.1",
                "destination_port": 8081,
                "protocol": "http",
                "packets": 480.0,
                "bytes": 350000.0,
                "connections": 100.0,
                "duration": 1.0,
                "http_rate": 480.0,
            }
        ],
        "flow_state": {"flow_count": 1},
        "telemetry_state": {},
        "freshness_state": {},
    }
    features = extract_feature_vector(telemetry)
    signatures = match_signatures(features)
    matched = {item.name for item in signatures if item.matched}
    assert "http_flood" in matched

    risk = RiskAssessment(0.9, "HIGH", 0.91, 0.9, 0.7, 0.8)
    classification = classify_attack(signatures, (), risk)
    detection = type(
        "DetectionStub",
        (),
        {
            "attack_detected": True,
            "attack_type": classification.attack_type,
            "confidence_score": risk.confidence_score,
            "risk_level": risk.risk_level,
            "classification": classification,
        },
    )()
    assert baseline_rule(detection).recommended_action == "rate_limit"
    assert evaluate_mitigation_policy(detection).selected_action == "rate_limit"


def test_slowloris_signature_and_policy_mapping():
    telemetry = {
        "sample_window_seconds": 1.0,
        "flows": [
            {
                "source": "10.0.0.1",
                "destination_port": 8081,
                "protocol": "slowloris",
                "packets": 50.0,
                "bytes": 8000.0,
                "connections": 90.0,
                "duration": 20.0,
                "http_rate": 50.0,
                "partial_connection_rate": 90.0,
            }
        ],
        "flow_state": {"flow_count": 1},
        "telemetry_state": {},
        "freshness_state": {},
    }
    features = extract_feature_vector(telemetry)
    signatures = match_signatures(features)
    matched = {item.name for item in signatures if item.matched}
    assert "slowloris" in matched

    risk = RiskAssessment(0.88, "HIGH", 0.89, 0.85, 0.7, 0.65)
    classification = classify_attack(signatures, (), risk)
    detection = type(
        "DetectionStub",
        (),
        {
            "attack_detected": True,
            "attack_type": classification.attack_type,
            "confidence_score": risk.confidence_score,
            "risk_level": risk.risk_level,
            "classification": classification,
        },
    )()
    assert baseline_rule(detection).recommended_action == "connection_reset"
    assert evaluate_mitigation_policy(detection).selected_action == "connection_reset"


def test_streaming_aggregation_detects_slowloris_pattern():
    event = StreamEvent(
        event_id="evt-1",
        source_type="live",
        packet_rate=10.0,
        byte_rate=1000.0,
        connection_rate=60.0,
        protocol="slowloris",
        source_ip="10.0.0.1",
        destination_ip="10.0.0.2",
        timestamp=attack_engine.datetime.now(attack_engine.timezone.utc),
        sequence_number=1,
        freshness_state="valid",
    )
    window = StreamWindow(
        "w1", event.timestamp.isoformat(), event.timestamp.isoformat(), (event,)
    )
    aggregation = aggregate_events(StreamWindowState("sliding", 10, (window,), 1))
    assert aggregation.attack_pattern == "slowloris"


def test_run_live_attack_suite_selects_requested_attacks(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(attack_engine, "ATTACK_DIR", tmp_path)
    monkeypatch.setattr(
        attack_engine,
        "_run_attack",
        lambda *args, **kwargs: {"attack_type": args[1], "summary": {"subsystems": {}}},
    )
    report = attack_engine.run_live_attack_suite(
        {}, attack="http_flood", warmup=1, attack_seconds=1, cooldown=1
    )
    assert [item["attack_type"] for item in report["scenarios"]] == ["http_flood"]
    assert Path(report["report_path"]).exists()
