"""Static and runtime health checks."""

from __future__ import annotations

from pathlib import Path
from shutil import which
import subprocess

from nsddos.config import ensure_runtime_directories, load_config, load_runtime_state
from nsddos.constants import COMPOSE_FILE, FLOODLIGHT_JAR, MININET_BIN, SFLOWRT_JAR
from nsddos.docker_manager import DockerManager
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
    return COMPOSE_FILE.exists()


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


def collect_static_health() -> list[HealthResult]:
    """Collect non-runtime-dependent checks."""
    return [
        HealthResult("docker", check_docker_installed(), "docker CLI available", "static"),
        HealthResult("compose", check_compose_file(), str(COMPOSE_FILE), "static"),
        HealthResult("config", check_config_valid(), "config schema loaded", "static"),
        HealthResult(
            "runtime_dirs",
            bool(check_runtime_directories()),
            "runtime directories bootstrapped",
            "static",
        ),
        HealthResult(
            "floodlight_artifact",
            FLOODLIGHT_JAR.exists(),
            str(FLOODLIGHT_JAR),
            "static",
        ),
        HealthResult(
            "sflowrt_artifact",
            SFLOWRT_JAR.exists(),
            str(SFLOWRT_JAR),
            "static",
        ),
        HealthResult(
            "mininet_binary",
            MININET_BIN.exists() or which("mn") is not None,
            str(MININET_BIN),
            "static",
        ),
        HealthResult(
            "ovs_vswitch",
            OVSProvider.is_installed(),
            "ovs-vsctl available",
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
    runtime_state = load_runtime_state()
    services = docker.get_service_states()
    all_services_healthy = bool(services) and all(service.healthy for service in services)
    return [
        HealthResult("docker_daemon", check_docker_daemon(), "docker daemon reachable", "runtime"),
        HealthResult(
            "containers",
            all_services_healthy,
            ", ".join(f"{service.name}:{service.status}" for service in services) or "no containers",
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
            runtime_state.topology_state == "running" and bool(mininet.status()["running"]),
            mininet.status()["controller"],
            "runtime",
        ),
        HealthResult(
            "ovs",
            ovs.service_running() and bool(ovs.list_bridges()),
            f"bridges={len(ovs.list_bridges())}",
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
