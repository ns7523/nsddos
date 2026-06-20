"""API pagination helpers."""

from __future__ import annotations

from nsddos.api.schemas import ApiPagination
from nsddos.runtime.query.models import RuntimeQueryPagination


def to_runtime_pagination(pagination: ApiPagination) -> RuntimeQueryPagination:
    """Convert API pagination to runtime pagination."""
    return RuntimeQueryPagination(limit=pagination.limit, offset=pagination.offset)
