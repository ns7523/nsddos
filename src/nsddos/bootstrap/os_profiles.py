"""Operating-system profile detection for installer engine."""

from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OSProfile:
    """Detected host OS profile."""

    family: str
    distribution: str
    package_manager: str
    supported: bool
    homebrew_installed: bool


def _detect_linux_distribution() -> str:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return "linux"
    for line in os_release.read_text(encoding="utf-8").splitlines():
        if line.startswith("ID="):
            return line.split("=", 1)[1].strip().strip('"').lower()
    return "linux"


def detect_os_profile() -> OSProfile:
    """Detect supported OS profile."""

    system = (platform.system() or "Unknown").lower()
    if system == "linux":
        distribution = _detect_linux_distribution()
        supported = distribution in {"ubuntu", "debian"}
        return OSProfile(
            family="Linux",
            distribution=distribution,
            package_manager="apt" if supported else "unsupported",
            supported=supported,
            homebrew_installed=False,
        )
    if system == "darwin":
        brew = shutil.which("brew")
        return OSProfile(
            family="macOS",
            distribution="macos",
            package_manager="brew" if brew else "unsupported",
            supported=brew is not None,
            homebrew_installed=brew is not None,
        )
    return OSProfile(
        family=platform.system() or "Unknown",
        distribution=system,
        package_manager="unsupported",
        supported=False,
        homebrew_installed=False,
    )
