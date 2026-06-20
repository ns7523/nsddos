"""Open vSwitch command helpers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from shutil import which

from nsddos.constants import OVS_OFCTL_BIN, OVS_VSCTL_BIN


def has_passwordless_sudo() -> bool:
    """Check sudo availability."""
    if which("sudo") is None:
        return False
    try:
        result = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def is_root() -> bool:
    """Check effective uid."""
    geteuid = getattr(os, "geteuid", None)
    return bool(geteuid and geteuid() == 0)


def require_prefix(require_root: bool = False) -> list[str]:
    """Return sudo prefix when needed."""
    if not require_root:
        return []
    if is_root():
        return []
    if has_passwordless_sudo():
        return ["sudo", "-n"]
    raise RuntimeError("OVS command requires root or passwordless sudo.")


def resolve_ovs_vsctl(bin_path: Path = OVS_VSCTL_BIN) -> str | None:
    """Resolve ovs-vsctl path."""
    as_text = str(bin_path)
    if "/" in as_text:
        return as_text if bin_path.exists() else None
    return which(as_text)


def resolve_ovs_ofctl(bin_path: Path = OVS_OFCTL_BIN) -> str | None:
    """Resolve ovs-ofctl path."""
    as_text = str(bin_path)
    if "/" in as_text:
        return as_text if bin_path.exists() else None
    return which(as_text)


def run_ovs_vsctl(
    args: list[str],
    require_root: bool = False,
    timeout: int = 5,
) -> subprocess.CompletedProcess[str]:
    """Run ovs-vsctl command."""
    binary = resolve_ovs_vsctl()
    if not binary:
        raise RuntimeError("ovs-vsctl not found.")
    command = [*require_prefix(require_root), binary, *args]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_ovs_ofctl(
    args: list[str],
    require_root: bool = False,
    timeout: int = 5,
) -> subprocess.CompletedProcess[str]:
    """Run ovs-ofctl command."""
    binary = resolve_ovs_ofctl()
    if not binary:
        raise RuntimeError("ovs-ofctl not found.")
    command = [*require_prefix(require_root), binary, *args]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
