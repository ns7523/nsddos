"""Typed relationship contracts."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeRelationship(DomainModel):
    relationship_type: str = ""
    source_id: str = ""
    target_id: str = ""
    detail: str = ""
