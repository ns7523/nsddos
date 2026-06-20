"""Typed persistence contracts."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeCapability(DomainModel):
    name: str = ""
    status: str = ""


@dataclass(frozen=True)
class RuntimeEnvironment(DomainModel):
    profile: str = ""
    status: str = ""
    detail: str = ""
