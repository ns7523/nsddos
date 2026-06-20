"""UI typed models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nsddos.runtime.models import SCHEMA_VERSION


@dataclass(frozen=True)
class UiPagePayload:
    name: str
    title: str
    items: list[dict[str, Any]]
    summary: dict[str, Any] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UiState:
    schema_version: str = SCHEMA_VERSION
    api_state: dict[str, Any] = field(default_factory=dict)
    synchronization_state: dict[str, Any] = field(default_factory=dict)
    replay_state: dict[str, Any] = field(default_factory=dict)
    graph_state: dict[str, Any] = field(default_factory=dict)
    pagination_state: dict[str, int] = field(default_factory=dict)
    refresh_metadata: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
