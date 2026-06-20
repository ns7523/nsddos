"""Typed verification rules and constraints."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from nsddos.runtime.models import VerificationResult

ValidatorFn = Callable[[dict[str, Any]], list[VerificationResult]]


@dataclass(frozen=True)
class RuntimeValidationConstraint:
    """Named deterministic validation constraint."""

    name: str
    detail: str
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeVerificationDependency:
    """Validator dependency edge."""

    source: str
    target: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeVerificationScope:
    """Verification scope metadata."""

    name: str
    categories: tuple[str, ...]
    degraded_safe: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeVerificationRule:
    """Executable verification rule."""

    name: str
    category: str
    validator: ValidatorFn
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    constraints: tuple[RuntimeValidationConstraint, ...] = field(default_factory=tuple)
    degraded_safe: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("validator", None)
        payload["constraints"] = [item.to_dict() for item in self.constraints]
        return payload
