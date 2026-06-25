"""Deployment secret inventory."""

from __future__ import annotations

import os

from nsddos.deployment.contracts import SecretContract


def build_secret_contract() -> SecretContract:
    """Build deterministic secret requirements."""
    required = ("NSDDOS_API_TOKEN", "NSDDOS_SECRET_KEY")
    optional = ("NSDDOS_CONTROLLER_PASSWORD", "NSDDOS_SFLOW_AUTH")
    missing = tuple(key for key in required if not os.getenv(key))
    return SecretContract(
        required_keys=required, optional_keys=optional, missing_keys=missing
    )
