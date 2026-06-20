from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import typer

from nsddos.api import evidence_api, graph_api, health_api, query_api, replay as replay_api
from nsddos.api import router as router_module
from nsddos.api import service_api, snapshots_api, timeline_api, verification_api
from nsddos.api.app import create_app
from nsddos.api.dependencies import get_config
from nsddos.api.schemas import ApiEvidenceRef, ApiQueryRequest, ApiQueryResponse
from nsddos.cli import api_start


def _client(config: dict | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_config] = lambda: config or {}
    return TestClient(app)


def _fake_query_response(name: str, scope: str) -> ApiQueryResponse:
    item = {
        "id": "item-1",
        "type": name,
        "status": "ok",
        "checks": {"config": True},
        "attack_detected": True,
        "attack_type": "syn_flood",
        "confidence_score": 0.91,
        "risk_level": "critical",
        "evidence_hash": "evidence-1",
        "classification_generation": "classification-1",
        "mitigation_required": True,
        "mitigation_action": "block_ip",
        "target_ip": "10.0.0.9",
        "execution_result": "verified",
        "mitigation_hash": "mitigation-1",
        "mitigation_generation": "generation-1",
        "provider_source": "stub",
        "packet_rate": 42.0,
        "byte_rate": 4200.0,
        "active_flows": 7,
        "health_state": "healthy",
        "controller_status": "connected",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "duration_seconds": 10,
        "intensity_level": "medium",
        "attack_probability": 0.88,
        "predicted_attack_type": "syn_flood",
        "anomaly_score": 0.12,
        "drift_score": 0.04,
        "model_version": "model-v1",
        "retraining_required": False,
        "session_id": "session-1",
        "active_events": 3,
        "queue_depth": 2,
        "dropped_events": 0,
        "throughput": 11.5,
        "stream_state": "active",
        "policy_id": "policy-1",
        "recommended_action": "block_ip",
        "escalation_level": 2,
        "threshold_score": 0.82,
        "attack_frequency": 5,
        "left": "snapshot-left",
        "right": "snapshot-right",
        "target": "snapshot-1",
        "record_type": "snapshot",
        "validity_state": "valid",
    }
    if name == "health":
        item = {"id": "health-1", "type": "health", "status": "ok", "checks": {"config": True, "runtime_dirs": True}}
    return ApiQueryResponse(
        request_id=f"request-{name}",
        query={"name": name, "scope": scope},
        items=[item],
        total=1,
        evidence=[ApiEvidenceRef(kind="query", reference=name, detail=scope)],
        plan={"query": name, "scope": scope, "replay_safe": True},
        cache={"hit": False},
        performance={"query_execution_ms": 1.0, "selector_ms": 0.5, "pagination_ms": 0.1},
        duration_ms=1.0,
        timestamp="2026-01-01T00:00:00+00:00",
    )


def _install_api_stubs(monkeypatch) -> None:
    modules = (
        evidence_api,
        graph_api,
        health_api,
        query_api,
        replay_api,
        service_api,
        snapshots_api,
        timeline_api,
        verification_api,
    )
    for module in modules:
        monkeypatch.setattr(
            module,
            "execute_api_query",
            lambda config, request, _module=module: _fake_query_response(request.name, request.scope),
        )

    monkeypatch.setattr(
        router_module,
        "_state_endpoint",
        lambda name, scope, limit, offset, config: _fake_query_response(name, scope),
    )
    monkeypatch.setattr(router_module, "train_ml_model", lambda config: SimpleNamespace(
        attack_probability=0.9,
        predicted_attack_type="syn_flood",
        confidence_score=0.91,
        anomaly_score=0.15,
        drift_score=0.05,
        model_version="model-v1",
        retraining_required=False,
    ))
    monkeypatch.setattr(router_module, "retrain_ml_model", lambda config: SimpleNamespace(
        attack_probability=0.88,
        predicted_attack_type="syn_flood",
        confidence_score=0.89,
        anomaly_score=0.11,
        drift_score=0.03,
        model_version="model-v2",
        retraining_required=False,
    ))
    monkeypatch.setattr(
        router_module,
        "process_stream_events",
        lambda config: SimpleNamespace(
            session=SimpleNamespace(session_id="session-1"),
            queue_state=SimpleNamespace(queue_depth=2),
            active_events=3,
            dropped_events=0,
            throughput=11.5,
            stream_state="active",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )
    monkeypatch.setattr(
        router_module,
        "evaluate_dynamic_policy",
        lambda config: SimpleNamespace(
            policy_id="policy-1",
            recommended_action="block_ip",
            escalation_level=2,
            threshold_score=0.82,
            attack_frequency=5,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )
    monkeypatch.setattr(
        router_module,
        "rollback_dynamic_policy",
        lambda config: SimpleNamespace(
            restored_policy_id="policy-0",
            restored_action="alert_only",
            restored_escalation_level=1,
            restored_threshold_score=0.63,
            timestamp="2026-01-01T00:00:00+00:00",
        ),
    )
    deployment_eval = SimpleNamespace(
        schema_version="1.0",
        deployment_id="deploy-1",
        environment="prod",
        container_contracts=[{"name": "api"}, {"name": "ui"}],
        health=SimpleNamespace(service_health="healthy"),
        deployment_state="dry_run_ready",
        rollback_state=SimpleNamespace(rollback_available=True),
        diagnostics=SimpleNamespace(to_dict=lambda: {"warnings": []}),
    )
    monkeypatch.setattr(router_module, "deploy_runtime_stack", lambda config: deployment_eval)
    monkeypatch.setattr(router_module, "deployment_health", lambda config: deployment_eval)
    monkeypatch.setattr(router_module, "rollback_runtime_stack", lambda config: deployment_eval)
    monkeypatch.setattr(router_module, "latest_diagnostics_payload", lambda: {"warnings": []})
    distributed_eval = SimpleNamespace(
        schema_version="1.0",
        cluster_id="cluster-1",
        active_nodes=3,
        leader_node="node-1",
        worker_count=3,
        replication_factor=2,
        partition_count=4,
        cluster_health="healthy",
        failover_available=True,
        checkpoint_state="ready",
        environment="cluster",
        diagnostics=SimpleNamespace(to_dict=lambda: {"warnings": []}),
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(router_module, "orchestrate_cluster_runtime", lambda config: distributed_eval)
    monkeypatch.setattr(router_module, "distributed_health", lambda config: distributed_eval)
    monkeypatch.setattr(
        router_module,
        "distributed_failover_plan",
        lambda config: SimpleNamespace(leader_failover_node="node-2", failover_available=True),
    )
    monkeypatch.setattr(router_module, "latest_distributed_diagnostics_payload", lambda: {"warnings": []})
    dashboard_eval = SimpleNamespace(
        dashboard_id="dashboard-1",
        active_attacks=1,
        active_alerts=1,
        stream_throughput=11.5,
        cluster_nodes=3,
        ml_confidence=0.91,
        mitigation_events=2,
        policy_events=4,
        dashboard_health="healthy",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(router_module, "generate_dashboard_state", lambda config: dashboard_eval)
    monkeypatch.setattr(router_module, "dashboard_alerts", lambda config: ({"alert_id": "alert-1"},))
    monkeypatch.setattr(router_module, "dashboard_report", lambda config: ({"report_id": "report-1"},))
    monkeypatch.setattr(router_module, "dashboard_diagnostics", lambda config: {"status": "ok"})
    release_eval = SimpleNamespace(
        release_version="1.0.0-rc1",
        benchmark_score=0.9,
        load_test_score=0.9,
        stress_test_score=0.9,
        security_score=0.9,
        release_state="release_ready",
    )
    monkeypatch.setattr(router_module, "generate_release_candidate", lambda config: release_eval)
    monkeypatch.setattr(router_module, "release_diagnostics", lambda config: {"status": "ok"})
    monkeypatch.setattr(router_module, "release_benchmark", lambda config: {"benchmark_score": 0.9})
    monkeypatch.setattr(router_module, "release_security_audit", lambda config: {"security_score": 0.9})
    monkeypatch.setattr(verification_api, "explain_verification", lambda config: {"validators": ["runtime"]})
    monkeypatch.setattr(replay_api, "explain_query_system", lambda: {"queries": [{"name": "replay"}]})


def test_api_token_protects_runtime_routes(monkeypatch):
    _install_api_stubs(monkeypatch)
    monkeypatch.setenv("NSDDOS_API_TOKEN", "secret-token")
    client = _client()

    assert client.get("/health").status_code == 200
    assert client.get("/runtime/detection").status_code == 401
    response = client.get("/runtime/detection", headers={"X-NSDDOS-API-Token": "secret-token"})

    assert response.status_code == 200
    assert response.json()["attack_type"] == "syn_flood"


def test_all_api_routes_avoid_500_in_isolated_mode(monkeypatch):
    _install_api_stubs(monkeypatch)
    client = _client()
    route_inputs = {
        "/runtime/query": {"json": ApiQueryRequest(name="health", scope="runtime").model_dump()},
        "/runtime/snapshots/compare": {"params": {"left": "snapshot-1", "right": "snapshot-2"}},
    }

    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        methods = sorted(method for method in route.methods if method not in {"HEAD", "OPTIONS"})
        path = route.path.replace("{snapshot_id}", "snapshot-1")
        for method in methods:
            kwargs = dict(route_inputs.get(path, {}))
            response = client.request(method, path, **kwargs)
            assert response.status_code < 500, (method, path, response.text)


def test_api_start_handles_keyboard_interrupt(monkeypatch):
    calls: dict[str, object] = {}

    def fake_run(target: str, host: str, port: int, reload: bool) -> None:
        calls["target"] = target
        calls["host"] = host
        calls["port"] = port
        calls["reload"] = reload
        raise KeyboardInterrupt()

    monkeypatch.setattr("nsddos.cli._bootstrap", lambda: {"api_port": 8008})
    monkeypatch.setattr("uvicorn.run", fake_run)

    try:
        api_start(host="127.0.0.1", port=8011)
    except typer.Exit:
        assert False, "api_start should not exit on KeyboardInterrupt"

    assert calls["target"] == "nsddos.api.app:app"
    assert calls["host"] == "127.0.0.1"
    assert calls["port"] == 8011
    assert calls["reload"] is False
