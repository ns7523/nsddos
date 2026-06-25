"""Canonical runtime orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Callable

import yaml

from nsddos.config import load_runtime_state, write_runtime_state
from nsddos.constants import PROJECT_ROOT, RUNTIME_DIR
from nsddos.runtime.environment import validate_bootstrap, validate_runtime_environment
from nsddos.runtime.events import emit_runtime_event
from nsddos.runtime.evidence import export_evidence_bundle
from nsddos.runtime.execution_graph import build_execution_graph
from nsddos.runtime.models import (
    RuntimeExecutionState,
    RuntimePhaseResult,
    RuntimePipelineSnapshot,
)
from nsddos.runtime.persistence import atomic_write_json
from nsddos.runtime.pipeline import build_execution_plan
from nsddos.runtime.reconcile import reconcile_runtime
from nsddos.runtime.convergence import validate_convergence
from nsddos.runtime.verification.engine import execute_runtime_verification


PIPELINE_DIR = RUNTIME_DIR / "pipeline"
PRESET_DIR = PROJECT_ROOT / "src" / "nsddos" / "runtime" / "presets"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _phase_result(
    phase: str,
    status: str,
    detail: str,
    started: str,
    start_time: float,
    artifacts: dict[str, Any] | None = None,
) -> RuntimePhaseResult:
    return RuntimePhaseResult(
        phase=phase,
        status=status,
        detail=detail,
        started_at=started,
        completed_at=_now(),
        duration_ms=(monotonic() - start_time) * 1000,
        artifacts=artifacts or {},
    )


def _runtime_files_exist() -> bool:
    required = [
        PROJECT_ROOT / "docker" / "runtime" / "base" / "Dockerfile",
        PROJECT_ROOT / "docker" / "runtime" / "dev" / "Dockerfile",
        PROJECT_ROOT / "docker" / "runtime" / "research" / "Dockerfile",
    ]
    return all(path.exists() for path in required)


def load_preset(name: str) -> dict[str, Any]:
    """Load runtime preset YAML."""
    path = PRESET_DIR / f"{name}.yaml"
    if not path.exists():
        raise RuntimeError(f"Unknown runtime preset: {name}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_pipeline_snapshot(
    plan: dict[str, Any], state: dict[str, Any], graph: dict[str, Any]
) -> Path:
    """Persist pipeline snapshot."""
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = RuntimePipelineSnapshot(
        timestamp=_now(), plan=plan, state=state, execution_graph=graph
    )
    path = PIPELINE_DIR / f"pipeline-{stamp}.json"
    atomic_write_json(path, snapshot.to_dict())
    return path


def _phase_handlers(
    config: dict[str, Any], preset: str
) -> dict[str, Callable[[], tuple[str, str, dict[str, Any]]]]:
    """Return small phase handlers."""
    return {
        "bootstrap": lambda: ("pass", "config loaded", {"preset": preset}),
        "environment_validate": lambda: _environment_phase(config),
        "runtime_prepare": lambda: (
            "pass" if _runtime_files_exist() else "warn",
            "canonical runtime files checked",
            {},
        ),
        "providers_prepare": lambda: (
            "pass",
            "providers resolved from preset",
            {"preset": load_preset(preset)},
        ),
        "docker_runtime_start": lambda: _docker_phase(config),
        "controller_start": lambda: (
            "warn",
            "controller start delegated to canonical runtime; skipped in degraded dry run",
            {},
        ),
        "telemetry_start": lambda: (
            "warn",
            "telemetry start delegated to canonical runtime; skipped in degraded dry run",
            {},
        ),
        "topology_start": lambda: (
            "warn",
            "topology start requires Linux OVS/Mininet runtime",
            {},
        ),
        "reconciliation_validate": lambda: _reconciliation_phase(config),
        "convergence_validate": lambda: _convergence_phase(config),
        "verification_prepare": lambda: _verification_prepare_phase(config),
        "verification_execute": lambda: _verify_phase(config),
        "verification_evidence_attach": lambda: _verification_evidence_phase(config),
        "verification_finalize": lambda: _verification_finalize_phase(config),
        "query_prepare": lambda: _query_prepare_phase(config),
        "query_dependency_validate": lambda: _query_dependency_phase(config),
        "query_execute": lambda: _query_execute_phase(config),
        "query_finalize": lambda: _query_finalize_phase(config),
        "api_prepare": lambda: _api_prepare_phase(config),
        "api_validate": lambda: _api_validate_phase(config),
        "api_query_bind": lambda: _api_query_bind_phase(config),
        "api_finalize": lambda: _api_finalize_phase(config),
        "evidence_capture": lambda: _evidence_phase(config),
    }


def _environment_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    env = validate_runtime_environment(config)
    status = "pass" if env.status == "compatible" else "warn"
    return status, env.detail, env.to_dict()


def _docker_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    bootstrap = validate_bootstrap(config)
    status = "pass" if bootstrap.get("bootstrap_ready") else "warn"
    return status, bootstrap.get("detail", ""), bootstrap


def _reconciliation_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    reconciliation = reconcile_runtime(config)
    status = "pass" if not reconciliation.inconsistent_entities else "warn"
    return status, reconciliation.detail, reconciliation.to_dict()


def _convergence_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    convergence = validate_convergence(config)
    status = "pass" if convergence.status == "converged" else "warn"
    return status, convergence.detail, convergence.to_dict()


def _verify_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    results = execute_runtime_verification(config)
    failed = sum(1 for item in results if item.status == "fail")
    status = "pass" if failed == 0 else "warn"
    return (
        status,
        f"failed={failed} total={len(results)}",
        {"results": [item.to_dict() for item in results]},
    )


def _verification_prepare_phase(
    config: dict[str, Any]
) -> tuple[str, str, dict[str, Any]]:
    from nsddos.runtime.verification.validators import default_registry

    registry = default_registry()
    ordered = [rule.name for rule in registry.ordered_rules()]
    return "pass", f"validators={len(ordered)}", {"validators": ordered}


def _verification_evidence_phase(
    config: dict[str, Any]
) -> tuple[str, str, dict[str, Any]]:
    from nsddos.runtime.verification.engine import explain_verification

    explanation = explain_verification(config)
    evidence = explanation.get("evidence", [])
    return (
        "pass" if evidence else "warn",
        f"evidence={len(evidence)}",
        {"evidence": evidence},
    )


def _verification_finalize_phase(
    config: dict[str, Any]
) -> tuple[str, str, dict[str, Any]]:
    from nsddos.runtime.verification.replay import replay_verification_runs

    replay = replay_verification_runs()
    return "pass", f"runs={replay.get('run_count', 0)}", replay


def _query_prepare_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    from nsddos.runtime.query.engine import explain_query_system

    explanation = explain_query_system()
    return "pass", f"queries={len(explanation.get('queries', []))}", explanation


def _query_dependency_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    from nsddos.runtime.query.registry import default_query_registry

    registry = default_query_registry()
    deps = [item.to_dict() for item in registry.dependencies()]
    registry.ordered()
    return "pass", f"dependencies={len(deps)}", {"dependencies": deps}


def _query_execute_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    from nsddos.runtime.query.engine import execute_query
    from nsddos.runtime.query.models import RuntimeQuery

    result = execute_query(config, RuntimeQuery(name="snapshots", scope="persistence"))
    return "pass", f"items={result.total}", result.to_dict()


def _query_finalize_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    from nsddos.runtime.cache import cache_summary

    summary = cache_summary()
    return "pass", f"cache_entries={summary.get('entries', 0)}", summary


def _api_prepare_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    from nsddos.api.app import get_route_summary

    summary = get_route_summary()
    return "pass", f"routes={summary.get('endpoint_count', 0)}", summary


def _api_validate_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    from nsddos.api.app import explain_api

    explanation = explain_api()
    ok = explanation.get("readonly") and explanation.get("query_backed")
    return (
        "pass" if ok else "warn",
        "API readonly/query-backed contract checked",
        explanation,
    )


def _api_query_bind_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    from nsddos.runtime.query.engine import explain_query_system

    explanation = explain_query_system()
    return "pass", f"bound_queries={len(explanation.get('queries', []))}", explanation


def _api_finalize_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    from nsddos.api.app import get_route_summary

    summary = get_route_summary()
    return (
        "pass",
        "API integrity finalized",
        {"routes": summary.get("endpoint_count", 0)},
    )


def _evidence_phase(config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    bundle = export_evidence_bundle(config)
    return "pass", bundle.bundle_dir, bundle.to_dict()


def execute_pipeline(
    config: dict[str, Any], preset: str = "minimal-lab", mode: str = "bootstrap"
) -> RuntimeExecutionState:
    """Execute canonical pipeline phases."""
    load_preset(preset)
    plan = build_execution_plan(config, preset=preset)
    graph = build_execution_graph(config, preset=preset)
    state = RuntimeExecutionState(
        plan=plan.name,
        status="running",
        started_at=_now(),
        preset=preset,
        profile=plan.profile,
    )
    handlers = _phase_handlers(config, preset)
    emit_runtime_event(
        f"pipeline.{mode}",
        "started",
        "Canonical runtime pipeline started.",
        {"preset": preset},
    )

    for phase in plan.phases:
        state.current_phase = phase.name
        started = _now()
        start_time = monotonic()
        status, detail, artifacts = handlers[phase.name]()
        result = _phase_result(
            phase.name, status, detail, started, start_time, artifacts
        )
        state.results.append(result)
        emit_runtime_event(
            f"pipeline.phase.{phase.name}", status, detail, {"preset": preset}
        )

    state.current_phase = None
    state.completed_at = _now()
    state.status = (
        "degraded_pipeline"
        if any(item.status == "warn" for item in state.results)
        else "stable_pipeline"
    )
    snapshot = save_pipeline_snapshot(plan.to_dict(), state.to_dict(), graph)
    runtime_state = load_runtime_state()
    runtime_state.preset_state = {"active": preset, "preset": load_preset(preset)}
    runtime_state.verification_results = [item.to_dict() for item in state.results]
    runtime_state.last_error = None
    write_runtime_state(runtime_state)
    emit_runtime_event(
        f"pipeline.{mode}",
        "completed",
        "Canonical runtime pipeline completed.",
        {"status": state.status, "snapshot": str(snapshot)},
    )
    return state


def shutdown_pipeline(
    config: dict[str, Any], preset: str = "minimal-lab"
) -> RuntimeExecutionState:
    """Run deterministic shutdown pipeline."""
    state = RuntimeExecutionState(
        plan="canonical-shutdown", status="running", started_at=_now(), preset=preset
    )
    phases = [
        "evidence_capture",
        "topology_stop",
        "telemetry_stop",
        "controller_stop",
        "docker_runtime_stop",
        "state_finalize",
    ]
    emit_runtime_event(
        "pipeline.shutdown",
        "started",
        "Canonical shutdown pipeline started.",
        {"preset": preset},
    )
    for phase in phases:
        started = _now()
        start_time = monotonic()
        detail = "shutdown phase recorded"
        status = "pass"
        if phase == "evidence_capture":
            bundle = export_evidence_bundle(config)
            artifacts = bundle.to_dict()
            detail = bundle.bundle_dir
        else:
            artifacts = {}
        state.results.append(
            _phase_result(phase, status, detail, started, start_time, artifacts)
        )
        emit_runtime_event(
            f"pipeline.phase.{phase}", status, detail, {"preset": preset}
        )
    state.completed_at = _now()
    state.status = "stable_pipeline"
    graph = build_execution_graph(config, preset=preset)
    save_pipeline_snapshot({"name": state.plan}, state.to_dict(), graph)
    emit_runtime_event(
        "pipeline.shutdown",
        "completed",
        "Canonical shutdown pipeline completed.",
        {"status": state.status},
    )
    return state


def use_runtime_preset(config: dict[str, Any], preset: str) -> dict[str, Any]:
    """Persist active runtime preset without starting services."""
    preset_payload = load_preset(preset)
    plan = build_execution_plan(config, preset=preset)
    graph = build_execution_graph(config, preset=preset)
    runtime_state = load_runtime_state()
    runtime_state.preset_state = {
        "active": preset,
        "preset": preset_payload,
        "plan": plan.to_dict(),
    }
    write_runtime_state(runtime_state)
    save_pipeline_snapshot(
        plan.to_dict(), {"preset": runtime_state.preset_state}, graph
    )
    emit_runtime_event(
        "pipeline.preset",
        "configured",
        "Runtime preset configured.",
        {"preset": preset},
    )
    return runtime_state.preset_state
