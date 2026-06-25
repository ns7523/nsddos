"""Static and runtime health report facade."""

from __future__ import annotations

from nsddos.health_checks import (
    check_compose_file,
    check_config_valid,
    check_dependency_validation,
    check_docker_daemon,
    check_docker_installed,
    check_port_availability,
    check_runtime_directories,
    collect_runtime_health,
    collect_static_health,
    validate_runtime_bootstrap,
)
from nsddos.runtime.models import HealthResult


def get_health_report(
    verbose: bool = False,
) -> dict[str, list[HealthResult] | dict[str, bool]]:
    """Return grouped health report."""

    static_results = collect_static_health()
    runtime_results = collect_runtime_health()
    if not verbose:
        flat = {
            result.name: result.ok for result in [*static_results, *runtime_results]
        }
        return {"flat": flat}
    return {
        "static": static_results,
        "runtime": runtime_results,
    }


__all__ = [
    "check_compose_file",
    "check_config_valid",
    "check_dependency_validation",
    "check_docker_daemon",
    "check_docker_installed",
    "check_port_availability",
    "check_runtime_directories",
    "collect_runtime_health",
    "collect_static_health",
    "get_health_report",
    "validate_runtime_bootstrap",
]
