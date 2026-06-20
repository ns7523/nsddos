"""Canonical runtime pipeline definition."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.dependencies import canonical_dependencies, resolve_phase_order
from nsddos.runtime.models import RuntimeExecutionPlan, RuntimePhase
from nsddos.runtime.profiles import detect_runtime_profile


PHASE_PROVIDERS = {
    "docker_runtime_start": ["docker"],
    "controller_start": ["floodlight"],
    "telemetry_start": ["sflowrt"],
    "topology_start": ["mininet", "ovs"],
    "reconciliation_validate": ["floodlight", "sflowrt", "mininet", "ovs"],
    "verification_execute": ["floodlight", "sflowrt", "mininet", "ovs"],
    "service_start": ["service"],
    "service_sync": ["service"],
    "service_validate": ["service"],
}


PHASE_GATES = {
    "bootstrap": "config",
    "environment_validate": "profile_compatibility",
    "runtime_prepare": "canonical_runtime_files",
    "providers_prepare": "provider_compatibility",
    "docker_runtime_start": "docker_daemon",
    "controller_start": "controller_readiness",
    "telemetry_start": "telemetry_readiness",
    "topology_start": "topology_readiness",
    "reconciliation_validate": "runtime_reconciliation",
    "convergence_validate": "runtime_convergence",
    "verification_prepare": "verification_registry",
    "verification_execute": "verification_engine",
    "verification_evidence_attach": "verification_evidence",
    "verification_finalize": "verification_integrity",
    "query_prepare": "query_registry",
    "query_dependency_validate": "query_dependencies",
    "query_execute": "query_engine",
    "query_finalize": "query_integrity",
    "api_prepare": "api_routes",
    "api_validate": "api_schema",
    "api_query_bind": "api_query_engine_binding",
    "api_finalize": "api_integrity",
    "service_prepare": "service_registry",
    "service_start": "service_lifecycle",
    "service_sync": "service_synchronization",
    "service_validate": "service_verification",
    "service_finalize": "service_integrity",
    "evidence_capture": "evidence",
}


def build_execution_plan(config: dict[str, Any], preset: str = "minimal-lab") -> RuntimeExecutionPlan:
    """Build canonical execution plan."""
    profile = detect_runtime_profile()
    phases = [
        RuntimePhase(
            name=name,
            dependencies=[dep.source for dep in canonical_dependencies() if dep.target == name],
            providers=PHASE_PROVIDERS.get(name, []),
            gate=PHASE_GATES.get(name, ""),
            required=name not in {"topology_start"} or preset in {"controller-lab", "reproducibility-lab"},
        )
        for name in resolve_phase_order()
    ]
    return RuntimeExecutionPlan(
        name="canonical-sdn-lab",
        phases=phases,
        dependencies=canonical_dependencies(),
        preset=preset,
        profile=profile.name,
    )
