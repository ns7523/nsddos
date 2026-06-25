"""Static and runtime health checks."""

from __future__ import annotations

from pathlib import Path
from shutil import which
import subprocess

from nsddos.bootstrap.assets import detect_runtime_asset_status
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.config import ensure_runtime_directories, load_config, load_runtime_state
from nsddos.constants import MININET_BIN, get_compose_file, get_floodlight_jar, get_sflowrt_jar
from nsddos.docker_manager import DockerManager
from nsddos.providers.docker_helper import LAB_HELPER_CONTAINER, helper_exec, helper_running
from nsddos.providers.floodlight.provider import FloodlightProvider
from nsddos.providers.mininet.provider import MininetProvider
from nsddos.providers.ovs.provider import OVSProvider
from nsddos.providers.sflow.provider import SFlowProvider
from nsddos.runtime.models import HealthResult


def check_docker_installed() -> bool:
    """Placeholder Docker availability check."""
    return which("docker") is not None


def check_docker_daemon() -> bool:
    """Check Docker daemon availability."""
    if not check_docker_installed():
        return False
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def check_compose_file() -> bool:
    """Check Docker Compose file availability."""
    return get_compose_file().exists()


def check_runtime_directories() -> list[Path]:
    """Ensure runtime directories exist."""
    return list(ensure_runtime_directories())


def check_config_valid() -> bool:
    """Config validation check."""
    config = load_config()
    return isinstance(config, dict) and "api_port" in config and "lab" in config


def check_port_availability() -> bool:
    """Placeholder port availability check."""
    return True


def check_dependency_validation() -> bool:
    """Placeholder dependency validation check."""
    return True


def _helper_command(args: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str] | None:
    """Run helper command when labhost container is available."""
    if not helper_running():
        return None
    return helper_exec(args, timeout=timeout)


def _helper_mininet_binary() -> tuple[bool, str]:
    """Return helper Mininet binary availability."""
    result = _helper_command(["which", "mn"])
    if result is None:
        return False, str(MININET_BIN)
    path = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, path or f"{LAB_HELPER_CONTAINER}: which mn"


def _helper_ovs_ready() -> tuple[bool, str]:
    """Return helper OVS readiness."""
    result = _helper_command(["ovs-vsctl", "show"])
    if result is None:
        return False, "ovs-vsctl available"
    detail = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, detail or f"{LAB_HELPER_CONTAINER}: ovs-vsctl show"


def _service_aliases(name: str) -> set[str]:
    """Return service/container aliases for matching."""
    aliases = {name}
    if name.startswith("nsddos-"):
        aliases.add(name.removeprefix("nsddos-"))
    else:
        aliases.add(f"nsddos-{name}")
    return aliases


def _required_container_health(services) -> tuple[bool, str]:
    """Return health for required NSDDOS stack containers only."""
    required = DEFAULT_STARTUP_PROFILE.container_names
    details: list[str] = []
    healthy = True
    for required_name in required:
        matched = next(
            (service for service in services if required_name in _service_aliases(service.name)),
            None,
        )
        if matched is None:
            healthy = False
            details.append(f"{required_name}:missing")
            continue
        state = matched.detail or matched.status
        details.append(f"{required_name}:{state}")
        if not matched.healthy:
            healthy = False
    return healthy and bool(services), ", ".join(details) or "no containers"


def collect_static_health() -> list[HealthResult]:
    """Collect non-runtime-dependent checks."""
    helper_mininet_ok, helper_mininet_detail = _helper_mininet_binary()
    helper_ovs_ok, helper_ovs_detail = _helper_ovs_ready()
    asset_status = detect_runtime_asset_status()
    compose_file = get_compose_file()
    floodlight_jar = get_floodlight_jar()
    sflowrt_jar = get_sflowrt_jar()
    return [
        HealthResult("docker", check_docker_installed(), "docker CLI available", "static"),
        HealthResult("compose", check_compose_file(), str(compose_file), "static"),
        HealthResult("config", check_config_valid(), "config schema loaded", "static"),
        HealthResult(
            "runtime_dirs",
            bool(check_runtime_directories()),
            "runtime directories bootstrapped",
            "static",
        ),
        HealthResult(
            "floodlight_artifact",
            floodlight_jar.exists(),
            str(floodlight_jar),
            "static",
        ),
        HealthResult(
            "sflowrt_artifact",
            sflowrt_jar.exists(),
            str(sflowrt_jar),
            "static",
        ),
        HealthResult("runtime_assets", asset_status.ready, asset_status.detail, "static"),
        HealthResult(
            "mininet_binary",
            MININET_BIN.exists() or which("mn") is not None or helper_mininet_ok,
            helper_mininet_detail,
            "static",
        ),
        HealthResult(
            "ovs_vswitch",
            OVSProvider.is_installed() or helper_ovs_ok,
            helper_ovs_detail,
            "static",
        ),
    ]


def collect_runtime_health() -> list[HealthResult]:
    """Collect live runtime checks."""
    docker = DockerManager()
    floodlight = FloodlightProvider()
    sflow = SFlowProvider()
    mininet = MininetProvider()
    ovs = OVSProvider()
    services = docker.get_service_states()
    containers_ok, containers_detail = _required_container_health(services)
    mininet_status = mininet.status()
    ovs_status = ovs.status()
    helper_mininet_ok, helper_mininet_detail = _helper_mininet_binary()
    helper_ovs_ok, helper_ovs_detail = _helper_ovs_ready()
    if helper_running():
        mininet_ok = helper_mininet_ok and bool(mininet_status.get("controller_reachable"))
        mininet_detail = f"{helper_mininet_detail} controller={mininet_status.get('controller')}"
        ovs_ok = helper_ovs_ok and bool(ovs_status.get("ready"))
        ovs_detail = helper_ovs_detail or ovs_status.get("detail", "")
    else:
        runtime_state = load_runtime_state()
        mininet_ok = runtime_state.topology_state == "running" and bool(mininet_status.get("running"))
        mininet_detail = str(mininet_status.get("controller", ""))
        ovs_ok = ovs.service_running() and bool(ovs.list_bridges())
        ovs_detail = f"bridges={len(ovs.list_bridges())}"
    return [
        HealthResult("docker_daemon", check_docker_daemon(), "docker daemon reachable", "runtime"),
        HealthResult(
            "containers",
            containers_ok,
            containers_detail,
            "runtime",
        ),
        HealthResult(
            "floodlight",
            bool(floodlight.status()["reachable"]),
            floodlight.status()["endpoint"],
            "runtime",
        ),
        HealthResult(
            "sflowrt",
            bool(sflow.status()["reachable"]),
            sflow.status()["endpoint"],
            "runtime",
        ),
        HealthResult(
            "mininet",
            mininet_ok,
            mininet_detail,
            "runtime",
        ),
        HealthResult(
            "ovs",
            ovs_ok,
            ovs_detail,
            "runtime",
        ),
    ]


def validate_runtime_bootstrap() -> dict[str, bool]:
    """Return compatibility bootstrap map."""
    results = collect_static_health()
    return {result.name: result.ok for result in results}


def get_health_report(verbose: bool = False) -> dict[str, list[HealthResult] | dict[str, bool]]:
    """Return grouped health report."""
    static_results = collect_static_health()
    runtime_results = collect_runtime_health()
    if not verbose:
        flat = {result.name: result.ok for result in [*static_results, *runtime_results]}
        return {"flat": flat}
    return {
        "static": static_results,
        "runtime": runtime_results,
    }
