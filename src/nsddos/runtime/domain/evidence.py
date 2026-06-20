"""Typed evidence entities."""

from __future__ import annotations

from dataclasses import dataclass, field

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeEvidence(DomainModel):
    evidence_id: str = ""
    reference: str = ""
    lineage: tuple[str, ...] = field(default_factory=tuple)
    detail: str = ""
