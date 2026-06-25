"""Typed runtime query models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from nsddos.runtime.models import SCHEMA_VERSION

QueryExecutor = Callable[[dict[str, Any], "RuntimeQuery"], dict[str, Any]]


@dataclass(frozen=True)
class RuntimeQueryScope:
    """Formal query scope."""

    name: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeQueryDependency:
    """Query dependency edge."""

    source: str
    target: str
    reason: str = "query_dependency"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeQueryFilter:
    """Typed query filter."""

    field: str
    value: Any
    operator: str = "eq"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeQueryPagination:
    """Stable pagination request."""

    limit: int = 25
    offset: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeQueryEvidence:
    """Evidence pointer returned by query."""

    kind: str
    reference: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeQuery:
    """Executable runtime query."""

    name: str
    scope: str
    filters: tuple[RuntimeQueryFilter, ...] = field(default_factory=tuple)
    pagination: RuntimeQueryPagination = field(default_factory=RuntimeQueryPagination)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    replay_safe: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "scope": self.scope,
            "filters": [item.to_dict() for item in self.filters],
            "pagination": self.pagination.to_dict(),
            "dependencies": list(self.dependencies),
            "replay_safe": self.replay_safe,
        }


@dataclass
class RuntimeQueryResult:
    """Typed query result."""

    query: RuntimeQuery
    items: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[RuntimeQueryEvidence] = field(default_factory=list)
    total: int = 0
    duration_ms: float = 0.0
    cache: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, float] = field(default_factory=dict)
    freshness: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "query": self.query.to_dict(),
            "items": self.items,
            "total": self.total,
            "evidence": [item.to_dict() for item in self.evidence],
            "duration_ms": self.duration_ms,
            "cache": self.cache,
            "plan": self.plan,
            "performance": self.performance,
            "freshness": self.freshness,
        }
