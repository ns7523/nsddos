"""Typed convergence contracts."""

from __future__ import annotations

from dataclasses import dataclass

from nsddos.runtime.domain.base import DomainModel


@dataclass(frozen=True)
class RuntimeConvergence(DomainModel):
    status: str = ""
    topology_agreement: str = ""
    datapath_agreement: str = ""
    controller_agreement: str = ""
    telemetry_agreement: str = ""
    divergence_reasons: str = ""
