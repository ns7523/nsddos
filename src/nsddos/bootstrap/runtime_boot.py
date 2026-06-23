"""Environment repair and runtime validation for startup."""

from __future__ import annotations

from nsddos.providers.docker_helper import LAB_HELPER_CONTAINER, helper_exec, helper_running
from rich.console import Console

from nsddos.bootstrap.installer import InstallerRunResult, execute_install_plan
from nsddos.bootstrap.planner import build_dependency_plan
from nsddos.bootstrap.profiles import LOCAL_DEVELOPMENT
from nsddos.bootstrap.setup import collect_environment_scan
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE, REQUIRED_STARTUP_REQUIREMENTS
from nsddos.bootstrap.state import EnvironmentScan
from nsddos.health import collect_runtime_health
from nsddos.runtime.models import HealthResult


def ensure_startup_prerequisites(console: Console) -> tuple[EnvironmentScan, InstallerRunResult]:
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


def _helper_check(name: str, command: list[str], detail: str) -> HealthResult:
    """Run startup health check inside lab helper container."""

    result = helper_exec(command, timeout=10)
    output = (result.stdout or result.stderr or detail).strip()
    return HealthResult(
        name=name,
        ok=result.returncode == 0,
        detail=output or detail,
        category="runtime",
    )


def validate_runtime_health() -> tuple[tuple[HealthResult, ...], tuple[str, ...]]:
    """Validate required runtime health checks."""

    runtime_results = tuple(collect_runtime_health())
    if helper_running():
        runtime_by_name = {result.name: result for result in runtime_results}
        results = tuple(
            result
            for name in ("docker_daemon", "containers", "floodlight", "sflowrt")
            if (result := runtime_by_name.get(name)) is not None
        ) + (
            _helper_check("mininet", ["mn", "--version"], f"{LAB_HELPER_CONTAINER}: mn --version"),
            _helper_check("ovs", ["ovs-vsctl", "show"], f"{LAB_HELPER_CONTAINER}: ovs-vsctl show"),
        )
    else:
        results = runtime_results
    failures = tuple(
        result.name
        for result in results
        if result.name in DEFAULT_STARTUP_PROFILE.required_health_checks and not result.ok
    )
    return results, failures
