"""Authoritative freshness evaluation engine."""

from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any

from nsddos.runtime.performance import record_timing
from nsddos.runtime.freshness.consistency import validate_consistency
from nsddos.runtime.freshness.models import FreshnessEvaluation, FreshnessStatus, RuntimeFreshness, ValidityState
from nsddos.runtime.freshness.timelines import normalize_time, now_utc_iso
from nsddos.runtime.freshness.windows import get_window


def _parse_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except ValueError:
            return datetime(2100, 1, 1, tzinfo=timezone.utc)


def _age_seconds(observed_at: str, reference_at: str) -> float:
    return max(0.0, (_parse_iso(reference_at) - _parse_iso(observed_at)).total_seconds())


def _validity(age_seconds: float, stale_after: int, max_age: int, replay_only: bool) -> ValidityState:
    if replay_only:
        return ValidityState.REPLAY_ONLY
    if age_seconds > max_age:
        return ValidityState.EXPIRED
    if age_seconds > stale_after:
        return ValidityState.STALE
    return ValidityState.VALID


def evaluate_freshness(scope: str, payload: dict[str, Any], reference_at: str | None = None) -> FreshnessEvaluation:
    start = monotonic()
    window = get_window(scope)
    created_at = normalize_time(str(payload.get("created_at", "")))
    observed_at = normalize_time(str(payload.get("observed_at", payload.get("timestamp", ""))))
    synchronized_at = normalize_time(str(payload.get("synchronized_at", observed_at)))
    now = reference_at or now_utc_iso()
    replay_only = bool(payload.get("replay_only", False))
    age_seconds = _age_seconds(observed_at, now)
    validity = _validity(age_seconds, window.stale_after_seconds, window.max_age_seconds, replay_only)
    consistency = validate_consistency(scope, payload)
    final_validity = validity
    if not consistency.valid and final_validity == ValidityState.VALID:
        final_validity = ValidityState.INCONSISTENT
    freshness_status = (
        FreshnessStatus.REPLAY_ONLY
        if final_validity == ValidityState.REPLAY_ONLY
        else FreshnessStatus.DEGRADED_LIVE
        if final_validity in {ValidityState.STALE, ValidityState.EXPIRED, ValidityState.INCONSISTENT, ValidityState.DIVERGENT, ValidityState.DEGRADED}
        else FreshnessStatus.AUTHORITATIVE_LIVE
    )
    evaluation = FreshnessEvaluation(
        freshness=RuntimeFreshness(
            created_at=created_at,
            observed_at=observed_at,
            synchronized_at=synchronized_at,
            freshness_window=window.name,
            freshness_status=freshness_status.value,
            validity_state=final_validity.value,
            replay_validity="replay-safe" if replay_only or bool(payload.get("replay_safe", True)) else "non-replay-safe",
            consistency_generation=consistency.generation,
            stale=final_validity in {ValidityState.STALE, ValidityState.DEGRADED},
            expired=final_validity == ValidityState.EXPIRED,
        ),
        consistency=consistency,
    )
    record_timing(f"freshness.{scope}.evaluate", (monotonic() - start) * 1000)
    return evaluation
