"""Typed session contracts."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeSession(DomainModel):
    session_id: str = ""
    owner: str = ""
    state: str = ""
    lifecycle: str = ""
