"""Typed verification contracts."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeVerification(DomainModel):
    verifier: str = ""
    category: str = ""
    status: str = ""
    severity: str = ""
    evidence_reference: str = ""
