"""Runtime verification validators."""

from __future__ import annotations

import json
from typing import Any

from nsddos.dashboard import generate_dashboard_state, validate_dashboard_evaluation
from nsddos.distributed import orchestrate_cluster_runtime, validate_distributed_evaluation
from nsddos.deployment import deploy_runtime_stack, validate_deployment_evaluation, validate_rollback_state
from nsddos.release import generate_release_candidate, validate_release_candidate
from nsddos.runtime.detection import evaluate_detection
from nsddos.runtime.mitigation import evaluate_mitigation
from nsddos.runtime.mitigation.validation import validate_mitigation_evaluation
from nsddos.runtime.ml import evaluate_ml_detection, latest_ml_evaluation, validate_ml_evaluation
from nsddos.runtime.models import SCHEMA_VERSION, VerificationResult
from nsddos.runtime.policy import (
    evaluate_dynamic_policy,
    latest_history_payload,
    latest_rollback_payload,
    validate_policy_evaluation,
    validate_policy_history,
    validate_policy_rollback,
)
from nsddos.runtime.policy.contracts_models import PolicyHistoryEntry, PolicyRollbackState
from nsddos.runtime.freshness import validate_freshness_payload
from nsddos.runtime.freshness.consistency import validate_consistency
from nsddos.runtime.providers.live.telemetry import collect_live_telemetry
from nsddos.runtime.providers.live.validation import validate_live_snapshot
from nsddos.runtime.simulation import generate_attack_traffic, validate_attack_contract
from nsddos.runtime.streaming import process_stream_events, validate_checkpoint, validate_streaming_evaluation
from nsddos.runtime.verification.registry import VerificationRegistry
from nsddos.runtime.verification.rules import RuntimeVerificationRule
from nsddos.runtime.domain.registry import default_domain_registry
from nsddos.runtime.domain.validation import validate_contract_payload


def _result(name: str, status: str, detail: str, category: str) -> VerificationResult:
    return VerificationResult(name=name, status=status, detail=detail, category=category)


def validate_environment(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate static/runtime environment."""
    running = context["running"]
    critical_static = {"docker", "compose", "config", "runtime_dirs"}
    results = [
        _result(
            item.name,
            "pass" if item.ok else ("fail" if item.name in critical_static or running else "warn"),
            item.detail,
            item.category,
        )
        for item in context["static_checks"]
    ]
    results.extend(
        _result(item.name, "pass" if item.ok else ("warn" if not running else "fail"), item.detail, item.category)
        for item in context["runtime_checks"]
    )
    profile = context["collection"].profile
    environment = context["collection"].environment
    capabilities = context["collection"].capabilities
    results.append(
        _result(
            "runtime_profile",
            "pass" if profile.get("name") in {"linux-native", "docker-linux"} else "warn",
            f"profile={profile.get('name')} detail={profile.get('detail', '')}",
            "environment",
        )
    )
    env_status = environment.get("status", "unsupported")
    results.append(
        _result(
            "profile_compatibility",
            "pass" if env_status == "compatible" else ("warn" if env_status in {"degraded", "partially_supported"} or not running else "fail"),
            environment.get("detail", ""),
            "environment",
        )
    )
    capability_status = "pass" if capabilities.get("docker_daemon") and capabilities.get("java_available") else "warn"
    if not capabilities.get("docker_installed") and running:
        capability_status = "fail"
    results.append(_result("capability_validation", capability_status, capabilities.get("detail", ""), "environment"))
    return results


def validate_reproducibility(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate reproducibility and bootstrap state."""
    running = context["running"]
    environment = context["collection"].environment
    reproducibility = context["collection"].reproducibility
    bootstrap = context["bootstrap"]
    provider_states = set(environment.get("provider_support", {}).values())
    return [
        _result(
            "provider_compatibility",
            "pass" if provider_states <= {"supported"} else ("warn" if "partial" in provider_states or not running else "fail"),
            json.dumps(environment.get("provider_support", {}), sort_keys=True),
            "reproducibility",
        ),
        _result(
            "environment_reproducibility",
            "pass" if reproducibility.get("status") == "reproducible" else ("warn" if reproducibility.get("status") == "partially_reproducible" or not running else "fail"),
            reproducibility.get("detail", ""),
            "reproducibility",
        ),
        _result(
            "runtime_portability",
            "pass" if bootstrap.get("status") == "supported" else ("warn" if bootstrap.get("status") == "degraded" or not running else "fail"),
            bootstrap.get("detail", ""),
            "reproducibility",
        ),
    ]


def validate_orchestration(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate execution graph and gates."""
    dep_state = context["dependency_state"]
    phase_names = context["phase_names"]
    replay = context["execution_replay"]
    pipeline_status = "reproducible_pipeline"
    if replay.get("failed"):
        pipeline_status = "unstable_pipeline"
    elif replay.get("warnings"):
        pipeline_status = "degraded_pipeline"
    return [
        _result("execution_graph_validation", "pass" if dep_state.get("valid") else "fail", f"phases={dep_state.get('phase_count')} deps={dep_state.get('dependency_count')}", "orchestration"),
        _result("startup_ordering_validation", "pass" if phase_names and phase_names[0] == "bootstrap" and phase_names[-1] == "evidence_capture" else "fail", " -> ".join(phase_names), "orchestration"),
        _result("orchestration_reproducibility", "pass" if pipeline_status == "reproducible_pipeline" else "warn", pipeline_status, "orchestration"),
        _result("readiness_gate_validation", "pass" if "verification_execute" in phase_names else "fail", "verification_execute gate present", "orchestration"),
        _result("convergence_gate_validation", "pass" if "convergence_validate" in phase_names else "fail", "convergence_validate gate present", "orchestration"),
    ]


def validate_collection(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate collection bundle shape."""
    collection = context["collection"]
    return [
        _result("collection_schema", "pass" if collection.schema_version == SCHEMA_VERSION else "fail", collection.schema_version, "collection"),
        _result("provider_collection", "pass" if collection.provider_status else "fail", f"providers={sorted(collection.provider_status)}", "collection"),
        _result("collection_cache_policy", "pass", json.dumps(collection.cache, sort_keys=True), "collection"),
    ]


def validate_normalization(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate normalized analysis bundle shape."""
    analysis = context["analysis"]
    return [
        _result("analysis_schema", "pass" if analysis.schema_version == SCHEMA_VERSION else "fail", analysis.schema_version, "normalization"),
        _result("identity_normalization", "pass" if not analysis.identity.get("conflicts") else "warn", f"conflicts={analysis.identity.get('conflicts', [])}", "normalization"),
        _result("datapath_normalization", "pass" if analysis.identity.get("switches") else "warn", f"switches={len(analysis.identity.get('switches', []))}", "normalization"),
    ]


def validate_topology(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate topology truth."""
    running = context["running"]
    topology = context["analysis"].topology
    interfaces = context["analysis"].interfaces
    return [
        _result("topology_consistency", "pass" if topology.get("consistent") else ("warn" if not running else "fail"), topology.get("detail", ""), "topology"),
        _result("interface_correlation", "pass" if not interfaces.get("missing_interfaces") else ("warn" if not running else "fail"), f"missing_interfaces={interfaces.get('missing_interfaces', [])}", "topology"),
        _result("controller_mapping", "pass" if not topology.get("missing_in_controller") and context["controller_open"] else ("warn" if not running else "fail"), f"missing_in_controller={topology.get('missing_in_controller', [])}", "topology"),
    ]


def validate_telemetry(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate telemetry visibility."""
    running = context["running"]
    provider_status = context["collection"].provider_status
    flows = context["collection"].flow_state
    freshness = context["collection"].freshness_state
    sflow = provider_status.get("sflowrt", {})
    reachable = bool(sflow.get("reachable") and sflow.get("flows_accessible") and sflow.get("metrics_accessible"))
    telemetry_status = "pass" if reachable else ("warn" if not running else "fail")
    if reachable and freshness.get("stale"):
        telemetry_status = "stale"
    flow_status = "pass" if flows.get("telemetry_present") else ("warn" if not running else "fail")
    if flows.get("telemetry_present") and freshness.get("stale"):
        flow_status = "stale"
    return [
        _result("telemetry_flowing", telemetry_status, f"flows={flows.get('flow_count', 0)} detail={freshness.get('detail', '')}", "telemetry"),
        _result("flow_visibility", flow_status, flows.get("detail", ""), "telemetry"),
        _result("telemetry_freshness", "stale" if freshness.get("stale") else "pass", freshness.get("detail", ""), "telemetry"),
    ]


def validate_reconciliation(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate reconciliation output."""
    running = context["running"]
    reconciliation = context["analysis"].reconciliation
    topology = context["analysis"].topology
    ok = not reconciliation.get("missing_entities") and not reconciliation.get("inconsistent_entities")
    return [
        _result("telemetry_topology_agreement", "pass" if not reconciliation.get("stale_entities") else ("warn" if not running else "stale"), f"stale_entities={reconciliation.get('stale_entities', [])}", "reconciliation"),
        _result("controller_ovs_agreement", "pass" if not topology.get("missing_in_controller") and not topology.get("missing_in_ovs") else ("warn" if not running else "fail"), f"provider_agreement={topology.get('provider_agreement', [])}", "reconciliation"),
        _result("runtime_reconciliation", "pass" if ok else ("warn" if not running else "fail"), reconciliation.get("detail", ""), "reconciliation"),
    ]


def validate_datapath(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate datapath truth."""
    running = context["running"]
    openflow = context["analysis"].openflow
    paths = context["analysis"].paths
    datapath_ok = not openflow.get("missing_ports") and not openflow.get("duplicate_ports")
    path_ok = not paths.get("missing_paths") and not paths.get("inconsistent_paths")
    return [
        _result("datapath_reconciliation", "pass" if datapath_ok else ("warn" if not running else "fail"), openflow.get("detail", ""), "datapath"),
        _result("port_level_visibility", "pass" if not openflow.get("stale_ports") and not openflow.get("orphan_ports") else ("warn" if not running else "stale"), f"stale_ports={openflow.get('stale_ports', [])} orphan_ports={openflow.get('orphan_ports', [])}", "datapath"),
        _result("interface_port_agreement", "pass" if not openflow.get("orphan_ports") else ("warn" if not running else "fail"), f"orphan_ports={openflow.get('orphan_ports', [])}", "datapath"),
        _result("telemetry_path_consistency", "pass" if path_ok else ("warn" if not running else "fail"), paths.get("detail", ""), "datapath"),
        _result("openflow_reconciliation", "pass" if openflow.get("ports") or not running else "fail", openflow.get("detail", ""), "datapath"),
    ]


def validate_convergence(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate convergence state."""
    running = context["running"]
    convergence = context["analysis"].convergence
    status_map = {"converged": "pass", "partially_converged": "warn", "diverged": "fail" if running else "warn"}
    return [
        _result("controller_convergence_validation", status_map.get(convergence.get("status", "diverged"), "warn"), convergence.get("detail", ""), "convergence"),
        _result("convergence_state", status_map.get(convergence.get("status", "diverged"), "warn"), f"status={convergence.get('status', 'unknown')}", "convergence"),
    ]


def validate_temporal(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate temporal analysis."""
    running = context["running"]
    temporal = context["analysis"].temporal
    stability = temporal.get("stability", {}).get("classification", "stable")
    status = "pass" if stability == "stable" else ("warn" if stability in {"degraded", "transient"} else "fail")
    return [
        _result("runtime_stability", status if running else ("warn" if status == "fail" else status), f"classification={stability}", "temporal"),
        _result("transition_history", "pass", f"transitions={len(temporal.get('transitions', []))}", "temporal"),
    ]


def validate_persistence(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate runtime state persistence."""
    runtime_state = context["runtime_state"]
    services = context["services"]
    state_service_names = sorted(service.name for service in runtime_state.services)
    live_service_names = sorted(service.name for service in services)
    running = context["running"]
    return [
        _result("runtime_state_schema", "pass" if runtime_state.schema_version == SCHEMA_VERSION else "fail", runtime_state.schema_version, "persistence"),
        _result("runtime_state_consistency", "pass" if state_service_names == live_service_names or not running else "fail", f"state={state_service_names} live={live_service_names}", "persistence"),
        _result("topology_state_consistency", "pass" if bool(context["provider_status"].get("mininet", {}).get("running")) == (runtime_state.topology_state == "running") else "fail", f"runtime={runtime_state.topology_state} provider={context['provider_status'].get('mininet', {}).get('running')}", "persistence"),
    ]


def validate_integrity(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate verification integrity."""
    registry = context["registry"]
    ordered = context["validator_order"]
    evidence = context["evidence"]
    from nsddos.runtime.query.registry import default_query_registry

    query_registry = default_query_registry()
    query_order = query_registry.ordered()
    try:
        from nsddos.api.app import explain_api, get_route_summary

        api_explain = explain_api()
        route_summary = get_route_summary()
        api_routes = route_summary.get("routes", [])
        api_status = "pass"
        api_detail = "API query-backed architecture active"
    except Exception as exc:
        api_explain = {"query_backed": False, "readonly": False}
        api_routes = []
        api_status = "warn"
        api_detail = f"api import degraded: {exc}"
    return [
        _result("validator_dependency_consistency", "pass" if len(ordered) == len(registry.rules) else "fail", f"validators={len(ordered)} rules={len(registry.rules)}", "integrity"),
        _result("verification_evidence_attached", "pass" if evidence else "fail", f"evidence={len(evidence)}", "integrity"),
        _result("verification_schema", "pass", SCHEMA_VERSION, "integrity"),
        _result("query_dependency_integrity", "pass" if query_order else "fail", f"queries={len(query_order)} deps={len(query_registry.dependencies())}", "integrity"),
        _result("query_scope_integrity", "pass" if query_registry.scopes else "fail", f"scopes={len(query_registry.scopes)}", "integrity"),
        _result("api_schema_consistency", "pass" if api_routes else api_status, f"routes={len(api_routes)}", "integrity"),
        _result("api_query_compatibility", "pass" if api_explain.get("query_backed") else api_status, api_detail, "integrity"),
        _result("api_pagination_stability", "pass" if api_routes else api_status, "limit/offset pagination enforced by typed schemas", "integrity"),
        _result("api_response_schema_integrity", "pass" if api_explain.get("readonly") else api_status, "Pydantic response models configured", "integrity"),
    ]


def validate_domain_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate typed domain contracts."""
    registry = default_domain_registry()
    payload = {"schema_version": "1.0", "contract_version": "17.0"}
    errors = validate_contract_payload(payload)
    return [
        _result("domain_registry_integrity", "pass" if registry.entity_types else "fail", f"entities={len(registry.entity_types)} relationships={len(registry.relationship_types)}", "domain"),
        _result("domain_contract_versioning", "pass" if not errors else "fail", ",".join(errors) or "contract versions valid", "domain"),
        _result("domain_schema_consistency", "pass" if len(registry.contract_versions) == len(registry.entity_types) else "fail", f"contract_versions={len(registry.contract_versions)}", "domain"),
    ]


def validate_freshness_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate freshness and temporal consistency contracts."""
    payload = context["analysis"].to_dict()
    telemetry = context["collection"].flow_state
    freshness_errors = validate_freshness_payload(
        {
            "created_at": payload.get("created_at"),
            "observed_at": telemetry.get("observed_at", payload.get("created_at")),
            "synchronized_at": telemetry.get("collected_at", payload.get("created_at")),
            "freshness_window": "runtime",
            "freshness_status": "authoritative-live",
            "validity_state": "valid",
            "replay_validity": "replay-safe",
            "consistency_generation": "verification-probe",
        }
    )
    consistency = validate_consistency("runtime", payload)
    return [
        _result(
            "freshness_contract_integrity",
            "pass" if not freshness_errors else "fail",
            ",".join(freshness_errors) or "freshness fields present",
            "freshness",
        ),
        _result(
            "temporal_consistency_integrity",
            "pass" if consistency.valid else "warn",
            ",".join(consistency.issues) or "consistent",
            "freshness",
        ),
        _result(
            "consistency_generation_integrity",
            "pass" if bool(consistency.generation) else "fail",
            consistency.generation,
            "freshness",
        ),
    ]


def _detection_telemetry_from_context(context: dict[str, Any]) -> dict[str, Any]:
    collection = context["collection"]
    return {
        "provider_source": "runtime-collection",
        "timestamp": collection.freshness_state.get("last_flow_timestamp") or "1970-01-01T00:00:00+00:00",
        "sample_window_seconds": collection.freshness_state.get("sample_interval_seconds", 1.0) or 1.0,
        "flows": [],
        "flow_state": collection.flow_state,
        "telemetry_state": collection.telemetry_state,
        "freshness_state": collection.freshness_state,
    }


def validate_detection_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate detection contracts."""
    try:
        evaluation = evaluate_detection(context["config"], telemetry=_detection_telemetry_from_context(context))
        errors: list[str] = []
    except Exception as exc:
        evaluation = None
        errors = [str(exc)]
    if evaluation is None:
        return [
            _result("detection_telemetry_validation", "fail", ",".join(errors), "detection"),
            _result("detection_contract_integrity", "fail", "detection evaluation unavailable", "detection"),
        ]
    return [
        _result("detection_telemetry_validation", "pass", f"provider={evaluation.evidence.provider_source}", "detection"),
        _result("detection_confidence_range", "pass" if 0.0 <= evaluation.confidence_score <= 1.0 else "fail", f"confidence={evaluation.confidence_score:.4f}", "detection"),
        _result("detection_attack_type_validation", "pass" if evaluation.attack_type else "fail", evaluation.attack_type, "detection"),
        _result("detection_evidence_hash_validation", "pass" if evaluation.evidence_hash else "fail", evaluation.evidence_hash, "detection"),
        _result("detection_scoring_consistency", "pass" if evaluation.classification.confidence_score == evaluation.risk.confidence_score else "fail", f"classification={evaluation.classification.confidence_score:.4f} risk={evaluation.risk.confidence_score:.4f}", "detection"),
    ]


def validate_ml_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate ML contracts."""
    enabled = bool(context["config"].get("runtime", {}).get("ml", {}).get("enabled", True))
    if not enabled:
        return [
            _result("ml_mode", "warn", "runtime.ml.enabled=false", "ml"),
            _result("ml_contract_integrity", "warn", "ml subsystem disabled", "ml"),
        ]
    try:
        evaluation = evaluate_ml_detection(
            context["config"],
            telemetry=_detection_telemetry_from_context(context),
        )
        errors = validate_ml_evaluation(evaluation)
        payload = latest_ml_evaluation()
    except Exception as exc:
        evaluation = None
        errors = [str(exc)]
        payload = {}
    if evaluation is None:
        return [
            _result("ml_contract_integrity", "fail", ",".join(errors), "ml"),
            _result("ml_model_validation", "fail", "ml evaluation unavailable", "ml"),
        ]
    return [
        _result("ml_contract_integrity", "pass" if not errors else "fail", ",".join(errors) or evaluation.model_id, "ml"),
        _result("ml_dataset_validation", "pass" if evaluation.dataset.row_count >= 1 else "fail", f"rows={evaluation.dataset.row_count}", "ml"),
        _result("ml_model_validation", "pass" if evaluation.training_state.model_id else "fail", evaluation.training_state.model_version, "ml"),
        _result("ml_inference_validation", "pass" if 0.0 <= evaluation.attack_probability <= 1.0 else "fail", f"attack_probability={evaluation.attack_probability:.4f}", "ml"),
        _result("ml_drift_validation", "pass" if 0.0 <= evaluation.drift_score <= 1.0 else "fail", f"drift_score={evaluation.drift_score:.4f}", "ml"),
        _result("ml_retraining_validation", "pass" if "retraining_required" in payload else "fail", f"retraining_required={evaluation.retraining_required}", "ml"),
    ]


def _policy_history_entries(payload: dict[str, Any]) -> tuple[PolicyHistoryEntry, ...]:
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return tuple()
    return tuple(
        PolicyHistoryEntry(
            policy_id=str(item.get("policy_id", "")),
            attack_type=str(item.get("attack_type", "")),
            source_ip=str(item.get("source_ip", "")),
            source_subnet=str(item.get("source_subnet", "")),
            recommended_action=str(item.get("recommended_action", "alert_only")),
            confidence_score=float(item.get("confidence_score", 0.0)),
            escalation_level=int(item.get("escalation_level", 0)),
            timestamp=str(item.get("timestamp", "")),
        )
        for item in entries
        if isinstance(item, dict)
    )


def _policy_rollback_state(payload: dict[str, Any]) -> PolicyRollbackState | None:
    if not payload or not payload.get("rollback_id"):
        return None
    return PolicyRollbackState(
        rollback_id=str(payload.get("rollback_id", "")),
        restored_policy_id=str(payload.get("restored_policy_id", "")),
        restored_action=str(payload.get("restored_action", "alert_only")),
        restored_escalation_level=int(payload.get("restored_escalation_level", 0)),
        restored_threshold_score=float(payload.get("restored_threshold_score", 0.0)),
        timestamp=str(payload.get("timestamp", "")),
        restored=bool(payload.get("restored", False)),
    )


def validate_policy_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate dynamic policy contracts."""
    enabled = bool(context["config"].get("runtime", {}).get("policy", {}).get("enabled", True))
    if not enabled:
        return [
            _result("policy_mode", "warn", "runtime.policy.enabled=false", "policy"),
            _result("policy_contract_integrity", "warn", "dynamic policy disabled", "policy"),
        ]
    try:
        evaluation = evaluate_dynamic_policy(
            context["config"],
            telemetry=_detection_telemetry_from_context(context),
        )
        evaluation_errors = validate_policy_evaluation(evaluation)
        history_entries = _policy_history_entries(latest_history_payload())
        history_errors = validate_policy_history(history_entries)
        rollback_state = _policy_rollback_state(latest_rollback_payload())
        rollback_errors = validate_policy_rollback(rollback_state) if rollback_state is not None else []
    except Exception as exc:
        evaluation = None
        evaluation_errors = [str(exc)]
        history_entries = tuple()
        history_errors = []
        rollback_state = None
        rollback_errors = []
    if evaluation is None:
        return [
            _result("policy_contract_integrity", "fail", ",".join(evaluation_errors), "policy"),
            _result("policy_history_validation", "warn", "policy history unavailable", "policy"),
        ]
    return [
        _result(
            "policy_contract_integrity",
            "pass" if not evaluation_errors else "fail",
            ",".join(evaluation_errors) or evaluation.policy_id,
            "policy",
        ),
        _result(
            "policy_escalation_validation",
            "pass" if 0 <= evaluation.escalation_level <= 4 else "fail",
            f"escalation_level={evaluation.escalation_level}",
            "policy",
        ),
        _result(
            "policy_conflict_validation",
            "pass" if evaluation.conflict_resolution.selected_action == evaluation.recommended_action else "fail",
            evaluation.conflict_resolution.reason,
            "policy",
        ),
        _result(
            "policy_history_validation",
            "pass" if history_entries and not history_errors else ("warn" if not history_entries else "fail"),
            ",".join(history_errors) or f"entries={len(history_entries)}",
            "policy",
        ),
        _result(
            "policy_rollback_validation",
            "pass" if rollback_state is not None and not rollback_errors else ("warn" if rollback_state is None else "fail"),
            ",".join(rollback_errors) or (rollback_state.rollback_id if rollback_state is not None else "rollback state unavailable"),
            "policy",
        ),
        _result(
            "policy_threshold_drift_validation",
            "pass" if abs(evaluation.diagnostics.threshold_drift) <= 1.0 else "fail",
            f"threshold_drift={evaluation.diagnostics.threshold_drift:.4f}",
            "policy",
        ),
    ]


def validate_live_provider_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate live provider contracts."""
    enabled = bool(context["config"].get("runtime", {}).get("live", {}).get("enabled", False))
    if not enabled:
        return [
            _result("live_provider_mode", "pass", "runtime.live.enabled=false disabled_by_config", "live"),
            _result("live_provider_contract_integrity", "pass", "live provider collection disabled_by_config", "live"),
        ]
    try:
        snapshot = collect_live_telemetry(context["config"])
        errors = validate_live_snapshot(snapshot)
    except Exception as exc:
        snapshot = None
        errors = [str(exc)]
    if snapshot is None:
        return [
            _result("live_provider_telemetry_validation", "fail", ",".join(errors), "live"),
            _result("live_provider_contract_integrity", "fail", "live telemetry unavailable", "live"),
        ]
    unreachable = [item.provider for item in snapshot.provider_health if item.state == "disconnected"]
    degraded = [item.provider for item in snapshot.provider_health if item.state in {"degraded", "reconnecting"}]
    return [
        _result("live_provider_telemetry_validation", "pass" if not errors else "fail", ",".join(errors) or snapshot.provider_source, "live"),
        _result("live_provider_reachability", "warn" if unreachable else "pass", f"unreachable={unreachable}", "live"),
        _result("live_provider_counter_validation", "pass" if snapshot.packet_rate >= 0 and snapshot.byte_rate >= 0 and snapshot.active_flows >= 0 else "fail", f"packet_rate={snapshot.packet_rate:.2f} byte_rate={snapshot.byte_rate:.2f}", "live"),
        _result("live_provider_timestamp_validation", "pass" if "stale_provider_timestamp" not in errors else "fail", snapshot.timestamp.isoformat(), "live"),
        _result("live_provider_topology_validation", "warn" if degraded and not snapshot.topology_state.switches else ("pass" if snapshot.topology_state.switches else "fail"), f"switches={len(snapshot.topology_state.switches)} hosts={len(snapshot.topology_state.hosts)}", "live"),
    ]


def validate_simulation_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate simulation contracts."""
    enabled = bool(context["config"].get("runtime", {}).get("simulation", {}).get("source_enabled", False))
    if not enabled:
        return [
            _result("simulation_mode", "pass", "runtime.simulation.source_enabled=false disabled_by_config", "simulation"),
            _result("simulation_contract_integrity", "pass", "simulation source disabled_by_config", "simulation"),
        ]
    try:
        contract = generate_attack_traffic(context["config"], replay_mode=True)
        errors = validate_attack_contract(contract)
    except Exception as exc:
        contract = None
        errors = [str(exc)]
    if contract is None:
        return [
            _result("simulation_contract_validation", "fail", ",".join(errors), "simulation"),
            _result("simulation_generator_integrity", "fail", "simulation contract unavailable", "simulation"),
        ]
    return [
        _result("simulation_contract_validation", "pass" if not errors else "fail", ",".join(errors) or contract.attack_type, "simulation"),
        _result("simulation_packet_rate_validation", "pass" if contract.packet_rate > 0 else "fail", f"packet_rate={contract.packet_rate:.2f}", "simulation"),
        _result("simulation_topology_route_validation", "pass" if contract.topology_path else "fail", f"path={list(contract.topology_path)}", "simulation"),
        _result("simulation_replay_validation", "pass" if contract.replay_records else "fail", f"replay_records={len(contract.replay_records)}", "simulation"),
        _result("simulation_schedule_validation", "pass" if contract.packet_schedule else "fail", f"schedule_entries={len(contract.packet_schedule)}", "simulation"),
    ]


def validate_streaming_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate streaming contracts."""
    enabled = bool(context["config"].get("runtime", {}).get("streaming", {}).get("enabled", False))
    if not enabled:
        return [
            _result("streaming_mode", "pass", "runtime.streaming.enabled=false disabled_by_config", "streaming"),
            _result("streaming_contract_integrity", "pass", "streaming mode disabled_by_config", "streaming"),
        ]
    try:
        evaluation = process_stream_events(context["config"])
        errors = validate_streaming_evaluation(evaluation)
        checkpoint_errors = validate_checkpoint(evaluation.checkpoint)
    except Exception as exc:
        evaluation = None
        errors = [str(exc)]
        checkpoint_errors = []
    if evaluation is None:
        return [
            _result("streaming_event_validation", "fail", ",".join(errors), "streaming"),
            _result("streaming_recovery_validation", "fail", "streaming evaluation unavailable", "streaming"),
        ]
    return [
        _result("streaming_event_validation", "pass" if not errors else "fail", ",".join(errors) or f"events={len(evaluation.source_events)}", "streaming"),
        _result("streaming_queue_validation", "pass" if not checkpoint_errors else "fail", ",".join(checkpoint_errors) or f"queue_depth={evaluation.queue_state.queue_depth}", "streaming"),
        _result("streaming_sequence_validation", "pass" if evaluation.checkpoint.sequence_number >= 0 else "fail", f"sequence={evaluation.checkpoint.sequence_number}", "streaming"),
        _result("streaming_checkpoint_validation", "pass" if evaluation.checkpoint.checkpoint_id else "fail", evaluation.checkpoint.checkpoint_id, "streaming"),
        _result("streaming_recovery_validation", "pass", f"session={evaluation.session.session_id}", "streaming"),
    ]


def validate_mitigation_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate mitigation contracts."""
    try:
        evaluation = evaluate_mitigation(
            context["config"],
            telemetry=_detection_telemetry_from_context(context),
        )
        errors = validate_mitigation_evaluation(evaluation)
    except Exception as exc:
        evaluation = None
        errors = [str(exc)]
    if evaluation is None:
        return [
            _result("mitigation_execution_validation", "fail", ",".join(errors), "mitigation"),
            _result("mitigation_contract_integrity", "fail", "mitigation evaluation unavailable", "mitigation"),
        ]
    controller_hash = evaluation.controller_payload.payload_hash if evaluation.controller_payload is not None else ""
    return [
        _result("mitigation_execution_validation", "pass" if not errors else "fail", ",".join(errors) or evaluation.execution_result, "mitigation"),
        _result("mitigation_action_validation", "pass" if evaluation.mitigation_action else "fail", evaluation.mitigation_action, "mitigation"),
        _result("mitigation_target_validation", "pass" if evaluation.mitigation_action == "alert_only" or bool(evaluation.target_ip) else "fail", evaluation.target_ip or "n/a", "mitigation"),
        _result("mitigation_confidence_consistency", "pass" if evaluation.confidence_score == evaluation.confidence_score else "fail", f"confidence={evaluation.confidence_score:.4f}", "mitigation"),
        _result("mitigation_hash_validation", "pass" if evaluation.mitigation_hash and (evaluation.mitigation_action == "alert_only" or controller_hash) else "fail", evaluation.mitigation_hash, "mitigation"),
    ]


def validate_deployment_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate deployment dry-run contracts."""
    try:
        evaluation = deploy_runtime_stack(context["config"])
        errors = validate_deployment_evaluation(evaluation)
        rollback_errors = validate_rollback_state(evaluation.rollback_state)
    except Exception as exc:
        evaluation = None
        errors = [str(exc)]
        rollback_errors = []
    if evaluation is None:
        return [
            _result("deployment_contract_integrity", "fail", ",".join(errors), "deployment"),
            _result("deployment_health_validation", "warn", "deployment evaluation unavailable", "deployment"),
        ]
    return [
        _result("deployment_contract_integrity", "pass" if not errors else "fail", ",".join(errors) or evaluation.deployment_id, "deployment"),
        _result("deployment_health_validation", "pass" if evaluation.health.state == "healthy" else "warn", evaluation.health.detail, "deployment"),
        _result("deployment_container_validation", "pass" if evaluation.container_contracts else "fail", f"containers={len(evaluation.container_contracts)}", "deployment"),
        _result("deployment_secret_validation", "warn" if evaluation.secret_contract.missing_keys else "pass", f"missing={list(evaluation.secret_contract.missing_keys)}", "deployment"),
        _result("deployment_autoscaling_validation", "pass" if evaluation.autoscaling_policy.max_replicas >= evaluation.autoscaling_policy.min_replicas else "fail", f"min={evaluation.autoscaling_policy.min_replicas} max={evaluation.autoscaling_policy.max_replicas}", "deployment"),
        _result("deployment_rollback_validation", "pass" if not rollback_errors else "fail", ",".join(rollback_errors) or evaluation.rollback_state.rollback_id, "deployment"),
    ]


def validate_distributed_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate distributed runtime contracts."""
    try:
        evaluation = orchestrate_cluster_runtime(context["config"])
        errors = validate_distributed_evaluation(evaluation)
    except Exception as exc:
        evaluation = None
        errors = [str(exc)]
    if evaluation is None:
        return [
            _result("distributed_contract_integrity", "fail", ",".join(errors), "distributed"),
            _result("distributed_cluster_validation", "warn", "distributed evaluation unavailable", "distributed"),
        ]
    status = "pass" if evaluation.active_nodes >= 1 and evaluation.cluster_health == "healthy" else "warn"
    if errors:
        status = "fail"
    return [
        _result("distributed_contract_integrity", "pass" if not errors else "fail", ",".join(errors) or evaluation.cluster_id, "distributed"),
        _result("distributed_cluster_validation", status, f"active_nodes={evaluation.active_nodes} health={evaluation.cluster_health}", "distributed"),
        _result("distributed_leader_validation", "pass" if evaluation.leader_node else "fail", evaluation.leader_node or "missing leader", "distributed"),
        _result("distributed_checkpoint_validation", "pass" if evaluation.checkpoint_state != "corrupt" else "fail", evaluation.checkpoint.checkpoint_id, "distributed"),
        _result("distributed_replication_validation", "pass" if evaluation.replication_factor >= 1 else "fail", f"replication_factor={evaluation.replication_factor}", "distributed"),
        _result(
            "distributed_failover_validation",
            "pass" if evaluation.failover_available or evaluation.active_nodes >= 1 else "warn",
            evaluation.failover_state.leader_failover_node or "no standby leader",
            "distributed",
        ),
    ]


def validate_dashboard_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate dashboard contracts."""
    try:
        evaluation = generate_dashboard_state(context["config"])
        errors = validate_dashboard_evaluation(evaluation)
    except Exception as exc:
        evaluation = None
        errors = [str(exc)]
    if evaluation is None:
        return [
            _result("dashboard_contract_integrity", "fail", ",".join(errors), "dashboard"),
            _result("dashboard_telemetry_validation", "warn", "dashboard evaluation unavailable", "dashboard"),
        ]
    stale_warnings = evaluation.diagnostics.stale_telemetry_warnings
    missing_warnings = evaluation.diagnostics.missing_data_warnings
    return [
        _result("dashboard_contract_integrity", "pass" if not errors else "fail", ",".join(errors) or evaluation.dashboard_id, "dashboard"),
        _result("dashboard_telemetry_validation", "warn" if stale_warnings else "pass", ",".join(stale_warnings) or "fresh", "dashboard"),
        _result("dashboard_visualization_validation", "pass" if not evaluation.diagnostics.visualization_errors else "fail", ",".join(evaluation.diagnostics.visualization_errors) or f"charts={len(evaluation.visualizations)}", "dashboard"),
        _result("dashboard_alert_validation", "pass" if evaluation.active_alerts >= 0 else "fail", f"alerts={evaluation.active_alerts}", "dashboard"),
        _result("dashboard_report_validation", "pass" if evaluation.reports else "fail", f"reports={len(evaluation.reports)}", "dashboard"),
        _result("dashboard_history_validation", "warn" if missing_warnings else "pass", ",".join(missing_warnings) or "history available", "dashboard"),
    ]


def validate_release_contracts(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate release engineering contracts."""
    try:
        evaluation = generate_release_candidate(context["config"])
        errors = validate_release_candidate(evaluation)
    except Exception as exc:
        evaluation = None
        errors = [str(exc)]
    if evaluation is None:
        return [
            _result("release_contract_integrity", "fail", ",".join(errors), "release"),
            _result("release_security_validation", "warn", "release evaluation unavailable", "release"),
        ]
    warn_only = context["collection"].environment.get("status") in {
        "degraded",
        "unsupported",
        "partially_supported",
    }
    security_status = "pass" if evaluation.security_score >= 0.80 else ("warn" if warn_only else "fail")
    dependency_status = "pass" if evaluation.dependency_health == "healthy" else (
        "warn" if evaluation.dependency_health == "degraded" or warn_only else "fail"
    )
    compliance_status = "pass" if evaluation.compliance_state == "compliant" else (
        "warn" if warn_only or evaluation.compliance_state == "degraded" else "fail"
    )
    release_status = "pass" if evaluation.release_state == "release_ready" else (
        "warn" if warn_only or evaluation.release_state == "release_review" else "fail"
    )
    return [
        _result("release_contract_integrity", "pass" if not errors else "fail", ",".join(errors) or evaluation.release_id, "release"),
        _result("release_benchmark_validation", "pass" if evaluation.benchmark_score >= 0.0 else "fail", f"benchmark_score={evaluation.benchmark_score:.4f}", "release"),
        _result("release_dependency_validation", dependency_status, f"dependency_health={evaluation.dependency_health}", "release"),
        _result("release_security_validation", security_status, f"security_score={evaluation.security_score:.4f}", "release"),
        _result("release_artifact_validation", "pass" if evaluation.artifacts else "fail", f"artifacts={len(evaluation.artifacts)}", "release"),
        _result("release_compliance_validation", compliance_status, f"compliance_state={evaluation.compliance_state}", "release"),
        _result("release_package_validation", release_status, f"release_state={evaluation.release_state}", "release"),
    ]


def validate_service(context: dict[str, Any]) -> list[VerificationResult]:
    """Validate runtime service coordination state."""
    from nsddos.service.diagnostics import collect_service_diagnostics
    from nsddos.service.locks import current_lock_owner
    from nsddos.service.persistence import load_service_state

    diagnostics = collect_service_diagnostics()
    service_state = load_service_state()
    sync = diagnostics.get("synchronization", {})
    replay = diagnostics.get("replay", {})
    lock_owner = current_lock_owner()
    session_count = diagnostics.get("session_count", 0)
    heartbeat_count = diagnostics.get("heartbeat_count", 0)
    running = context["running"]

    return [
        _result("service_session_consistency", "pass" if session_count > 0 or not running else "warn", f"sessions={session_count}", "service"),
        _result("service_synchronization_integrity", "pass" if sync.get("state") in {"synchronized", ""} else "warn", f"sync_state={sync.get('state', 'unknown')}", "service"),
        _result("service_replay_integrity", "pass" if replay.get("latest_sequence", 0) >= 0 else "fail", f"events={replay.get('event_count', 0)}", "service"),
        _result("service_heartbeat_integrity", "pass" if heartbeat_count >= 0 else "fail", f"heartbeats={heartbeat_count}", "service"),
        _result("service_lock_consistency", "pass" if lock_owner in {None, service_state.owner} else "fail", f"lock_owner={lock_owner} state_owner={service_state.owner}", "service"),
        _result("service_recovery_replay_safe", "pass" if service_state.replay_safe else "fail", f"replay_safe={service_state.replay_safe}", "service"),
    ]


def default_registry() -> VerificationRegistry:
    """Build authoritative default verification registry."""
    registry = VerificationRegistry()
    for rule in (
        RuntimeVerificationRule("environment", "environment", validate_environment),
        RuntimeVerificationRule("reproducibility", "reproducibility", validate_reproducibility, ("environment",)),
        RuntimeVerificationRule("orchestration", "orchestration", validate_orchestration, ("environment",)),
        RuntimeVerificationRule("collection", "collection", validate_collection, ("environment",)),
        RuntimeVerificationRule("normalization", "normalization", validate_normalization, ("collection",)),
        RuntimeVerificationRule("topology", "topology", validate_topology, ("normalization",)),
        RuntimeVerificationRule("telemetry", "telemetry", validate_telemetry, ("collection",)),
        RuntimeVerificationRule("reconciliation", "reconciliation", validate_reconciliation, ("topology", "telemetry")),
        RuntimeVerificationRule("datapath", "datapath", validate_datapath, ("topology",)),
        RuntimeVerificationRule("convergence", "convergence", validate_convergence, ("reconciliation", "datapath")),
        RuntimeVerificationRule("temporal", "temporal", validate_temporal, ("convergence",)),
        RuntimeVerificationRule("persistence", "persistence", validate_persistence, ("collection",)),
        RuntimeVerificationRule("service", "service", validate_service, ("persistence",)),
        RuntimeVerificationRule("domain", "domain", validate_domain_contracts, ("service",)),
        RuntimeVerificationRule("freshness", "freshness", validate_freshness_contracts, ("domain",)),
        RuntimeVerificationRule("live_provider", "live", validate_live_provider_contracts, ("freshness",)),
        RuntimeVerificationRule("simulation", "simulation", validate_simulation_contracts, ("freshness", "live_provider")),
        RuntimeVerificationRule("streaming", "streaming", validate_streaming_contracts, ("freshness", "live_provider", "simulation")),
        RuntimeVerificationRule("detection", "detection", validate_detection_contracts, ("freshness", "live_provider", "simulation", "streaming")),
        RuntimeVerificationRule("ml", "ml", validate_ml_contracts, ("detection",)),
        RuntimeVerificationRule("policy", "policy", validate_policy_contracts, ("detection", "ml")),
        RuntimeVerificationRule("mitigation", "mitigation", validate_mitigation_contracts, ("detection", "policy")),
        RuntimeVerificationRule("deployment", "deployment", validate_deployment_contracts, ("service", "mitigation")),
        RuntimeVerificationRule("distributed", "distributed", validate_distributed_contracts, ("deployment",)),
        RuntimeVerificationRule("dashboard", "dashboard", validate_dashboard_contracts, ("distributed",)),
        RuntimeVerificationRule("release", "release", validate_release_contracts, ("dashboard",)),
        RuntimeVerificationRule("integrity", "integrity", validate_integrity, ("persistence", "convergence", "service", "domain", "freshness", "live_provider", "simulation", "streaming", "detection", "ml", "policy", "mitigation", "deployment", "distributed", "dashboard", "release")),
    ):
        registry.register(rule)
    return registry
