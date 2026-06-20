"""Runtime state querying for API-facing read models."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.analysis_layer import aggregate_runtime
from nsddos.runtime.collection_layer import collect_runtime_bundle
from nsddos.runtime.query.models import RuntimeQuery


def _analysis(config: dict[str, Any]) -> dict[str, Any]:
    aggregation = aggregate_runtime(config, collect_runtime_bundle(config))
    return aggregation.analysis.to_dict()


def query_convergence(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query convergence state through normalized runtime analysis."""
    convergence = _analysis(config).get("convergence", {})
    return {"items": [{"id": "convergence", **convergence}]}


def query_health(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query runtime health through query registry."""
    from nsddos.health import get_health_report

    checks = get_health_report(verbose=False)["flat"]
    status = "ok" if all(checks.values()) else "degraded"
    return {"items": [{"id": "health", "status": status, "checks": checks}]}


def query_drift(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query drift state through normalized runtime analysis."""
    drift = _analysis(config).get("drift", [])
    items = []
    for index, item in enumerate(drift):
        if isinstance(item, dict):
            items.append({"id": item.get("id", f"drift:{index}"), **item})
        else:
            items.append({"id": f"drift:{index}", "detail": str(item)})
    return {"items": items}


def query_stability(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query stability state through normalized runtime analysis."""
    temporal = _analysis(config).get("temporal", {})
    stability = temporal.get("stability", {})
    return {"items": [{"id": "stability", **stability}]}
