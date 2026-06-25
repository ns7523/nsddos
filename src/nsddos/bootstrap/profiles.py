"""Deployment profile definitions for setup wizard."""

from __future__ import annotations

from nsddos.bootstrap.state import DeploymentProfile

LOCAL_DEVELOPMENT = DeploymentProfile(
    key="local-development",
    label="Local Development",
    description="General workstation setup for iterative development.",
)
EC2_SERVER = DeploymentProfile(
    key="ec2-server",
    label="EC2 Server",
    description="Remote Linux host for deployed runtime preparation.",
)
DOCKER_RUNTIME_ONLY = DeploymentProfile(
    key="docker-runtime-only",
    label="Docker Runtime Only",
    description="Container-only runtime without full SDN lab tooling.",
)
FULL_SDN_LAB_MODE = DeploymentProfile(
    key="full-sdn-lab-mode",
    label="Full SDN Lab Mode",
    description="Complete SDN lab stack with strongest environment requirements.",
)

DEPLOYMENT_PROFILES: tuple[DeploymentProfile, ...] = (
    LOCAL_DEVELOPMENT,
    EC2_SERVER,
    DOCKER_RUNTIME_ONLY,
    FULL_SDN_LAB_MODE,
)


def profile_choices() -> tuple[tuple[int, DeploymentProfile], ...]:
    """Return numeric profile choices."""

    return tuple(
        (index, profile) for index, profile in enumerate(DEPLOYMENT_PROFILES, start=1)
    )


def get_profile_by_choice(choice: int) -> DeploymentProfile:
    """Resolve numeric choice to deployment profile."""

    if not 1 <= choice <= len(DEPLOYMENT_PROFILES):
        raise ValueError(f"Unsupported deployment profile choice: {choice}")
    return DEPLOYMENT_PROFILES[choice - 1]
