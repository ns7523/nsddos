"""Typed synchronization contracts."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeSynchronization(DomainModel):
    synchronization_id: str = ""
    state: str = ""
    runtime_checksum: str = ""
    query_checksum: str = ""
    evidence_checksum: str = ""
