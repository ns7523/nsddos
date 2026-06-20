"""Release registry lookups."""

from __future__ import annotations

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import read_json_checked

RELEASE_DIR = RUNTIME_DIR / "release"


def _read(name: str) -> dict:
    path = RELEASE_DIR / name
    if not path.exists():
        return {}
    return read_json_checked(path)


def latest_release_candidate() -> dict:
    """Load latest release candidate."""
    return _read("latest.json")


def latest_artifacts_payload() -> dict:
    """Load latest release artifacts."""
    return _read("artifacts.json")


def latest_benchmark_payload() -> dict:
    """Load latest benchmark payload."""
    return _read("benchmark.json")


def latest_package_payload() -> dict:
    """Load latest package payload."""
    return _read("package.json")


def latest_diagnostics_payload() -> dict:
    """Load latest diagnostics payload."""
    return _read("diagnostics.json")


def latest_security_audit_payload() -> dict:
    """Load latest security audit payload."""
    return _read("security_audit.json")
