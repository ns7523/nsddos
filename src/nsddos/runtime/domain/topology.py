"""Typed topology contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeTopology(DomainModel):
    switches: tuple[str, ...] = field(default_factory=tuple)
    hosts: tuple[str, ...] = field(default_factory=tuple)
    links: tuple[str, ...] = field(default_factory=tuple)
