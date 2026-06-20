from __future__ import annotations

from pathlib import Path

from nsddos.runtime.detection import engine as detection_engine
from nsddos.runtime.detection.engine import evaluate_detection
from nsddos.runtime.detection.validation import validate_detection_telemetry


def _telemetry(flows: list[dict], timestamp: str = "2026-01-01T00:00:00Z") -> dict:
    return {
        "provider_source": "test-fixture",
        "timestamp": timestamp,
        "sample_window_seconds": 1.0,
        "flows": flows,
        "flow_state": {"flow_count": len(flows), "telemetry_present": True},
        "telemetry_state": {"active_flow_count": len(flows), "collector_reachable": True},
        "freshness_state": {"sample_interval_seconds": 1.0, "stale": False},
    }


def _evaluate(tmp_path: Path, monkeypatch, flows: list[dict], timestamp: str = "2026-01-01T00:00:00Z"):
    monkeypatch.setattr(detection_engine, "DETECTION_DIR", tmp_path / "detection")
    return evaluate_detection({}, telemetry=_telemetry(flows, timestamp=timestamp))


def test_syn_flood_detection(tmp_path: Path, monkeypatch) -> None:
    flows = [{"source": "10.0.0.1", "destination_port": 80, "packets": 1200, "bytes": 600000, "syn_rate": 1200, "ack_rate": 20, "connections": 400, "duration": 2}]
    result = _evaluate(tmp_path, monkeypatch, flows)
    assert result.attack_detected is True
    assert result.attack_type == "syn_flood"


def test_udp_flood_detection(tmp_path: Path, monkeypatch) -> None:
    flows = [{"source": "10.0.0.2", "destination_port": 53, "packets": 1500, "bytes": 1200000, "udp_rate": 1500, "connections": 200, "duration": 3, "protocol": "udp"}]
    result = _evaluate(tmp_path, monkeypatch, flows)
    assert result.attack_type == "udp_flood"
    assert result.risk_level in {"HIGH", "CRITICAL"}


def test_icmp_flood_detection(tmp_path: Path, monkeypatch) -> None:
    flows = [{"source": "10.0.0.3", "destination_port": 0, "packets": 1800, "bytes": 900000, "icmp_rate": 1800, "connections": 100, "duration": 2, "protocol": "icmp"}]
    result = _evaluate(tmp_path, monkeypatch, flows)
    assert result.attack_type == "icmp_flood"


def test_normal_traffic_classification(tmp_path: Path, monkeypatch) -> None:
    flows = [
        {"source": "10.0.0.4", "destination_port": 443, "packets": 40, "bytes": 20000, "ack_rate": 35, "syn_rate": 20, "connections": 10, "duration": 20},
        {"source": "10.0.0.5", "destination_port": 443, "packets": 50, "bytes": 25000, "ack_rate": 45, "syn_rate": 15, "connections": 12, "duration": 18},
    ]
    result = _evaluate(tmp_path, monkeypatch, flows)
    assert result.attack_detected is False
    assert result.attack_type == "normal"


def test_false_positive_threshold_behavior(tmp_path: Path, monkeypatch) -> None:
    flows = [{"source": "10.0.0.6", "destination_port": 80, "packets": 700, "bytes": 200000, "syn_rate": 700, "ack_rate": 500, "connections": 100, "duration": 10}]
    result = _evaluate(tmp_path, monkeypatch, flows)
    assert result.attack_type == "normal"


def test_deterministic_confidence_scoring(tmp_path: Path, monkeypatch) -> None:
    flows = [{"source": "10.0.0.7", "destination_port": 80, "packets": 1200, "bytes": 600000, "syn_rate": 1200, "ack_rate": 20, "connections": 400, "duration": 2}]
    first = _evaluate(tmp_path, monkeypatch, flows, timestamp="2026-01-01T00:00:00Z")
    second = _evaluate(tmp_path, monkeypatch, flows, timestamp="2026-01-01T00:00:00Z")
    assert first.confidence_score == second.confidence_score


def test_deterministic_classification_generation_hashing(tmp_path: Path, monkeypatch) -> None:
    flows = [{"source": "10.0.0.8", "destination_port": 80, "packets": 1200, "bytes": 600000, "syn_rate": 1200, "ack_rate": 20, "connections": 400, "duration": 2}]
    first = _evaluate(tmp_path, monkeypatch, flows, timestamp="2026-01-01T00:00:00Z")
    second = _evaluate(tmp_path, monkeypatch, flows, timestamp="2026-01-01T00:00:00Z")
    assert first.classification_generation == second.classification_generation


def test_malformed_telemetry_rejection() -> None:
    errors = validate_detection_telemetry({"provider_source": "bad"})
    assert "missing:flows" in errors


def test_invalid_packet_rate_handling(tmp_path: Path, monkeypatch) -> None:
    flows = [{"source": "10.0.0.9", "destination_port": 80, "packets": -1, "bytes": 10, "connections": 1, "duration": 1}]
    try:
        _evaluate(tmp_path, monkeypatch, flows)
    except ValueError as exc:
        assert "invalid_feature_vector_values" in str(exc)
    else:
        raise AssertionError("negative packet rate must fail")
