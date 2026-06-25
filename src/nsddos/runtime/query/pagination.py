"""Stable query pagination."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.query.models import RuntimeQueryPagination


def paginate(
    items: list[dict[str, Any]], pagination: RuntimeQueryPagination
) -> list[dict[str, Any]]:
    """Return deterministic page."""
    ordered = sorted(
        items,
        key=lambda item: str(
            item.get("timestamp", item.get("id", item.get("path", "")))
        ),
    )
    start = max(0, pagination.offset)
    limit = max(0, pagination.limit)
    return ordered[start : start + limit]
