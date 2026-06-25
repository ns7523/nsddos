"""Deployment container contracts."""

from __future__ import annotations

from pathlib import Path

from nsddos.constants import PROJECT_ROOT
from nsddos.deployment.contracts import ContainerContract


def manifest_path(*parts: str) -> Path:
    """Return deployment manifest path under the project root."""
    return PROJECT_ROOT / "deployment" / Path(*parts)


def build_container_contracts(
    environment: str = "prod",
) -> tuple[ContainerContract, ...]:
    """Build deterministic container contracts from repo manifests."""
    compose_manifest = manifest_path("docker", "docker-compose.prod.yml")
    dockerfile = manifest_path("docker", "Dockerfile.prod")
    return (
        ContainerContract(
            name="nsddos-api",
            image=f"nsddos/api:{environment}",
            command="python -m nsddos api start --host 0.0.0.0 --port 8008",
            ports=("8008:8008",),
            environment_keys=("NSDDOS_HOME", "NSDDOS_CONFIG", "NSDDOS_API_TOKEN"),
            mounts=(f"{dockerfile}",),
            replicas=1,
            source_manifest=str(compose_manifest),
        ),
        ContainerContract(
            name="nsddos-ui",
            image=f"nsddos/ui:{environment}",
            command="python -m nsddos ui start",
            ports=("3000:3000",),
            environment_keys=("NSDDOS_HOME", "NSDDOS_CONFIG"),
            mounts=(f"{dockerfile}",),
            replicas=1,
            source_manifest=str(compose_manifest),
        ),
        ContainerContract(
            name="nsddos-runtime",
            image=f"nsddos/runtime:{environment}",
            command="python -m nsddos verify",
            ports=(),
            environment_keys=("NSDDOS_HOME", "NSDDOS_CONFIG", "NSDDOS_RUNTIME_MODE"),
            mounts=(f"{dockerfile}",),
            replicas=1,
            source_manifest=str(compose_manifest),
        ),
    )
