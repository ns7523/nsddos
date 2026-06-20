"""Runtime evidence API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.schemas import ApiFilter, ApiPagination, ApiQueryRequest, ApiQueryResponse

router = APIRouter(prefix="/runtime/evidence", tags=["runtime-evidence"])


@router.get("", response_model=ApiQueryResponse)
def runtime_evidence(
    verification: str | None = Query(default=None),
    replay: str | None = Query(default=None),
    convergence: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query evidence bundles."""
    filters: list[ApiFilter] = []
    if verification:
        filters.append(ApiFilter(field="verification_count", value=0, operator="exists"))
    if replay:
        filters.append(ApiFilter(field="id", value=replay, operator="contains"))
    if convergence:
        filters.append(ApiFilter(field="convergence", value=convergence))
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="evidence",
            scope="evidence",
            filters=filters,
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )
