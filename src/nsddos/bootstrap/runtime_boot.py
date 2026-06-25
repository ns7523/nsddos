"""Environment repair and runtime validation for startup."""

from __future__ import annotations

from rich.console import Console

from nsddos.bootstrap.installer import InstallerRunResult, execute_install_plan
from nsddos.bootstrap.planner import build_dependency_plan
from nsddos.bootstrap.profiles import LOCAL_DEVELOPMENT
from nsddos.bootstrap.setup import collect_environment_scan
from nsddos.bootstrap.startup_profiles import (
    DEFAULT_STARTUP_PROFILE,
    REQUIRED_STARTUP_REQUIREMENTS,
)
from nsddos.bootstrap.state import EnvironmentScan
from nsddos.health_checks import collect_runtime_health
from nsddos.runtime.models import HealthResult


def ensure_startup_prerequisites(
    console: Console,
) -> tuple[EnvironmentScan, InstallerRunResult]:
    """Auto-repair required startup prerequisites."""

    initial_scan = collect_environment_scan()
    plan = build_dependency_plan(initial_scan, LOCAL_DEVELOPMENT)
    result = execute_install_plan(
        console,
        plan,
        initial_scan,
        auto_approve_required=True,
        allowed_titles=REQUIRED_STARTUP_REQUIREMENTS,
    )
    return collect_environment_scan(), result


def validate_runtime_health() -> tuple[tuple[HealthResult, ...], tuple[str, ...]]:
    """Validate required runtime health checks."""

    runtime_results = tuple(collect_runtime_health())
    results = runtime_results
    failures = tuple(
        result.name
        for result in results
        if result.name in DEFAULT_STARTUP_PROFILE.required_health_checks
        and not result.ok
    )
    return results, failures
