"""Collection registry helpers."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.providers_registry import build_provider_registry


def runtime_registry(config: dict[str, Any]) -> dict[str, Any]:
    """Return runtime provider registry."""
    return build_provider_registry(config)
