"""Verification API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.schemas import (
    ApiEvidenceRef,
    ApiExplainResponse,
    ApiFilter,
    ApiPagination,
    ApiQueryRequest,
    ApiQueryResponse,
)
from nsddos.runtime.verification.engine import explain_verification

router = APIRouter(prefix="/runtime/verification", tags=["runtime-verification"])


@router.get("", response_model=ApiQueryResponse)
def runtime_verification(
    category: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query verification state."""
    filters = [ApiFilter(field="category", value=category)] if category else []
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="verification",
            scope="verification",
            filters=filters,
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )


@router.get("/explain", response_model=ApiExplainResponse)
def explain_runtime_verification(
    config: dict[str, Any] = Depends(get_config),
) -> ApiExplainResponse:
    """Explain verification dependencies."""
    return ApiExplainResponse(
        subject="runtime-verification",
        detail=explain_verification(config),
        evidence=[ApiEvidenceRef(kind="verification", reference="engine", detail="validator registry")],
    )
