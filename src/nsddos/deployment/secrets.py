"""Deployment secret inventory."""

from __future__ import annotations

import os

from nsddos.constants import PROJECT_ROOT
from nsddos.deployment.contracts import SecretContract


def _example_env_values() -> dict[str, str]:
    """Load deterministic local placeholder env values from .env.example."""
    path = PROJECT_ROOT / ".env.example"
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def build_secret_contract() -> SecretContract:
    """Build deterministic secret requirements."""
    required = ("NSDDOS_API_TOKEN", "NSDDOS_SECRET_KEY")
    optional = ("NSDDOS_CONTROLLER_PASSWORD", "NSDDOS_SFLOW_AUTH")
    example_values = _example_env_values()
    missing = tuple(key for key in required if not (os.getenv(key) or example_values.get(key)))
    return SecretContract(required_keys=required, optional_keys=optional, missing_keys=missing)
