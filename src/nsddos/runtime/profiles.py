"""Canonical runtime profile definitions."""

from __future__ import annotations

from nsddos.runtime.capabilities import detect_runtime_capabilities
from nsddos.runtime.models import RuntimeProfile
from nsddos.providers.docker_helper import helper_running


PROFILE_DEFINITIONS: dict[str, RuntimeProfile] = {
    "linux-native": RuntimeProfile(
        name="linux-native",
        platform="linux",
        description="Canonical Linux host with local Docker, OVS, Mininet, Floodlight compatibility.",
        required_services=["docker", "ovs", "mininet", "java"],
        supported_capabilities=["docker", "ovs", "mininet", "openflow", "sflow"],
        runtime_limitations=[],
        verification_expectations=["full-runtime", "controller", "telemetry", "datapath"],
        provider_availability={"floodlight": "full", "sflowrt": "full", "ovs": "full", "mininet": "full"},
        privilege_requirements=["root-or-passwordless-sudo"],
    ),
    "docker-linux": RuntimeProfile(
        name="docker-linux",
        platform="linux",
        description="Linux host with canonical Docker runtime, partial host SDN support.",
        required_services=["docker", "java"],
        supported_capabilities=["docker", "container-networking", "sflow"],
        runtime_limitations=["host-ovs-required-for-full-datapath", "host-mininet-required-for-full-topology"],
        verification_expectations=["container-runtime", "controller", "telemetry"],
        provider_availability={"floodlight": "full", "sflowrt": "full", "ovs": "partial", "mininet": "partial"},
        privilege_requirements=["docker-access"],
    ),
    "wsl2": RuntimeProfile(
        name="wsl2",
        platform="linux",
        description="WSL2 runtime. Good for CLI, partial for SDN lab unless nested networking tuned.",
        required_services=["docker"],
        supported_capabilities=["docker", "container-networking"],
        runtime_limitations=["ovs-often-partial", "mininet-often-degraded", "kernel-networking-varies"],
        verification_expectations=["degraded-runtime", "reproducibility", "telemetry"],
        provider_availability={"floodlight": "full", "sflowrt": "full", "ovs": "partial", "mininet": "partial"},
        privilege_requirements=["docker-access", "sudo-for-host-networking"],
    ),
    "macos-degraded": RuntimeProfile(
        name="macos-degraded",
        platform="darwin",
        description="macOS diagnostic/runtime-export mode. Not canonical for full SDN lab.",
        required_services=["docker"],
        supported_capabilities=["docker"],
        runtime_limitations=["no-native-mininet", "no-native-ovs-datapath", "telemetry-truth-degraded"],
        verification_expectations=["diagnostics", "exports", "degraded-verify"],
        provider_availability={"floodlight": "partial", "sflowrt": "partial", "ovs": "unsupported", "mininet": "unsupported"},
        privilege_requirements=["docker-access"],
    ),
}


def detect_runtime_profile() -> RuntimeProfile:
    """Detect best matching runtime profile without mutating config."""
    caps = detect_runtime_capabilities()
    helper = caps.docker_daemon and helper_running()
    if caps.platform == "darwin" and helper:
        profile = PROFILE_DEFINITIONS["docker-linux"]
    elif caps.platform == "darwin":
        profile = PROFILE_DEFINITIONS["macos-degraded"]
    elif caps.wsl2:
        profile = PROFILE_DEFINITIONS["wsl2"]
    elif caps.linux_kernel and caps.docker_daemon and caps.ovs_installed and caps.mininet_supported:
        profile = PROFILE_DEFINITIONS["linux-native"]
    elif caps.linux_kernel and caps.docker_daemon:
        profile = PROFILE_DEFINITIONS["docker-linux"]
    elif caps.linux_kernel:
        profile = PROFILE_DEFINITIONS["docker-linux"]
    else:
        profile = PROFILE_DEFINITIONS["macos-degraded"]

    detected = RuntimeProfile(**profile.to_dict())
    detected.detected = True
    if helper and detected.name == "docker-linux":
        detected.runtime_limitations = []
        detected.provider_availability = {
            "floodlight": "full",
            "sflowrt": "full",
            "ovs": "full",
            "mininet": "full",
        }
        detected.verification_expectations = ["full-runtime", "controller", "telemetry", "datapath"]
    detected.detail = f"platform={caps.platform} wsl2={caps.wsl2} docker={caps.docker_daemon} helper={helper}"
    return detected
