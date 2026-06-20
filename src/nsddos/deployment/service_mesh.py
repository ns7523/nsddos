"""Deployment service dependency graph."""

from __future__ import annotations

from nsddos.deployment.contracts import ServiceMeshContract


def build_service_mesh_contract() -> ServiceMeshContract:
    """Build deterministic service dependency graph."""
    return ServiceMeshContract(
        services=("nsddos-ui", "nsddos-api", "nsddos-runtime", "floodlight", "sflowrt"),
        dependencies=(
            ("nsddos-ui", "nsddos-api"),
            ("nsddos-api", "nsddos-runtime"),
            ("nsddos-runtime", "floodlight"),
            ("nsddos-runtime", "sflowrt"),
        ),
        controllers=("floodlight",),
        providers=("sflowrt",),
    )
