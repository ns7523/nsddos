"""Runtime reproducibility analysis."""

from __future__ import annotations

from typing import Any

from nsddos.constants import COMPOSE_FILE
from nsddos.runtime.environment import validate_runtime_environment
from nsddos.runtime.models import ReproducibilityAssessment
from nsddos.runtime.profiles import detect_runtime_profile


def analyze_reproducibility(config: dict[str, Any]) -> ReproducibilityAssessment:
    """Deterministically assess reproducibility quality."""
    profile = detect_runtime_profile()
    environment = validate_runtime_environment(config)

    deterministic_inputs = ["yaml-config", "src-layout", "typed-runtime-state"]
    if COMPOSE_FILE.exists():
        deterministic_inputs.append("compose-file")
    if profile.name in {"linux-native", "docker-linux"}:
        deterministic_inputs.append("canonical-linux-profile")

    provider_repro = {
        name: ("reproducible" if status == "supported" else "partial" if status == "partial" else "non_reproducible")
        for name, status in environment.provider_support.items()
    }
    snapshot_portable = profile.name != "linux-native" or environment.status in {"compatible", "degraded", "partially_supported"}
    profile_stable = profile.name in {"linux-native", "docker-linux"}

    if environment.status == "compatible" and profile_stable:
        status = "reproducible"
    elif environment.status in {"degraded", "partially_supported"}:
        status = "partially_reproducible"
    else:
        status = "non_reproducible"

    return ReproducibilityAssessment(
        status=status,
        deterministic_inputs=deterministic_inputs,
        portability_limits=environment.reproducibility_limitations + environment.missing_dependencies,
        provider_reproducibility=provider_repro,
        snapshot_portable=snapshot_portable,
        profile_stable=profile_stable,
        detail=f"profile={profile.name} environment={environment.status}",
    )

