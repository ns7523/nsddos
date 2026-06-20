"""Runtime query API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.schemas import ApiEvidenceRef, ApiExplainResponse, ApiQueryRequest, ApiQueryResponse
from nsddos.runtime.query.engine import explain_query_system

router = APIRouter(prefix="/runtime", tags=["runtime-query"])


@router.post("/query", response_model=ApiQueryResponse)
def runtime_query(
    request: ApiQueryRequest,
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Execute query-backed runtime request."""
    return execute_api_query(config, request)


@router.get("/query/explain", response_model=ApiExplainResponse)
def explain_runtime_query() -> ApiExplainResponse:
    """Explain query scopes and dependencies."""
    return ApiExplainResponse(
        subject="runtime-query",
        detail=explain_query_system(),
        evidence=[ApiEvidenceRef(kind="query", reference="registry", detail="query registry")],
    )
