from __future__ import annotations

from fastapi.testclient import TestClient

from nsddos.api.app import create_app, explain_api, get_route_summary
from nsddos.api.dependencies import get_config
from nsddos.runtime.persistence import atomic_write_json


def _client(config: dict | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config or {}
    return TestClient(app)


def test_api_route_summary_contains_required_groups():
    summary = get_route_summary()
    paths = {route["path"] for route in summary["routes"]}

    assert "/health" in paths
    assert "/runtime/query" in paths
    assert "/runtime/verification" in paths
    assert "/runtime/graph" in paths
    assert "/runtime/evidence" in paths
    assert "/runtime/snapshots" in paths
    assert "/runtime/timeline" in paths
    assert "/runtime/replay" in paths
    assert "/runtime/convergence" in paths
    assert "/runtime/drift" in paths
    assert "/runtime/stability" in paths
    assert "/runtime/detection" in paths
    assert "/runtime/mitigation" in paths
    assert "/runtime/live-telemetry" in paths
    assert "/runtime/provider-health" in paths
    assert "/runtime/provider-discovery" in paths
    assert "/runtime/simulate" in paths
    assert "/runtime/simulate-replay" in paths
    assert "/runtime/simulation-diagnostics" in paths
    assert "/runtime/stream/start" in paths
    assert "/runtime/stream/status" in paths
    assert "/runtime/stream/checkpoint" in paths
    assert "/runtime/stream/diagnostics" in paths
    assert "/runtime/ml/train" in paths
    assert "/runtime/ml/infer" in paths
    assert "/runtime/ml/diagnostics" in paths
    assert "/runtime/ml/retrain" in paths
    assert "/runtime/policy/evaluate" in paths
    assert "/runtime/policy/history" in paths
    assert "/runtime/policy/diagnostics" in paths
    assert "/runtime/policy/rollback" in paths
    assert "/deployment/start" in paths
    assert "/deployment/health" in paths
    assert "/deployment/diagnostics" in paths
    assert "/deployment/rollback" in paths
    assert "/distributed/orchestrate" in paths
    assert "/distributed/health" in paths
    assert "/distributed/diagnostics" in paths
    assert "/distributed/failover" in paths
    assert "/dashboard" in paths
    assert "/dashboard/alerts" in paths
    assert "/dashboard/report" in paths
    assert "/dashboard/diagnostics" in paths
    assert "/release/build" in paths
    assert "/release/diagnostics" in paths
    assert "/release/benchmark" in paths
    assert "/release/security-audit" in paths


def test_api_explain_declares_readonly_query_backed_contract():
    explanation = explain_api()

    assert explanation["readonly"] is True
    assert explanation["query_backed"] is True
    assert explanation["provider_access"] == "forbidden"


def test_health_response_is_typed_and_schema_versioned(tmp_path, monkeypatch):
    from nsddos import health as health_module
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module

    monkeypatch.setattr(
        health_module,
        "get_health_report",
        lambda verbose=False: {"flat": {"config": True, "runtime_dirs": True}},
    )
    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")
    response = _client().get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"]
    assert payload["status"] in {"ok", "degraded"}
    assert isinstance(payload["checks"], dict)


def test_runtime_query_post_uses_query_engine(tmp_path, monkeypatch):
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import snapshots as snapshots_module

    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    atomic_write_json(
        snapshot_dir / "snapshot-1.json",
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "schema_version": "1.0",
            "convergence_state": {"status": "converged"},
            "runtime_profile": {"name": "linux-native"},
        },
    )
    monkeypatch.setattr(snapshots_module, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")

    response = _client().post(
        "/runtime/query",
        json={
            "name": "snapshots",
            "scope": "persistence",
            "pagination": {"limit": 10, "offset": 0},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]["name"] == "snapshots"
    assert payload["total"] == 1
    assert payload["items"][0]["convergence"] == "converged"
    assert payload["replay_safe"] is True


def test_snapshot_api_pagination_is_stable(tmp_path, monkeypatch):
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import snapshots as snapshots_module

    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    for index in range(3):
        atomic_write_json(
            snapshot_dir / f"snapshot-{index}.json", {"timestamp": str(index)}
        )
    monkeypatch.setattr(snapshots_module, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")

    first = _client().get("/runtime/snapshots?limit=1&offset=0").json()
    second = _client().get("/runtime/snapshots?limit=1&offset=1").json()

    assert first["items"][0]["id"] == "snapshot-0"
    assert second["items"][0]["id"] == "snapshot-1"
    assert first["total"] == 3


def test_evidence_api_reads_evidence_bundle(tmp_path, monkeypatch):
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import evidence as evidence_module

    evidence_dir = tmp_path / "evidence" / "run"
    evidence_dir.mkdir(parents=True)
    atomic_write_json(
        evidence_dir / "evidence.json",
        {
            "schema_version": "1.0",
            "snapshot": {"timestamp": "2026-01-01T00:00:00Z"},
            "convergence": {"status": "partially_converged"},
            "verification": [{"name": "x"}],
        },
    )
    monkeypatch.setattr(evidence_module, "EVIDENCE_DIR", tmp_path / "evidence")
    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")

    response = _client().get("/runtime/evidence")

    assert response.status_code == 200
    assert response.json()["items"][0]["verification_count"] == 1


def test_graph_api_returns_query_backed_graph(monkeypatch, tmp_path):
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import graph as graph_query

    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(
        graph_query,
        "build_runtime_graph",
        lambda config: {
            "nodes": [{"id": "query:snapshots", "type": "runtime_query"}],
            "edges": [{"source": "a", "target": "b", "type": "query_dependency"}],
        },
    )

    response = _client().get("/runtime/graph?node_type=runtime_query")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["id"] == "query:snapshots"
    assert payload["plan"]["replay_safe"] is True


def test_api_response_exposes_runtime_timing_metrics(tmp_path, monkeypatch):
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import snapshots as snapshots_module

    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    atomic_write_json(snapshot_dir / "snapshot-1.json", {"timestamp": "1"})
    monkeypatch.setattr(snapshots_module, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")

    payload = _client().get("/runtime/snapshots").json()

    assert {"query_execution_ms", "selector_ms", "pagination_ms"} <= set(
        payload["performance"]
    )
    assert (
        payload["performance"]["query_execution_ms"]
        >= payload["performance"]["pagination_ms"]
    )


def test_detection_api_returns_typed_response(monkeypatch):
    from nsddos.runtime.query import detection as detection_query

    monkeypatch.setattr(
        detection_query,
        "evaluate_detection",
        lambda config: type(
            "DetectionEval",
            (),
            {
                "to_dict": lambda self: {
                    "attack_detected": True,
                    "attack_type": "syn_flood",
                    "confidence_score": 0.91,
                    "risk_level": "CRITICAL",
                    "evidence_hash": "abc",
                    "classification_generation": "def",
                    "detection_status": "detected",
                    "telemetry_timestamp": "2026-01-01T00:00:00Z",
                    "baseline_source": "fallback",
                }
            },
        )(),
    )

    response = _client().get("/runtime/detection")

    assert response.status_code == 200
    payload = response.json()
    assert payload["attack_detected"] is True
    assert payload["attack_type"] == "syn_flood"
    assert payload["confidence"] == 0.91
    assert payload["classification_generation"] == "def"


def test_mitigation_api_returns_typed_response(monkeypatch):
    from nsddos.runtime.query import mitigation as mitigation_query

    monkeypatch.setattr(
        mitigation_query,
        "evaluate_mitigation",
        lambda config: type(
            "MitigationEval",
            (),
            {
                "to_dict": lambda self: {
                    "mitigation_required": True,
                    "mitigation_action": "block_ip",
                    "target_ip": "10.0.0.8",
                    "target_subnet": "",
                    "confidence_score": 0.91,
                    "mitigation_status": "dry_run_ready",
                    "execution_result": "controller_payload_generated",
                    "mitigation_hash": "abc",
                    "mitigation_generation": "def",
                    "attack_type": "syn_flood",
                    "risk_level": "HIGH",
                    "timestamp": "2100-01-01T00:00:00Z",
                }
            },
        )(),
    )

    response = _client().get("/runtime/mitigation")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mitigation_required"] is True
    assert payload["mitigation_action"] == "block_ip"
    assert payload["target_ip"] == "10.0.0.8"
    assert payload["mitigation_generation"] == "def"


def test_deployment_api_returns_typed_response(monkeypatch):
    from nsddos.api import router as router_module

    monkeypatch.setattr(
        router_module,
        "deploy_runtime_stack",
        lambda config: type(
            "DeploymentEval",
            (),
            {
                "deployment_id": "deploy-prod-1",
                "environment": "prod",
                "container_contracts": (object(), object(), object()),
                "health": type("Health", (), {"service_health": "degraded"})(),
                "deployment_state": "degraded_dry_run",
                "rollback_state": type("Rollback", (), {"rollback_available": True})(),
            },
        )(),
    )

    response = _client().post("/deployment/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload["deployment_id"] == "deploy-prod-1"
    assert payload["environment"] == "prod"
    assert payload["container_count"] == 3
    assert payload["service_health"] == "degraded"
    assert payload["deployment_state"] == "degraded_dry_run"
    assert payload["rollback_available"] is True


def test_distributed_api_returns_typed_response(monkeypatch):
    from nsddos.api import router as router_module

    monkeypatch.setattr(
        router_module,
        "orchestrate_cluster_runtime",
        lambda config: type(
            "DistributedEval",
            (),
            {
                "cluster_id": "cluster:test",
                "active_nodes": 2,
                "leader_node": "node-1",
                "worker_count": 5,
                "replication_factor": 2,
                "partition_count": 4,
                "cluster_health": "healthy",
                "failover_available": True,
                "checkpoint_state": "ready",
                "timestamp": type(
                    "Ts", (), {"isoformat": lambda self: "2100-01-01T00:00:00+00:00"}
                )(),
            },
        )(),
    )

    response = _client().post("/distributed/orchestrate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["cluster_id"] == "cluster:test"
    assert payload["active_nodes"] == 2
    assert payload["leader_node"] == "node-1"
    assert payload["replication_factor"] == 2
    assert payload["checkpoint_state"] == "ready"


def test_dashboard_api_returns_typed_response(monkeypatch):
    from nsddos.api import router as router_module

    monkeypatch.setattr(
        router_module,
        "generate_dashboard_state",
        lambda config: type(
            "DashboardEval",
            (),
            {
                "dashboard_id": "dashboard:test",
                "active_attacks": 1,
                "active_alerts": 2,
                "stream_throughput": 12.5,
                "cluster_nodes": 1,
                "ml_confidence": 0.82,
                "mitigation_events": 1,
                "policy_events": 4,
                "dashboard_health": "degraded",
                "timestamp": type(
                    "Ts", (), {"isoformat": lambda self: "2100-01-01T00:00:00+00:00"}
                )(),
            },
        )(),
    )

    response = _client().get("/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dashboard_id"] == "dashboard:test"
    assert payload["active_attacks"] == 1
    assert payload["active_alerts"] == 2
    assert payload["ml_confidence"] == 0.82
    assert payload["dashboard_health"] == "degraded"


def test_release_api_returns_typed_response(monkeypatch):
    from nsddos.api import router as router_module

    monkeypatch.setattr(
        router_module,
        "generate_release_candidate",
        lambda config: type(
            "ReleaseEval",
            (),
            {
                "release_version": "1.0.0-rc1",
                "benchmark_score": 0.83,
                "load_test_score": 0.79,
                "stress_test_score": 0.75,
                "security_score": 0.91,
                "release_state": "release_ready",
            },
        )(),
    )

    response = _client().post("/release/build")

    assert response.status_code == 200
    payload = response.json()
    assert payload["release_version"] == "1.0.0-rc1"
    assert payload["benchmark_score"] == 0.83
    assert payload["stress_test_score"] == 0.75
    assert payload["release_state"] == "release_ready"


def test_live_telemetry_api_returns_typed_response(monkeypatch):
    from nsddos.runtime.query import live as live_query

    monkeypatch.setattr(
        live_query,
        "collect_live_telemetry",
        lambda config: type(
            "LiveEval",
            (),
            {
                "to_dict": lambda self: {
                    "provider_source": "live-provider-registry",
                    "packet_rate": 10.0,
                    "byte_rate": 100.0,
                    "active_flows": 2,
                    "health_state": "healthy",
                    "controller_status": "connected",
                    "timestamp": "2100-01-01T00:00:00Z",
                }
            },
        )(),
    )

    response = _client().get("/runtime/live-telemetry")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_source"] == "live-provider-registry"
    assert payload["active_flows"] == 2
    assert payload["controller_status"] == "connected"


def test_provider_health_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import live as live_query

    monkeypatch.setattr(
        live_query,
        "collect_live_telemetry",
        lambda config: type(
            "Snapshot",
            (),
            {
                "timestamp": type(
                    "Ts", (), {"isoformat": lambda self: "2100-01-01T00:00:00+00:00"}
                )(),
                "provider_health": (),
            },
        )(),
    )
    monkeypatch.setattr(
        live_query,
        "collect_provider_health",
        lambda records: {
            "sflowrt": {"state": "healthy", "reachable": True, "latency_ms": 1.0}
        },
    )

    response = _client().get("/runtime/provider-health")

    assert response.status_code == 200
    assert response.json()["items"][0]["provider"] == "sflowrt"


def test_provider_discovery_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import live as live_query

    monkeypatch.setattr(
        live_query,
        "collect_live_telemetry",
        lambda config: type(
            "Snapshot",
            (),
            {
                "timestamp": type(
                    "Ts", (), {"isoformat": lambda self: "2100-01-01T00:00:00+00:00"}
                )(),
                "topology_state": type(
                    "Topo",
                    (),
                    {"switches": ("s1",), "hosts": ("h1",), "controllers": ("c1",)},
                )(),
            },
        )(),
    )
    monkeypatch.setattr(
        live_query,
        "discover_runtime_providers",
        lambda floodlight_switches, mininet_switches, mininet_hosts, controller_endpoint: (
            type(
                "Discovery",
                (),
                {
                    "provider": "mininet",
                    "to_dict": lambda self: {
                        "switches": ["s1"],
                        "hosts": ["h1"],
                        "controllers": ["c1"],
                    },
                },
            )(),
        ),
    )

    response = _client().get("/runtime/provider-discovery")

    assert response.status_code == 200
    assert response.json()["items"][0]["provider"] == "mininet"


def test_simulation_api_returns_typed_response(monkeypatch):
    from nsddos.runtime.query import simulation as simulation_query

    monkeypatch.setattr(
        simulation_query,
        "generate_attack_traffic",
        lambda config, **kwargs: type(
            "SimulationEval",
            (),
            {
                "to_dict": lambda self: {
                    "attack_type": "syn_flood",
                    "target_ip": "10.0.0.1",
                    "packet_rate": 1200.0,
                    "byte_rate": 76800.0,
                    "duration_seconds": 10,
                    "intensity_level": "medium",
                    "timestamp": "2100-01-01T00:00:00Z",
                }
            },
        )(),
    )

    response = _client().get("/runtime/simulate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["attack_type"] == "syn_flood"
    assert payload["target_ip"] == "10.0.0.1"
    assert payload["duration_seconds"] == 10


def test_simulation_replay_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import simulation as simulation_query

    monkeypatch.setattr(
        simulation_query,
        "generate_attack_traffic",
        lambda config, **kwargs: type(
            "Contract",
            (),
            {
                "attack_type": "syn_flood",
                "target_ip": "10.0.0.1",
                "replay_records": (1, 2, 3),
                "duration_seconds": 10,
                "timestamp": type(
                    "Ts", (), {"isoformat": lambda self: "2100-01-01T00:00:00+00:00"}
                )(),
            },
        )(),
    )

    response = _client().get("/runtime/simulate-replay")

    assert response.status_code == 200
    assert response.json()["items"][0]["replay_records"] == 3


def test_simulation_diagnostics_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import simulation as simulation_query

    monkeypatch.setattr(
        simulation_query,
        "generate_attack_traffic",
        lambda config, **kwargs: type(
            "Contract",
            (),
            {
                "attack_type": "syn_flood",
                "timestamp": type(
                    "Ts", (), {"isoformat": lambda self: "2100-01-01T00:00:00+00:00"}
                )(),
            },
        )(),
    )
    monkeypatch.setattr(
        simulation_query,
        "build_simulation_diagnostics",
        lambda contract: type(
            "Diagnostics",
            (),
            {
                "to_dict": lambda self: {
                    "packet_count": 10,
                    "byte_count": 100,
                    "schedule_duration_ms": 50,
                    "replay_drift_detected": False,
                }
            },
        )(),
    )

    response = _client().get("/runtime/simulation-diagnostics")

    assert response.status_code == 200
    assert response.json()["items"][0]["packet_count"] == 10


def test_stream_start_api_returns_typed_response(monkeypatch):
    from datetime import datetime, timezone

    from nsddos.api import router as api_router

    monkeypatch.setattr(
        api_router,
        "process_stream_events",
        lambda config: type(
            "StreamingEval",
            (),
            {
                "session": type("Session", (), {"session_id": "stream-1"})(),
                "active_events": 3,
                "queue_state": type("Queue", (), {"queue_depth": 1})(),
                "dropped_events": 0,
                "throughput": 0.3,
                "stream_state": "active",
                "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
            },
        )(),
    )

    response = _client().post("/runtime/stream/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "stream-1"
    assert payload["active_events"] == 3
    assert payload["stream_state"] == "active"


def test_stream_status_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import streaming as streaming_query

    monkeypatch.setattr(
        streaming_query,
        "latest_streaming_evaluation",
        lambda: {
            "session": {"session_id": "stream-1"},
            "active_events": 2,
            "queue_state": {"queue_depth": 1},
            "dropped_events": 0,
            "throughput": 0.2,
            "stream_state": "active",
            "timestamp": "2100-01-01T00:00:00Z",
            "diagnostics": {"session_health": "healthy"},
        },
    )

    response = _client().get("/runtime/stream/status")

    assert response.status_code == 200
    assert response.json()["items"][0]["session_id"] == "stream-1"


def test_stream_checkpoint_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import streaming as streaming_query

    monkeypatch.setattr(
        streaming_query,
        "latest_checkpoint",
        lambda: {
            "session_id": "stream-1",
            "checkpoint_id": "checkpoint-1",
            "event_offset": 2,
            "sequence_number": 2,
            "queue_state": {"queue_depth": 1},
            "timestamp": "2100-01-01T00:00:00Z",
        },
    )

    response = _client().get("/runtime/stream/checkpoint")

    assert response.status_code == 200
    assert response.json()["items"][0]["checkpoint_id"] == "checkpoint-1"


def test_stream_diagnostics_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import streaming as streaming_query

    monkeypatch.setattr(
        streaming_query,
        "latest_streaming_evaluation",
        lambda: {
            "timestamp": "2100-01-01T00:00:00Z",
            "diagnostics": {
                "queue_latency_ms": 5.0,
                "processing_throughput": 2.0,
                "dropped_event_count": 1,
                "buffer_pressure": 0.5,
                "session_health": "degraded",
                "checkpoint_lag": 0,
            },
        },
    )

    response = _client().get("/runtime/stream/diagnostics")

    assert response.status_code == 200
    assert response.json()["items"][0]["session_health"] == "degraded"


def test_ml_infer_api_returns_typed_response(monkeypatch):
    from nsddos.runtime.query import ml as ml_query

    monkeypatch.setattr(
        ml_query,
        "evaluate_ml_detection",
        lambda config: type(
            "MLEval",
            (),
            {
                "to_dict": lambda self: {
                    "model_id": "ml-1",
                    "attack_probability": 0.91,
                    "predicted_attack_type": "syn_flood",
                    "confidence_score": 0.88,
                    "anomaly_score": 0.77,
                    "drift_score": 0.21,
                    "false_positive_score": 0.05,
                    "retraining_required": False,
                    "model_version": "v1",
                    "timestamp": "2100-01-01T00:00:00Z",
                }
            },
        )(),
    )
    monkeypatch.setattr(ml_query, "latest_ml_evaluation", lambda: {})

    response = _client().get("/runtime/ml/infer")

    assert response.status_code == 200
    payload = response.json()
    assert payload["attack_probability"] == 0.91
    assert payload["predicted_attack_type"] == "syn_flood"
    assert payload["model_version"] == "v1"


def test_ml_diagnostics_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import ml as ml_query

    monkeypatch.setattr(
        ml_query,
        "latest_ml_evaluation",
        lambda: {
            "timestamp": "2100-01-01T00:00:00Z",
            "diagnostics": {
                "model_accuracy_metrics": {
                    "precision": 0.8,
                    "recall": 0.7,
                    "false_positive_rate": 0.1,
                    "confidence_quality": 0.75,
                },
                "drift_metrics": {"drift_score": 0.2},
                "retraining_frequency": 1,
            },
        },
    )

    response = _client().get("/runtime/ml/diagnostics")

    assert response.status_code == 200
    assert response.json()["items"][0]["precision"] == 0.8


def test_ml_train_api_returns_typed_response(monkeypatch):
    from nsddos.api import router as api_router

    monkeypatch.setattr(
        api_router,
        "train_ml_model",
        lambda config: type(
            "MLEval",
            (),
            {
                "attack_probability": 0.7,
                "predicted_attack_type": "udp_flood",
                "confidence_score": 0.66,
                "anomaly_score": 0.55,
                "drift_score": 0.11,
                "model_version": "train-v1",
                "retraining_required": False,
            },
        )(),
    )

    response = _client().post("/runtime/ml/train")

    assert response.status_code == 200
    assert response.json()["model_version"] == "train-v1"


def test_ml_retrain_api_returns_typed_response(monkeypatch):
    from nsddos.api import router as api_router

    monkeypatch.setattr(
        api_router,
        "retrain_ml_model",
        lambda config: type(
            "MLEval",
            (),
            {
                "attack_probability": 0.75,
                "predicted_attack_type": "icmp_flood",
                "confidence_score": 0.69,
                "anomaly_score": 0.60,
                "drift_score": 0.31,
                "model_version": "retrain-v1",
                "retraining_required": True,
            },
        )(),
    )

    response = _client().post("/runtime/ml/retrain")

    assert response.status_code == 200
    assert response.json()["retraining_required"] is True


def test_policy_evaluate_api_returns_typed_response(monkeypatch):
    from datetime import datetime, timezone

    from nsddos.api import router as api_router

    monkeypatch.setattr(
        api_router,
        "evaluate_dynamic_policy",
        lambda config: type(
            "PolicyEval",
            (),
            {
                "policy_id": "policy-1",
                "recommended_action": "block_ip",
                "escalation_level": 2,
                "threshold_score": 0.82,
                "attack_frequency": 3,
                "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
            },
        )(),
    )

    response = _client().post("/runtime/policy/evaluate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_id"] == "policy-1"
    assert payload["recommended_action"] == "block_ip"
    assert payload["escalation_level"] == 2


def test_policy_history_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import policy as policy_query

    monkeypatch.setattr(
        policy_query,
        "latest_history_payload",
        lambda: {
            "entries": [
                {
                    "policy_id": "policy-1",
                    "attack_type": "syn_flood",
                    "source_ip": "10.0.0.8",
                    "recommended_action": "rate_limit",
                    "escalation_level": 1,
                    "timestamp": "2100-01-01T00:00:00Z",
                }
            ]
        },
    )

    response = _client().get("/runtime/policy/history")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "policy-1"


def test_policy_diagnostics_api_is_query_backed(monkeypatch):
    from nsddos.runtime.query import policy as policy_query

    monkeypatch.setattr(
        policy_query,
        "latest_policy_evaluation",
        lambda: {
            "timestamp": "2100-01-01T00:00:00Z",
            "diagnostics": {
                "decision_latency_ms": 2.5,
                "conflict_count": 1,
                "escalation_level": 2,
                "rollback_ready": True,
                "threshold_drift": 0.1,
            },
        },
    )

    response = _client().get("/runtime/policy/diagnostics")

    assert response.status_code == 200
    assert response.json()["items"][0]["rollback_ready"] is True


def test_policy_rollback_api_returns_typed_response(monkeypatch):
    from nsddos.api import router as api_router

    monkeypatch.setattr(
        api_router,
        "rollback_dynamic_policy",
        lambda config: type(
            "RollbackState",
            (),
            {
                "restored_policy_id": "policy-1",
                "restored_action": "rate_limit",
                "restored_escalation_level": 1,
                "restored_threshold_score": 0.64,
                "timestamp": "2100-01-01T00:00:00Z",
            },
        )(),
    )

    response = _client().post("/runtime/policy/rollback")

    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_id"] == "policy-1"
    assert payload["recommended_action"] == "rate_limit"
    assert payload["threshold_score"] == 0.64


def test_snapshot_lookup_lineage_and_compare_are_query_backed(tmp_path, monkeypatch):
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import snapshots as snapshots_module

    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    atomic_write_json(
        snapshot_dir / "snapshot-1.json", {"timestamp": "1", "services": []}
    )
    atomic_write_json(
        snapshot_dir / "snapshot-2.json",
        {"timestamp": "2", "services": [{"name": "sflowrt"}]},
    )
    monkeypatch.setattr(snapshots_module, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")

    lookup = _client().get("/runtime/snapshots/snapshot-1").json()
    lineage = _client().get("/runtime/snapshots/snapshot-2/lineage").json()
    comparison = (
        _client()
        .get("/runtime/snapshots/compare?left=snapshot-1&right=snapshot-2")
        .json()
    )

    assert lookup["items"][0]["id"] == "snapshot-1"
    assert lineage["items"][0]["source"] == "snapshot-1"
    assert lineage["items"][0]["target"] == "snapshot-2"
    assert comparison["items"][0]["left"] == "snapshot-1"
    assert comparison["items"][0]["right"] == "snapshot-2"
    assert lookup["query"]["name"] == "snapshots"


def test_graph_edge_traversal_uses_relationship_filters(monkeypatch, tmp_path):
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import graph as graph_query

    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(
        graph_query,
        "build_runtime_graph",
        lambda config: {
            "nodes": [{"id": "query:snapshots", "type": "runtime_query"}],
            "edges": [
                {
                    "source": "phase:api_query_bind",
                    "target": "query:snapshots",
                    "type": "api_query_surface",
                },
                {
                    "source": "query:snapshots",
                    "target": "query:evidence",
                    "type": "query_dependency",
                },
            ],
        },
    )

    payload = (
        _client()
        .get(
            "/runtime/graph/traverse?source=query:snapshots&relationship=query_dependency"
        )
        .json()
    )

    assert payload["items"][0]["source"] == "query:snapshots"
    assert payload["items"][0]["target"] == "query:evidence"
    assert payload["query"]["scope"] == "graph"


def test_evidence_and_timeline_filters_are_exposed(tmp_path, monkeypatch):
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import evidence as evidence_module
    from nsddos.runtime.query import timeline as timeline_module

    evidence_dir = tmp_path / "evidence"
    (evidence_dir / "run-a").mkdir(parents=True)
    (evidence_dir / "run-b").mkdir(parents=True)
    atomic_write_json(
        evidence_dir / "run-a" / "evidence.json",
        {
            "schema_version": "1.0",
            "convergence": {"status": "converged"},
            "verification": [{"name": "v"}],
        },
    )
    atomic_write_json(
        evidence_dir / "run-b" / "evidence.json",
        {
            "schema_version": "1.0",
            "convergence": {"status": "diverged"},
            "verification": [],
        },
    )
    monkeypatch.setattr(evidence_module, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(timeline_module, "build_runtime_timeline", lambda: [])
    monkeypatch.setattr(
        timeline_module,
        "load_transition_history",
        lambda: [
            {
                "id": "t1",
                "timestamp": "1",
                "status": "converged",
                "kind": "convergence",
            },
            {"id": "t2", "timestamp": "2", "status": "drifted", "kind": "drift"},
        ],
    )

    evidence = _client().get("/runtime/evidence?convergence=converged").json()
    transitions = _client().get("/runtime/timeline/transitions?kind=drift").json()

    assert [item["id"] for item in evidence["items"]] == ["run-a"]
    assert [item["id"] for item in transitions["items"]] == ["t2"]
