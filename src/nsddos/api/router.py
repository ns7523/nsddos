"""API router assembly."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.routing import APIRoute

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.evidence_api import router as evidence_router
from nsddos.api.graph_api import router as graph_router
from nsddos.api.health_api import router as health_router
from nsddos.api.query_api import router as query_router
from nsddos.api.replay import router as replay_router
from nsddos.api.schemas import (
    ApiPagination,
    ApiQueryRequest,
    ApiQueryResponse,
    ApiRouteInfo,
    ApiRouteSummary,
    DashboardResponse,
    DetectionResponse,
    DeploymentResponse,
    DistributedResponse,
    LiveTelemetryResponse,
    MLDetectionResponse,
    MitigationResponse,
    PolicyResponse,
    ReleaseResponse,
    SimulationResponse,
    StreamingResponse,
)
from nsddos.api.service_api import router as service_router
from nsddos.api.snapshots_api import router as snapshots_router
from nsddos.api.timeline_api import router as timeline_router
from nsddos.api.verification_api import router as verification_router
from nsddos.dashboard import dashboard_alerts, dashboard_diagnostics, dashboard_report, generate_dashboard_state
from nsddos.distributed import (
    distributed_failover_plan,
    distributed_health,
    latest_diagnostics_payload as latest_distributed_diagnostics_payload,
    orchestrate_cluster_runtime,
)
from nsddos.deployment import deploy_runtime_stack, deployment_health, latest_diagnostics_payload, rollback_runtime_stack
from nsddos.release import generate_release_candidate, release_benchmark, release_diagnostics, release_security_audit
from nsddos.runtime.ml import retrain_ml_model, train_ml_model
from nsddos.runtime.policy import evaluate_dynamic_policy, rollback_dynamic_policy
from nsddos.runtime.streaming import process_stream_events

router = APIRouter()
router.include_router(health_router)
router.include_router(query_router)
router.include_router(verification_router)
router.include_router(graph_router)
router.include_router(evidence_router)
router.include_router(timeline_router)
router.include_router(snapshots_router)
router.include_router(replay_router)
router.include_router(service_router)


def _state_endpoint(name: str, scope: str, limit: int, offset: int, config: dict[str, Any]) -> ApiQueryResponse:
    return execute_api_query(
        config,
        ApiQueryRequest(
            name=name,
            scope=scope,
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )


@router.get("/runtime/convergence", response_model=ApiQueryResponse)
def runtime_convergence(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query convergence state."""
    return _state_endpoint("convergence", "convergence", limit, offset, config)


@router.get("/runtime/drift", response_model=ApiQueryResponse)
def runtime_drift(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query runtime drift."""
    return _state_endpoint("drift", "temporal", limit, offset, config)


@router.get("/runtime/stability", response_model=ApiQueryResponse)
def runtime_stability(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query runtime stability."""
    return _state_endpoint("stability", "temporal", limit, offset, config)


@router.get("/runtime/detection", response_model=DetectionResponse)
def runtime_detection(
    config: dict[str, Any] = Depends(get_config),
) -> DetectionResponse:
    """Query detection state."""
    payload = _state_endpoint("detection", "detection", 1, 0, config)
    item = payload.items[0] if payload.items else {}
    return DetectionResponse(
        attack_detected=bool(item.get("attack_detected", False)),
        attack_type=str(item.get("attack_type", "normal")),
        confidence=float(item.get("confidence_score", 0.0)),
        risk_level=str(item.get("risk_level", "LOW")),
        evidence_hash=str(item.get("evidence_hash", "")),
        classification_generation=str(item.get("classification_generation", "")),
    )


@router.get("/runtime/mitigation", response_model=MitigationResponse)
def runtime_mitigation(
    config: dict[str, Any] = Depends(get_config),
) -> MitigationResponse:
    """Query mitigation state."""
    payload = _state_endpoint("mitigation", "mitigation", 1, 0, config)
    item = payload.items[0] if payload.items else {}
    return MitigationResponse(
        mitigation_required=bool(item.get("mitigation_required", False)),
        mitigation_action=str(item.get("mitigation_action", "alert_only")),
        target_ip=str(item.get("target_ip", "")),
        execution_result=str(item.get("execution_result", "")),
        mitigation_hash=str(item.get("mitigation_hash", "")),
        mitigation_generation=str(item.get("mitigation_generation", "")),
    )


@router.get("/runtime/live-telemetry", response_model=LiveTelemetryResponse)
def runtime_live_telemetry(
    config: dict[str, Any] = Depends(get_config),
) -> LiveTelemetryResponse:
    """Query live telemetry state."""
    payload = _state_endpoint("live_telemetry", "live", 1, 0, config)
    item = payload.items[0] if payload.items else {}
    return LiveTelemetryResponse(
        provider_source=str(item.get("provider_source", "")),
        packet_rate=float(item.get("packet_rate", 0.0)),
        byte_rate=float(item.get("byte_rate", 0.0)),
        active_flows=int(item.get("active_flows", 0)),
        health_state=str(item.get("health_state", "disconnected")),
        controller_status=str(item.get("controller_status", "unknown")),
        timestamp=str(item.get("timestamp", "")),
    )


@router.get("/runtime/provider-health", response_model=ApiQueryResponse)
def runtime_provider_health(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query live provider health."""
    return _state_endpoint("provider_health", "provider", limit, offset, config)


@router.get("/runtime/provider-discovery", response_model=ApiQueryResponse)
def runtime_provider_discovery(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query live provider discovery."""
    return _state_endpoint("provider_discovery", "provider", limit, offset, config)


@router.get("/runtime/simulate", response_model=SimulationResponse)
def runtime_simulate(
    config: dict[str, Any] = Depends(get_config),
) -> SimulationResponse:
    """Query simulation state."""
    payload = _state_endpoint("simulation", "simulation", 1, 0, config)
    item = payload.items[0] if payload.items else {}
    return SimulationResponse(
        attack_type=str(item.get("attack_type", "")),
        target_ip=str(item.get("target_ip", "")),
        packet_rate=float(item.get("packet_rate", 0.0)),
        byte_rate=float(item.get("byte_rate", 0.0)),
        duration_seconds=int(item.get("duration_seconds", 0)),
        intensity_level=str(item.get("intensity_level", "")),
        timestamp=str(item.get("timestamp", "")),
    )


@router.get("/runtime/simulate-replay", response_model=ApiQueryResponse)
def runtime_simulate_replay(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query simulation replay state."""
    return _state_endpoint("simulation_replay", "simulation", limit, offset, config)


@router.get("/runtime/ml/infer", response_model=MLDetectionResponse)
def runtime_ml_infer(
    config: dict[str, Any] = Depends(get_config),
) -> MLDetectionResponse:
    """Query ML inference state."""
    payload = _state_endpoint("ml_infer", "ml", 1, 0, config)
    item = payload.items[0] if payload.items else {}
    return MLDetectionResponse(
        attack_probability=float(item.get("attack_probability", 0.0)),
        predicted_attack_type=str(item.get("predicted_attack_type", "normal")),
        confidence_score=float(item.get("confidence_score", 0.0)),
        anomaly_score=float(item.get("anomaly_score", 0.0)),
        drift_score=float(item.get("drift_score", 0.0)),
        model_version=str(item.get("model_version", "")),
        retraining_required=bool(item.get("retraining_required", False)),
    )


@router.get("/runtime/ml/diagnostics", response_model=ApiQueryResponse)
def runtime_ml_diagnostics(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query ML diagnostics."""
    return _state_endpoint("ml_diagnostics", "ml", limit, offset, config)


@router.post("/runtime/ml/train", response_model=MLDetectionResponse)
def runtime_ml_train(
    config: dict[str, Any] = Depends(get_config),
) -> MLDetectionResponse:
    """Train ML model."""
    evaluation = train_ml_model(config)
    return MLDetectionResponse(
        attack_probability=evaluation.attack_probability,
        predicted_attack_type=evaluation.predicted_attack_type,
        confidence_score=evaluation.confidence_score,
        anomaly_score=evaluation.anomaly_score,
        drift_score=evaluation.drift_score,
        model_version=evaluation.model_version,
        retraining_required=evaluation.retraining_required,
    )


@router.post("/runtime/ml/retrain", response_model=MLDetectionResponse)
def runtime_ml_retrain(
    config: dict[str, Any] = Depends(get_config),
) -> MLDetectionResponse:
    """Retrain ML model."""
    evaluation = retrain_ml_model(config)
    return MLDetectionResponse(
        attack_probability=evaluation.attack_probability,
        predicted_attack_type=evaluation.predicted_attack_type,
        confidence_score=evaluation.confidence_score,
        anomaly_score=evaluation.anomaly_score,
        drift_score=evaluation.drift_score,
        model_version=evaluation.model_version,
        retraining_required=evaluation.retraining_required,
    )


@router.get("/runtime/simulation-diagnostics", response_model=ApiQueryResponse)
def runtime_simulation_diagnostics(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query simulation diagnostics."""
    return _state_endpoint("simulation_diagnostics", "simulation", limit, offset, config)


@router.post("/runtime/stream/start", response_model=StreamingResponse)
def runtime_stream_start(
    config: dict[str, Any] = Depends(get_config),
) -> StreamingResponse:
    """Start bounded streaming session."""
    evaluation = process_stream_events(config)
    return StreamingResponse(
        session_id=evaluation.session.session_id,
        active_events=evaluation.active_events,
        queue_depth=evaluation.queue_state.queue_depth,
        dropped_events=evaluation.dropped_events,
        throughput=evaluation.throughput,
        stream_state=evaluation.stream_state,
        timestamp=evaluation.timestamp.isoformat(),
    )


@router.get("/runtime/stream/status", response_model=ApiQueryResponse)
def runtime_stream_status(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query stream status."""
    return _state_endpoint("stream_status", "streaming", limit, offset, config)


@router.get("/runtime/stream/checkpoint", response_model=ApiQueryResponse)
def runtime_stream_checkpoint(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query stream checkpoint."""
    return _state_endpoint("stream_checkpoint", "streaming", limit, offset, config)


@router.get("/runtime/stream/diagnostics", response_model=ApiQueryResponse)
def runtime_stream_diagnostics(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query stream diagnostics."""
    return _state_endpoint("stream_diagnostics", "streaming", limit, offset, config)


@router.post("/runtime/policy/evaluate", response_model=PolicyResponse)
def runtime_policy_evaluate(
    config: dict[str, Any] = Depends(get_config),
) -> PolicyResponse:
    """Evaluate dynamic policy."""
    evaluation = evaluate_dynamic_policy(config)
    return PolicyResponse(
        policy_id=evaluation.policy_id,
        recommended_action=evaluation.recommended_action,
        escalation_level=evaluation.escalation_level,
        threshold_score=evaluation.threshold_score,
        attack_frequency=evaluation.attack_frequency,
        timestamp=evaluation.timestamp.isoformat(),
    )


@router.get("/runtime/policy/history", response_model=ApiQueryResponse)
def runtime_policy_history(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query policy history."""
    return _state_endpoint("policy_history", "policy", limit, offset, config)


@router.get("/runtime/policy/diagnostics", response_model=ApiQueryResponse)
def runtime_policy_diagnostics(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query policy diagnostics."""
    return _state_endpoint("policy_diagnostics", "policy", limit, offset, config)


@router.post("/runtime/policy/rollback", response_model=PolicyResponse)
def runtime_policy_rollback(
    config: dict[str, Any] = Depends(get_config),
) -> PolicyResponse:
    """Rollback policy state."""
    rollback = rollback_dynamic_policy(config)
    return PolicyResponse(
        policy_id=rollback.restored_policy_id,
        recommended_action=rollback.restored_action,
        escalation_level=rollback.restored_escalation_level,
        threshold_score=rollback.restored_threshold_score,
        attack_frequency=0,
        timestamp=rollback.timestamp,
    )


@router.post("/deployment/start", response_model=DeploymentResponse)
def deployment_start(
    config: dict[str, Any] = Depends(get_config),
) -> DeploymentResponse:
    """Compute dry-run deployment evaluation."""
    evaluation = deploy_runtime_stack(config)
    return DeploymentResponse(
        deployment_id=evaluation.deployment_id,
        environment=evaluation.environment,
        container_count=len(evaluation.container_contracts),
        service_health=evaluation.health.service_health,
        deployment_state=evaluation.deployment_state,
        rollback_available=evaluation.rollback_state.rollback_available,
    )


@router.get("/deployment/health", response_model=DeploymentResponse)
def deployment_health_endpoint(
    config: dict[str, Any] = Depends(get_config),
) -> DeploymentResponse:
    """Return deployment health summary."""
    evaluation = deployment_health(config)
    return DeploymentResponse(
        deployment_id=evaluation.deployment_id,
        environment=evaluation.environment,
        container_count=len(evaluation.container_contracts),
        service_health=evaluation.health.service_health,
        deployment_state=evaluation.deployment_state,
        rollback_available=evaluation.rollback_state.rollback_available,
    )


@router.get("/deployment/diagnostics", response_model=dict[str, Any])
def deployment_diagnostics(
    config: dict[str, Any] = Depends(get_config),
) -> dict[str, Any]:
    """Return deployment diagnostics payload."""
    evaluation = deployment_health(config)
    return {
        "schema_version": evaluation.schema_version,
        "deployment_id": evaluation.deployment_id,
        "environment": evaluation.environment,
        "diagnostics": latest_diagnostics_payload() or evaluation.diagnostics.to_dict(),
    }


@router.post("/deployment/rollback", response_model=DeploymentResponse)
def deployment_rollback(
    config: dict[str, Any] = Depends(get_config),
) -> DeploymentResponse:
    """Compute dry-run rollback evaluation."""
    evaluation = rollback_runtime_stack(config)
    return DeploymentResponse(
        deployment_id=evaluation.deployment_id,
        environment=evaluation.environment,
        container_count=len(evaluation.container_contracts),
        service_health=evaluation.health.service_health,
        deployment_state=evaluation.deployment_state,
        rollback_available=evaluation.rollback_state.rollback_available,
    )


@router.post("/distributed/orchestrate", response_model=DistributedResponse)
def distributed_orchestrate(
    config: dict[str, Any] = Depends(get_config),
) -> DistributedResponse:
    """Compute dry-run distributed evaluation."""
    evaluation = orchestrate_cluster_runtime(config)
    return DistributedResponse(
        cluster_id=evaluation.cluster_id,
        active_nodes=evaluation.active_nodes,
        leader_node=evaluation.leader_node,
        worker_count=evaluation.worker_count,
        replication_factor=evaluation.replication_factor,
        partition_count=evaluation.partition_count,
        cluster_health=evaluation.cluster_health,
        failover_available=evaluation.failover_available,
        checkpoint_state=evaluation.checkpoint_state,
        timestamp=evaluation.timestamp.isoformat(),
    )


@router.get("/distributed/health", response_model=DistributedResponse)
def distributed_health_endpoint(
    config: dict[str, Any] = Depends(get_config),
) -> DistributedResponse:
    """Return distributed health summary."""
    evaluation = distributed_health(config)
    return DistributedResponse(
        cluster_id=evaluation.cluster_id,
        active_nodes=evaluation.active_nodes,
        leader_node=evaluation.leader_node,
        worker_count=evaluation.worker_count,
        replication_factor=evaluation.replication_factor,
        partition_count=evaluation.partition_count,
        cluster_health=evaluation.cluster_health,
        failover_available=evaluation.failover_available,
        checkpoint_state=evaluation.checkpoint_state,
        timestamp=evaluation.timestamp.isoformat(),
    )


@router.get("/distributed/diagnostics", response_model=dict[str, Any])
def distributed_diagnostics(
    config: dict[str, Any] = Depends(get_config),
) -> dict[str, Any]:
    """Return distributed diagnostics payload."""
    evaluation = distributed_health(config)
    return {
        "schema_version": evaluation.schema_version,
        "cluster_id": evaluation.cluster_id,
        "environment": evaluation.environment,
        "diagnostics": latest_distributed_diagnostics_payload() or evaluation.diagnostics.to_dict(),
    }


@router.post("/distributed/failover", response_model=DistributedResponse)
def distributed_failover(
    config: dict[str, Any] = Depends(get_config),
) -> DistributedResponse:
    """Return distributed failover summary."""
    evaluation = distributed_health(config)
    failover = distributed_failover_plan(config)
    return DistributedResponse(
        cluster_id=evaluation.cluster_id,
        active_nodes=evaluation.active_nodes,
        leader_node=failover.leader_failover_node or evaluation.leader_node,
        worker_count=evaluation.worker_count,
        replication_factor=evaluation.replication_factor,
        partition_count=evaluation.partition_count,
        cluster_health=evaluation.cluster_health,
        failover_available=failover.failover_available,
        checkpoint_state=evaluation.checkpoint_state,
        timestamp=evaluation.timestamp.isoformat(),
    )


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard_state(
    config: dict[str, Any] = Depends(get_config),
) -> DashboardResponse:
    """Return dashboard summary."""
    evaluation = generate_dashboard_state(config)
    return DashboardResponse(
        dashboard_id=evaluation.dashboard_id,
        active_attacks=evaluation.active_attacks,
        active_alerts=evaluation.active_alerts,
        stream_throughput=evaluation.stream_throughput,
        cluster_nodes=evaluation.cluster_nodes,
        ml_confidence=evaluation.ml_confidence,
        mitigation_events=evaluation.mitigation_events,
        policy_events=evaluation.policy_events,
        dashboard_health=evaluation.dashboard_health,
        timestamp=evaluation.timestamp.isoformat(),
    )


@router.get("/dashboard/alerts", response_model=dict[str, Any])
def dashboard_alerts_endpoint(
    config: dict[str, Any] = Depends(get_config),
) -> dict[str, Any]:
    """Return dashboard alerts."""
    return {"alerts": list(dashboard_alerts(config))}


@router.get("/dashboard/report", response_model=dict[str, Any])
def dashboard_report_endpoint(
    config: dict[str, Any] = Depends(get_config),
) -> dict[str, Any]:
    """Return dashboard reports."""
    return {"reports": list(dashboard_report(config))}


@router.get("/dashboard/diagnostics", response_model=dict[str, Any])
def dashboard_diagnostics_endpoint(
    config: dict[str, Any] = Depends(get_config),
) -> dict[str, Any]:
    """Return dashboard diagnostics."""
    return {"diagnostics": dashboard_diagnostics(config)}


@router.post("/release/build", response_model=ReleaseResponse)
def release_build(
    config: dict[str, Any] = Depends(get_config),
) -> ReleaseResponse:
    """Compute deterministic release candidate."""
    evaluation = generate_release_candidate(config)
    return ReleaseResponse(
        release_version=evaluation.release_version,
        benchmark_score=evaluation.benchmark_score,
        load_test_score=evaluation.load_test_score,
        stress_test_score=evaluation.stress_test_score,
        security_score=evaluation.security_score,
        release_state=evaluation.release_state,
    )


@router.get("/release/diagnostics", response_model=dict[str, Any])
def release_diagnostics_endpoint(
    config: dict[str, Any] = Depends(get_config),
) -> dict[str, Any]:
    """Return release diagnostics payload."""
    return {"diagnostics": release_diagnostics(config)}


@router.get("/release/benchmark", response_model=dict[str, Any])
def release_benchmark_endpoint(
    config: dict[str, Any] = Depends(get_config),
) -> dict[str, Any]:
    """Return release benchmark payload."""
    return {"benchmark": release_benchmark(config)}


@router.get("/release/security-audit", response_model=dict[str, Any])
def release_security_audit_endpoint(
    config: dict[str, Any] = Depends(get_config),
) -> dict[str, Any]:
    """Return release security audit payload."""
    return {"security_audit": release_security_audit(config)}


def route_summary(routes: list[Any]) -> ApiRouteSummary:
    """Summarize registered routes."""
    items = []
    for route in routes:
        if isinstance(route, APIRoute):
            methods = sorted(method for method in route.methods if method not in {"HEAD", "OPTIONS"})
            items.append(ApiRouteInfo(path=route.path, methods=methods, name=route.name))
    items.sort(key=lambda item: (item.path, ",".join(item.methods)))
    return ApiRouteSummary(routes=items, endpoint_count=len(items))
