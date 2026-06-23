"""Validation helpers for setup wizard planning."""

from __future__ import annotations

from nsddos.bootstrap.state import DeploymentProfile, EnvironmentScan, InstallRequirement


def build_profile_advisories(
    scan: EnvironmentScan,
    profile: DeploymentProfile,
) -> tuple[InstallRequirement, ...]:
    """Build advisory plan items for selected profile."""

    advisories: list[InstallRequirement] = []
    if profile.key == "full-sdn-lab-mode" and scan.os_family != "Linux":
        advisories.append(
            InstallRequirement(
                "L1",
                "Prepare Linux Host",
                "Full SDN Lab Mode works best on Linux host or Linux VM.",
            )
        )
    if profile.key == "ec2-server" and scan.os_family != "Linux":
        advisories.append(
            InstallRequirement(
                "L2",
                "Target Remote Linux Server",
                "Current machine is not Linux; plan assumes remote EC2 preparation.",
            )
        )
    if scan.available_memory_bytes and scan.available_memory_bytes < 8 * 1024**3:
        advisories.append(
            InstallRequirement(
                "R1",
                "Review Memory Capacity",
                "Available memory below 8 GB baseline for smoother container runtime work.",
                required=False,
            )
        )
    if scan.available_disk_bytes and scan.available_disk_bytes < 20 * 1024**3:
        advisories.append(
            InstallRequirement(
                "R2",
                "Review Disk Capacity",
                "Available disk below 20 GB baseline for images, logs, and runtime state.",
                required=False,
            )
        )
    return tuple(advisories)
