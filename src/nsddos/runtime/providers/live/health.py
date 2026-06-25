"""Live provider health evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.runtime.providers.live.contracts import ProviderHealthRecord


def _age_seconds(value: str) -> float:
    if not value:
        return 0.0
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return max(0.0, (datetime.now(timezone.utc) - observed).total_seconds())


def evaluate_provider_health(
    provider: str,
    *,
    reachable: bool,
    latency_ms: float,
    malformed: bool,
    last_timestamp: str = "",
    error_count: int = 0,
) -> ProviderHealthRecord:
    age_seconds = _age_seconds(last_timestamp)
    if not reachable and error_count > 0:
        state = "reconnecting"
        detail = "provider unreachable, retrying"
    elif not reachable:
        state = "disconnected"
        detail = "provider unreachable"
    elif malformed:
        state = "degraded"
        detail = "malformed provider payload"
    elif age_seconds > 180:
        state = "degraded"
        detail = f"stale provider timestamp age={age_seconds:.1f}s"
    else:
        state = "healthy"
        detail = "provider healthy"
    return ProviderHealthRecord(
        provider=provider,
        state=state,
        reachable=reachable,
        latency_ms=latency_ms,
        detail=detail,
        last_timestamp=last_timestamp,
        error_count=error_count,
    )


def collect_provider_health(
    records: tuple[ProviderHealthRecord, ...]
) -> dict[str, dict[str, object]]:
    return {item.provider: item.to_dict() for item in records}
