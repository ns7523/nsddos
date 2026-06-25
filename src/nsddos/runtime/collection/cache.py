"""Collection cache facade."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.cache import get_cache, set_cache


def collection_cache_get(
    name: str, inputs: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Get collection cache."""
    return get_cache(name, inputs)


def collection_cache_set(
    name: str, inputs: dict[str, Any], value: dict[str, Any]
) -> dict[str, Any]:
    """Set collection cache."""
    return set_cache(name, inputs, value)
