"""Typed freshness and consistency models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION


class FreshnessStatus(StrEnum):
    AUTHORITATIVE_LIVE = "authoritative-live"
    DEGRADED_LIVE = "degraded-live"
    REPLAY_ONLY = "replay-only"


class ValidityState(StrEnum):
    VALID = "valid"
    STALE = "stale"
    EXPIRED = "expired"
    DEGRADED = "degraded"
    REPLAY_ONLY = "replay_only"
    INCONSISTENT = "inconsistent"
    DIVERGENT = "divergent"


@dataclass(frozen=True)
class FreshnessWindow:
    name: str
    max_age_seconds: int
    stale_after_seconds: int


@dataclass(frozen=True)
class RuntimeFreshness:
    created_at: str
    observed_at: str
    synchronized_at: str
    freshness_window: str
    freshness_status: str
    validity_state: str
    replay_validity: str
    consistency_generation: str
    stale: bool
    expired: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConsistencyCheck:
    scope: str
    valid: bool
    generation: str
    issues: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FreshnessEvaluation:
    freshness: RuntimeFreshness
    consistency: ConsistencyCheck
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "freshness": self.freshness.to_dict(),
            "consistency": asdict(self.consistency),
        }
