"""Health API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.schemas import ApiEvidenceRef, ApiHealthResponse
from nsddos.api.schemas import ApiQueryRequest

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiHealthResponse)
def health(config: dict[str, Any] = Depends(get_config)) -> ApiHealthResponse:
    """Return API/runtime health summary."""
    result = execute_api_query(config, ApiQueryRequest(name="health", scope="runtime"))
    item = result.items[0] if result.items else {"status": "degraded", "checks": {}}
    return ApiHealthResponse(
        status=str(item.get("status", "degraded")),
        checks=dict(item.get("checks", {})),
        evidence=[
            *result.evidence,
            ApiEvidenceRef(
                kind="health",
                reference="runtime-health",
                detail="query-backed health checks",
            ),
        ],
    )
