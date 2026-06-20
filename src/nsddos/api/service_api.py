"""Service runtime API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.schemas import ApiPagination, ApiQueryRequest, ApiQueryResponse

router = APIRouter(prefix="/runtime/service", tags=["service"])


@router.get("", response_model=ApiQueryResponse)
def runtime_service_state(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="service",
            scope="service",
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )
