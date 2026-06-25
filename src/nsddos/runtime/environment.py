"""Deterministic runtime environment validation."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.capabilities import detect_runtime_capabilities
from nsddos.runtime.models import EnvironmentCompatibility
from nsddos.runtime.profiles import detect_runtime_profile
from nsddos.runtime.providers_registry import build_provider_registry, collect_provider_status_from_registry


def validate_runtime_environment(config: dict[str, Any]) -> EnvironmentCompatibility:
    """Validate runtime environment compatibility."""
    profile = detect_runtime_profile()
    caps = detect_runtime_capabilities()
    providers = collect_provider_status_from_registry(build_provider_registry(config))

    supported: list[str] = []
    degraded: list[str] = []
    unsupported: list[str] = []
    missing: list[str] = []
    limits: list[str] = list(profile.runtime_limitations)
    provider_support: dict[str, str] = {}

    def mark(name: str, ok: bool, degrade: bool = False) -> None:
        if ok:
            supported.append(name)
        elif degrade:
            degraded.append(name)
        else:
            unsupported.append(name)

    mark("docker", caps.docker_daemon, degrade=caps.docker_installed)
    mark("java", caps.java_available)
    mark("ovs", caps.ovs_service, degrade=caps.ovs_installed)
    mark("mininet", caps.mininet_supported, degrade=caps.docker_daemon)
    mark("openflow", caps.openflow_compatible, degrade=caps.docker_daemon)
    mark("sflow", caps.sflow_capable, degrade=caps.docker_daemon)

    if not caps.docker_installed:
        missing.append("docker-cli")
    if not caps.docker_daemon:
        missing.append("docker-daemon")
    if not caps.java_available:
        missing.append("java")
    if not caps.ovs_service:
        limits.append("labhost-runtime-not-running")
    if not caps.mininet_supported:
        limits.append("mininet-runtime-not-running")

    for name, status in providers.items():
        if status.get("ready") or status.get("reachable") or status.get("artifact_exists"):
            provider_support[name] = "supported"
        elif status.get("installed") or status.get("artifact_exists"):
            provider_support[name] = "partial"
            degraded.append(f"provider:{name}")
        else:
            provider_support[name] = "unsupported"
            unsupported.append(f"provider:{name}")

    if unsupported:
        env_status = "unsupported"
    elif degraded or limits:
        env_status = "degraded" if supported else "partially_supported"
    else:
        env_status = "compatible"

    return EnvironmentCompatibility(
        profile=profile.name,
        status=env_status,
        supported=sorted(set(supported)),
        degraded=sorted(set(degraded)),
        unsupported=sorted(set(unsupported)),
        provider_support=provider_support,
        missing_dependencies=sorted(set(missing)),
        reproducibility_limitations=sorted(set(limits)),
        detail=f"profile={profile.name} docker={caps.docker_daemon} ovs={caps.ovs_service} mininet={caps.mininet_supported}",
    )


def validate_bootstrap(config: dict[str, Any]) -> dict[str, Any]:
    """Preflight canonical lab bootstrap viability."""
    env = validate_runtime_environment(config)
    bootstrap_ready = env.status == "compatible"
    if env.profile == "macos-degraded":
        bootstrap_ready = False
    if env.profile == "wsl2" and "sudo-needed-for-mininet" in env.reproducibility_limitations:
        bootstrap_ready = False
    return {
        "profile": env.profile,
        "status": "supported" if bootstrap_ready else ("degraded" if env.status != "unsupported" else "unsupported"),
        "bootstrap_ready": bootstrap_ready,
        "missing_dependencies": env.missing_dependencies,
        "limitations": env.reproducibility_limitations,
        "provider_support": env.provider_support,
        "detail": env.detail,
    }
