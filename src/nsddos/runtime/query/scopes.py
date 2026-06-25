"""Runtime query scopes."""

from __future__ import annotations

from nsddos.runtime.query.models import RuntimeQueryScope

SCOPE_NAMES = (
    "runtime",
    "orchestration",
    "collection",
    "normalization",
    "reconciliation",
    "convergence",
    "topology",
    "datapath",
    "telemetry",
    "temporal",
    "verification",
    "persistence",
    "reproducibility",
    "evidence",
    "replay",
    "graph",
    "service",
    "detection",
    "mitigation",
    "live",
    "provider",
    "simulation",
    "streaming",
    "policy",
    "ml",
)


def default_scopes() -> dict[str, RuntimeQueryScope]:
    """Return supported query scopes."""
    return {
        name: RuntimeQueryScope(name=name, detail=f"{name} query scope")
        for name in SCOPE_NAMES
    }
