"""Typed graph entities."""

from __future__ import annotations

from dataclasses import dataclass, field

from nsddos.runtime.domain.base import DomainModel
from nsddos.runtime.domain.relationships import RuntimeRelationship


@dataclass(frozen=True)
class RuntimeEntity(DomainModel):
    entity_id: str = ""
    entity_type: str = ""
    label: str = ""
    detail: str = ""


@dataclass(frozen=True)
class RuntimeGraph(DomainModel):
    nodes: tuple[RuntimeEntity, ...] = field(default_factory=tuple)
    relationships: tuple[RuntimeRelationship, ...] = field(default_factory=tuple)
