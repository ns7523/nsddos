"""Runtime replay API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.schemas import (
    ApiEvidenceRef,
    ApiExplainResponse,
    ApiPagination,
    ApiQueryRequest,
    ApiQueryResponse,
)
from nsddos.runtime.query.engine import explain_query_system

router = APIRouter(prefix="/runtime/replay", tags=["runtime-replay"])


@router.get("", response_model=ApiQueryResponse)
def runtime_replay(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query replay history."""
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="replay",
            scope="replay",
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )


@router.get("/explain", response_model=ApiExplainResponse)
def explain_runtime_replay() -> ApiExplainResponse:
    """Explain replay-safe query surface."""
    return ApiExplainResponse(
        subject="runtime-replay",
        detail={"query_system": explain_query_system(), "replay_safe": True},
        evidence=[ApiEvidenceRef(kind="replay", reference="query-engine", detail="replay-safe ordering")],
    )
