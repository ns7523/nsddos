"""Typed timeline entities."""

from __future__ import annotations

from dataclasses import dataclass, field

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeTransition(DomainModel):
    transition_id: str = ""
    event_type: str = ""
    timestamp: str = ""
    affected_entities: tuple[str, ...] = field(default_factory=tuple)
    detail: str = ""


@dataclass(frozen=True)
class RuntimeTimeline(DomainModel):
    transitions: tuple[RuntimeTransition, ...] = field(default_factory=tuple)
