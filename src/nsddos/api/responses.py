"""API response conversion."""

from __future__ import annotations

from hashlib import sha256

from nsddos.api.schemas import ApiEvidenceRef, ApiQueryResponse
from nsddos.runtime.domain.serialization import to_canonical_dict
from nsddos.runtime.query.models import RuntimeQueryResult


def query_response(result: RuntimeQueryResult) -> ApiQueryResponse:
    """Convert runtime query result to typed API response."""
    canonical_result = to_canonical_dict(result)
    request_id = sha256(str(result.query.to_dict()).encode("utf-8")).hexdigest()[:16]
    return ApiQueryResponse(
        request_id=request_id,
        query=canonical_result["query"],
        items=canonical_result["items"],
        total=canonical_result["total"],
        evidence=[ApiEvidenceRef(**item.to_dict()) for item in result.evidence],
        plan=canonical_result["plan"],
        cache=canonical_result["cache"],
        performance=canonical_result["performance"],
        freshness=canonical_result.get("freshness", {}),
        duration_ms=canonical_result["duration_ms"],
        replay_safe=result.query.replay_safe,
        timestamp=result.timestamp,
    )
