"""API dependencies and query binding."""

from __future__ import annotations

from typing import Any

from nsddos.api.pagination import to_runtime_pagination
from nsddos.api.responses import query_response
from nsddos.api.schemas import ApiQueryRequest, ApiQueryResponse
from nsddos.config import load_config
from nsddos.runtime.query.engine import execute_query
from nsddos.runtime.query.models import RuntimeQuery, RuntimeQueryFilter


def get_config() -> dict[str, Any]:
    """Load runtime config for API request."""
    return load_config()


def to_runtime_query(request: ApiQueryRequest) -> RuntimeQuery:
    """Convert API query request to runtime query."""
    return RuntimeQuery(
        name=request.name,
        scope=request.scope,
        filters=tuple(
            RuntimeQueryFilter(item.field, item.value, item.operator)
            for item in request.filters
        ),
        pagination=to_runtime_pagination(request.pagination),
        replay_safe=request.replay_safe,
    )


def execute_api_query(config: dict[str, Any], request: ApiQueryRequest) -> ApiQueryResponse:
    """Execute query through authoritative runtime query engine."""
    return query_response(execute_query(config, to_runtime_query(request)))
