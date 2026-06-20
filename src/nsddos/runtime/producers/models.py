"""Typed producer models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nsddos.runtime.domain.base import RuntimeRecord


@dataclass(frozen=True)
class ProducerEntity:
    producer: str
    record: RuntimeRecord


@dataclass(frozen=True)
class ProducerOutput:
    producer: str
    entities: tuple[ProducerEntity, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProducerContractStatus:
    producer: str
    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
