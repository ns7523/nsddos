"""Authoritative runtime verification engine."""

from __future__ import annotations

import socket
from datetime import datetime, timezone
from time import monotonic
from typing import Any
from uuid import uuid4

from nsddos.config import load_runtime_state
from nsddos.docker_manager import DockerManager
from nsddos.health_checks import collect_runtime_health, collect_static_health
from nsddos.runtime.analysis_layer import aggregate_runtime
from nsddos.runtime.cache import set_cache
from nsddos.runtime.collection_layer import collect_runtime_bundle
from nsddos.runtime.dependencies import dependency_validation
from nsddos.runtime.environment import validate_bootstrap
from nsddos.runtime.models import VerificationResult
from nsddos.runtime.pipeline import build_execution_plan
from nsddos.runtime.replay import replay_execution_history
from nsddos.runtime.verification.evidence import build_verification_evidence
from nsddos.runtime.verification.replay import persist_verification_execution, replay_verification_runs
from nsddos.runtime.verification.results import VerificationCategoryResult, VerificationExecutionResult
from nsddos.runtime.verification.validators import default_registry
from nsddos.service.manager import RuntimeServiceManager


def _socket_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check TCP reachability."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def build_verification_context(config: dict[str, Any]) -> dict[str, Any]:
    """Build verification context from collection + analysis layers."""
    service = RuntimeServiceManager(config)
    service.start(owner="verification")
    service.synchronize()
    runtime_state = load_runtime_state()
    collection = collect_runtime_bundle(config)
    aggregation = aggregate_runtime(config, collection)
    docker = DockerManager()
    active_preset = runtime_state.preset_state.get("active", "minimal-lab") if runtime_state.preset_state else "minimal-lab"
    plan = build_execution_plan(config, preset=active_preset)
    return {
        "config": config,
        "runtime_state": runtime_state,
        "running": runtime_state.stack_running,
        "collection": collection,
        "analysis": aggregation.analysis,
        "aggregation": aggregation,
        "provider_status": collection.provider_status,
        "static_checks": collect_static_health(),
        "runtime_checks": collect_runtime_health(),
        "services": docker.get_service_states(),
        "dependency_state": dependency_validation(),
        "phase_names": [phase.name for phase in plan.phases],
        "execution_plan": plan,
        "execution_replay": replay_execution_history(),
        "bootstrap": validate_bootstrap(config),
        "controller_open": _socket_reachable("127.0.0.1", config.get("lab", {}).get("controller_port", 6653)),
    }


def execute_verification(config: dict[str, Any], persist: bool = True) -> VerificationExecutionResult:
    """Execute authoritative verification run."""
    run_id = str(uuid4())
    registry = default_registry()
    start = monotonic()
    context = build_verification_context(config)
    evidence = build_verification_evidence(context)
    context["registry"] = registry
    context["evidence"] = evidence
    ordered_rules = registry.ordered_rules()
    context["validator_order"] = [rule.name for rule in ordered_rules]

    categories: dict[str, VerificationCategoryResult] = {}
    results: list[VerificationResult] = []
    performance: dict[str, float] = {}
    degraded_validators: list[str] = []

    for rule in ordered_rules:
        phase_start = monotonic()
        rule_results = registry.execute_rule(rule, context)
        duration = (monotonic() - phase_start) * 1000
        performance[f"validator.{rule.name}.ms"] = duration
        if any(result.status in {"warn", "stale"} for result in rule_results):
            degraded_validators.append(rule.name)
        results.extend(rule_results)
        bucket = categories.setdefault(rule.category, VerificationCategoryResult(rule.category))
        bucket.results.extend(rule_results)
        bucket.duration_ms += duration
        set_cache(
            "verification-validator",
            {"run_id": run_id, "validator": rule.name},
            {"results": [item.to_dict() for item in rule_results], "duration_ms": duration},
        )

    performance["verification.total.ms"] = (monotonic() - start) * 1000
    execution = VerificationExecutionResult(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        results=results,
        categories=list(categories.values()),
        validator_order=[rule.name for rule in ordered_rules],
        degraded_validators=sorted(set(degraded_validators)),
        dependency_graph=[edge.to_dict() for edge in registry.dependencies()],
        evidence=evidence,
        performance=performance,
    )
    if persist:
        persist_verification_execution(execution.to_dict())
    return execution


def execute_runtime_verification(config: dict[str, Any]) -> list[VerificationResult]:
    """Compatibility output for existing CLI and confidence code."""
    return execute_verification(config).results


def explain_verification(config: dict[str, Any]) -> dict[str, Any]:
    """Return current verification pipeline explanation."""
    execution = execute_verification(config)
    replay = replay_verification_runs()
    return {
        "execution": execution.to_dict(),
        "replay": replay,
        "categories": [category.to_dict() for category in execution.categories],
        "validator_order": execution.validator_order,
        "dependency_graph": execution.dependency_graph,
        "degraded_validators": execution.degraded_validators,
        "skipped_validators": execution.skipped_validators,
        "evidence": [item.to_dict() for item in execution.evidence],
        "performance": execution.performance,
    }
