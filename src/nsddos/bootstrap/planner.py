"""Dependency planning orchestration for setup wizard."""

from __future__ import annotations

from nsddos.bootstrap.requirements import build_install_requirements
from nsddos.bootstrap.state import DependencyPlan, DeploymentProfile, EnvironmentScan
from nsddos.bootstrap.validator import build_profile_advisories


def build_dependency_plan(scan: EnvironmentScan, profile: DeploymentProfile) -> DependencyPlan:
    """Build non-installing dependency plan."""

    advisories = build_profile_advisories(scan, profile)
    requirements = build_install_requirements(scan, profile, advisory=advisories)
    return DependencyPlan(
        profile=profile,
        requirements=requirements,
        summary=f"{len(requirements)} setup actions planned for {profile.label}.",
    )
