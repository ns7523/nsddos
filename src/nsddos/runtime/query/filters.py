"""Deterministic query filtering."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.query.models import RuntimeQueryFilter


def _value(item: dict[str, Any], field: str) -> Any:
    current: Any = item
    for part in field.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def apply_filters(items: list[dict[str, Any]], filters: tuple[RuntimeQueryFilter, ...]) -> list[dict[str, Any]]:
    """Apply deterministic filters."""
    result = list(items)
    for query_filter in filters:
        if query_filter.operator == "eq":
            result = [item for item in result if _value(item, query_filter.field) == query_filter.value]
        elif query_filter.operator == "contains":
            result = [item for item in result if str(query_filter.value) in str(_value(item, query_filter.field))]
        elif query_filter.operator == "exists":
            result = [item for item in result if _value(item, query_filter.field) is not None]
        else:
            raise ValueError(f"unsupported filter operator: {query_filter.operator}")
    return result
