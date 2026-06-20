"""Canonical runtime dependency resolution."""

from __future__ import annotations

from nsddos.runtime.models import RuntimeDependency


PHASE_ORDER = [
    "bootstrap",
    "environment_validate",
    "runtime_prepare",
    "providers_prepare",
    "docker_runtime_start",
    "controller_start",
    "telemetry_start",
    "topology_start",
    "reconciliation_validate",
    "convergence_validate",
    "verification_prepare",
    "verification_execute",
    "verification_evidence_attach",
    "verification_finalize",
    "query_prepare",
    "query_dependency_validate",
    "query_execute",
    "query_finalize",
    "api_prepare",
    "api_validate",
    "api_query_bind",
    "api_finalize",
    "service_prepare",
    "service_start",
    "service_sync",
    "service_validate",
    "service_finalize",
    "evidence_capture",
]


def canonical_dependencies() -> list[RuntimeDependency]:
    """Return canonical phase dependencies."""
    deps = []
    for source, target in zip(PHASE_ORDER, PHASE_ORDER[1:]):
        deps.append(RuntimeDependency(source=source, target=target, reason="canonical_order"))
    deps.extend(
        [
            RuntimeDependency("controller_start", "topology_start", "controller before topology"),
            RuntimeDependency("telemetry_start", "reconciliation_validate", "telemetry before reconciliation"),
            RuntimeDependency("topology_start", "reconciliation_validate", "topology before reconciliation"),
            RuntimeDependency("reconciliation_validate", "convergence_validate", "truth before convergence"),
            RuntimeDependency("convergence_validate", "verification_prepare", "convergence before verify"),
            RuntimeDependency("verification_prepare", "verification_execute", "prepare before execute"),
            RuntimeDependency("verification_execute", "verification_evidence_attach", "verify before evidence"),
            RuntimeDependency("verification_evidence_attach", "verification_finalize", "evidence before finalize"),
            RuntimeDependency("verification_finalize", "query_prepare", "verification before query"),
            RuntimeDependency("query_prepare", "query_dependency_validate", "query prepare before dependency validation"),
            RuntimeDependency("query_dependency_validate", "query_execute", "query dependencies before execution"),
            RuntimeDependency("query_execute", "query_finalize", "query execute before finalize"),
            RuntimeDependency("query_finalize", "api_prepare", "query before API binding"),
            RuntimeDependency("api_prepare", "api_validate", "API prepare before validation"),
            RuntimeDependency("api_validate", "api_query_bind", "API validation before query binding"),
            RuntimeDependency("api_query_bind", "api_finalize", "API query binding before finalize"),
            RuntimeDependency("api_finalize", "service_prepare", "api finalized before service"),
            RuntimeDependency("service_prepare", "service_start", "service prepare before start"),
            RuntimeDependency("service_start", "service_sync", "service start before sync"),
            RuntimeDependency("service_sync", "service_validate", "service sync before validation"),
            RuntimeDependency("service_validate", "service_finalize", "service validation before finalize"),
        ]
    )
    return deps


def resolve_phase_order() -> list[str]:
    """Return deterministic topological phase order."""
    return list(PHASE_ORDER)


def dependency_validation() -> dict[str, object]:
    """Validate dependency graph shape."""
    phases = set(PHASE_ORDER)
    deps = canonical_dependencies()
    missing = [dep.to_dict() for dep in deps if dep.source not in phases or dep.target not in phases]
    return {
        "valid": not missing,
        "phase_count": len(PHASE_ORDER),
        "dependency_count": len(deps),
        "missing": missing,
    }
