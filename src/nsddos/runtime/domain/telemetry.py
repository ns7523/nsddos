"""Typed telemetry contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeTelemetry(DomainModel):
    flow_count: int = 0
    fresh: bool = False
    lineage: tuple[str, ...] = field(default_factory=tuple)
