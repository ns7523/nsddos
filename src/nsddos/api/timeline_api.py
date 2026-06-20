"""Runtime timeline API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.schemas import ApiFilter, ApiPagination, ApiQueryRequest, ApiQueryResponse

router = APIRouter(prefix="/runtime/timeline", tags=["runtime-timeline"])


@router.get("", response_model=ApiQueryResponse)
def runtime_timeline(
    status: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query temporal runtime history."""
    filters = []
    if status:
        filters.append(ApiFilter(field="status", value=status))
    if kind:
        filters.append(ApiFilter(field="kind", value=kind))
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="timeline",
            scope="temporal",
            filters=filters,
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )


@router.get("/transitions", response_model=ApiQueryResponse)
def runtime_timeline_transitions(
    status: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query replay-safe transition history."""
    filters = [ApiFilter(field="record_type", value="transition")]
    if status:
        filters.append(ApiFilter(field="status", value=status))
    if kind:
        filters.append(ApiFilter(field="kind", value=kind))
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="timeline",
            scope="temporal",
            filters=filters,
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )
