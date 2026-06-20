from __future__ import annotations

from nsddos.dashboard import generate_dashboard_state, validate_dashboard_evaluation


def _patch_sources(monkeypatch):
    from nsddos.dashboard import server as server_module

    monkeypatch.setattr(
        server_module,
        "latest_detection_evidence",
        lambda: {
            "attack_detected": True,
            "attack_type": "syn_flood",
            "risk_level": "HIGH",
            "telemetry_timestamp": "2100-01-01T00:00:00+00:00",
            "classification_generation": "gen-1",
        },
    )
    monkeypatch.setattr(
        server_module,
        "latest_mitigation_evidence",
        lambda: {
            "mitigation_action": "block_ip",
            "execution_result": "controller_payload_generated",
            "target_ip": "10.0.0.8",
            "risk_level": "HIGH",
            "timestamp": "2100-01-01T00:00:01+00:00",
        },
    )
    monkeypatch.setattr(server_module, "latest_policy_evaluation", lambda: {"policy_id": "policy-1", "recommended_action": "block_ip", "threshold_score": 0.8})
    monkeypatch.setattr(
        server_module,
        "latest_policy_history_payload",
        lambda: {
            "entries": [
                {
                    "policy_id": "policy-1",
                    "attack_type": "syn_flood",
                    "source_ip": "10.0.0.8",
                    "recommended_action": "block_ip",
                    "escalation_level": 1,
                    "confidence_score": 0.8,
                    "timestamp": "2100-01-01T00:00:00+00:00",
                }
            ]
        },
    )
    monkeypatch.setattr(
        server_module,
        "latest_ml_evaluation",
        lambda: {
            "confidence_score": 0.82,
            "drift_score": 0.31,
            "anomaly_score": 0.65,
            "false_positive_score": 0.08,
            "retraining_required": True,
            "model_version": "v1",
            "timestamp": "2100-01-01T00:00:02+00:00",
            "feature_vector": {"packet_rate": 120.0, "byte_rate": 2048.0},
            "diagnostics": {
                "retraining_frequency": 2,
                "drift_metrics": {"drift_score": 0.31},
                "model_accuracy_metrics": {"false_positive_rate": 0.08},
            },
        },
    )
    monkeypatch.setattr(server_module, "latest_distributed_evaluation", lambda: {"active_nodes": 2, "cluster_health": "healthy", "timestamp": "2100-01-01T00:00:03+00:00"})
    monkeypatch.setattr(server_module, "latest_deployment_payload", lambda: {"deployment_id": "deploy-1"})
    monkeypatch.setattr(
        server_module,
        "latest_streaming_evaluation",
        lambda: {
            "throughput": 12.5,
            "dropped_events": 1,
            "queue_state": {"queue_depth": 3},
            "session": {"session_id": "stream-1"},
            "diagnostics": {"queue_latency_ms": 4.5},
            "aggregation": {"packet_total": 120.0, "byte_total": 2048.0},
        },
    )
    monkeypatch.setattr(
        server_module,
        "replay_verification_runs",
        lambda limit=1: {
            "runs": [
                {
                    "results": [
                        {"name": "live_provider_mode", "status": "warn", "category": "live"},
                        {"name": "policy_rollback_validation", "status": "pass", "category": "policy"},
                    ]
                }
            ]
        },
    )
    monkeypatch.setattr(server_module, "persist_dashboard_history", lambda evaluation: None)


def test_dashboard_metrics_alerts_and_reports(monkeypatch):
    _patch_sources(monkeypatch)

    evaluation = generate_dashboard_state({})

    assert evaluation.active_attacks == 1
    assert evaluation.active_alerts >= 2
    assert evaluation.stream_throughput == 12.5
    assert evaluation.cluster_nodes == 2
    assert evaluation.ml_confidence == 0.82
    assert evaluation.policy_events == 1
    assert evaluation.reports
    assert not validate_dashboard_evaluation(evaluation)


def test_dashboard_threat_intel_and_policy_aggregation(monkeypatch):
    _patch_sources(monkeypatch)

    evaluation = generate_dashboard_state({})

    assert evaluation.threat_intel.repeated_attacker_ips[0][0] == "10.0.0.8"
    assert evaluation.policy_analytics.escalation_frequency == 1
    assert evaluation.ml_metrics.retraining_frequency == 2


def test_dashboard_stale_telemetry_handling(monkeypatch):
    _patch_sources(monkeypatch)
    from nsddos.dashboard import server as server_module

    monkeypatch.setattr(
        server_module,
        "latest_detection_evidence",
        lambda: {
            "attack_detected": True,
            "attack_type": "syn_flood",
            "risk_level": "HIGH",
            "telemetry_timestamp": "2000-01-01T00:00:00+00:00",
            "classification_generation": "gen-1",
        },
    )

    evaluation = generate_dashboard_state({})

    assert evaluation.diagnostics.stale_telemetry_warnings
