"""Side-effect-light health collectors."""

from __future__ import annotations

from pathlib import Path
from shutil import which
import subprocess

from nsddos.bootstrap.assets import detect_runtime_asset_status
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.config import ensure_runtime_directories, load_config
from nsddos.constants import get_compose_file, get_floodlight_jar, get_sflowrt_jar
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


def collect_static_health() -> list[HealthResult]:
    """Collect non-runtime-dependent checks."""

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
    ]


def collect_runtime_health() -> list[HealthResult]:
    """Collect live runtime checks."""

    docker = DockerManager()
    floodlight = FloodlightProvider()
    sflow = SFlowProvider()
    mininet = MininetProvider()
    ovs = OVSProvider()
    containers_ok, containers_detail, _services = docker.stack_health(DEFAULT_STARTUP_PROFILE.container_names)
    mininet_status = mininet.status()
    ovs_status = ovs.status()
    mininet_ok = containers_ok and bool(mininet_status.get("ready"))
    mininet_detail = str(mininet_status.get("detail") or mininet_status.get("controller", ""))
    ovs_ok = containers_ok and bool(ovs_status.get("ready"))
    ovs_detail = str(ovs_status.get("detail", ""))
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

    return {result.name: result.ok for result in collect_static_health()}
