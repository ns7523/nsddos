"""Runtime snapshot API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from nsddos.api.dependencies import execute_api_query, get_config
from nsddos.api.schemas import ApiFilter, ApiPagination, ApiQueryRequest, ApiQueryResponse

router = APIRouter(prefix="/runtime/snapshots", tags=["runtime-snapshots"])


@router.get("", response_model=ApiQueryResponse)
def runtime_snapshots(
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Query schema-aware snapshot metadata."""
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="snapshots",
            scope="persistence",
            pagination=ApiPagination(limit=limit, offset=offset),
        ),
    )


@router.get("/compare", response_model=ApiQueryResponse)
def runtime_snapshot_compare(
    left: str = Query(...),
    right: str = Query(...),
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Compare snapshots through query-backed snapshot selector."""
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="snapshots",
            scope="persistence",
            filters=[
                ApiFilter(field="record_type", value="comparison"),
                ApiFilter(field="left", value=left),
                ApiFilter(field="right", value=right),
            ],
        ),
    )


@router.get("/{snapshot_id}", response_model=ApiQueryResponse)
def runtime_snapshot_lookup(
    snapshot_id: str,
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Lookup snapshot metadata by stable id."""
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="snapshots",
            scope="persistence",
            filters=[ApiFilter(field="id", value=snapshot_id)],
        ),
    )


@router.get("/{snapshot_id}/lineage", response_model=ApiQueryResponse)
def runtime_snapshot_lineage(
    snapshot_id: str,
    config: dict[str, Any] = Depends(get_config),
) -> ApiQueryResponse:
    """Lookup snapshot lineage through query-backed selector."""
    return execute_api_query(
        config,
        ApiQueryRequest(
            name="snapshots",
            scope="persistence",
            filters=[
                ApiFilter(field="record_type", value="lineage"),
                ApiFilter(field="target", value=snapshot_id),
            ],
        ),
    )
