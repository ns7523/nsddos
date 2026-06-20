"""Domain lifecycle contracts."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeSnapshot(DomainModel):
    snapshot_id: str = ""
    state: str = ""


@dataclass(frozen=True)
class RuntimeDrift(DomainModel):
    drift_id: str = ""
    detail: str = ""
