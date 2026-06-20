"""Typed datapath contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeDatapath(DomainModel):
    ports: tuple[str, ...] = field(default_factory=tuple)
    interfaces: tuple[str, ...] = field(default_factory=tuple)
    paths: tuple[str, ...] = field(default_factory=tuple)
