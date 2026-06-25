"""Runtime graph API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.schemas import (
    ApiFilter,
    ApiPagination,
    ApiQueryRequest,
    ApiQueryResponse,
)

router = APIRouter(prefix="/runtime/graph", tags=["runtime-graph"])


@router.get("", response_model=ApiQueryResponse)
def runtime_graph(
    node_type: str | None = Query(default=None),
    edge_type: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query graph nodes and relationships."""
    filters: list[ApiFilter] = []
    if node_type:
        filters.append(ApiFilter(field="type", value=node_type))
    if edge_type:
        filters.append(ApiFilter(field="edge_type", value=edge_type))
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="graph",
            scope="graph",
            filters=filters,
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )


@router.get("/traverse", response_model=ApiQueryResponse)
def runtime_graph_traverse(
    source: str | None = Query(default=None),
    target: str | None = Query(default=None),
    relationship: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Traverse graph relationships through query-backed filters."""
    filters: list[ApiFilter] = []
    if source:
        filters.append(ApiFilter(field="source", value=source))
    if target:
        filters.append(ApiFilter(field="target", value=target))
    if relationship:
        filters.append(ApiFilter(field="edge_type", value=relationship))
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="graph",
            scope="graph",
            filters=filters,
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )
