"""Authoritative runtime query engine."""

from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.cache import set_cache
from nsddos.runtime.persistence import atomic_write_json
from nsddos.runtime.performance import empty_query_metrics, record_timing
from nsddos.runtime.domain.base import RuntimeRecord
from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.freshness.validation import filter_expired
from nsddos.runtime.producers import produce_records
from nsddos.runtime.query.filters import apply_filters
from nsddos.runtime.query.models import (
    RuntimeQuery,
    RuntimeQueryEvidence,
    RuntimeQueryResult,
)
from nsddos.runtime.query.pagination import paginate
from nsddos.runtime.query.registry import RuntimeQueryDefinition, default_query_registry

QUERY_DIR = RUNTIME_DIR / "query"
ARCHIVAL_SCOPES = {"persistence", "evidence", "replay"}


def _plan(definition: RuntimeQueryDefinition, query: RuntimeQuery) -> dict[str, Any]:
    return {
        "query": query.name,
        "scope": query.scope,
        "dependencies": list(definition.dependencies),
        "replay_safe": definition.replay_safe and query.replay_safe,
    }


def _persist_query_result(result: RuntimeQueryResult) -> str:
    QUERY_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = QUERY_DIR / f"query-{stamp}-{result.query.name}.json"
    atomic_write_json(path, result.to_dict())
    return str(path)


def execute_query(config: dict[str, Any], query: RuntimeQuery) -> RuntimeQueryResult:
    """Execute registered runtime query deterministically."""
    registry = default_query_registry()
    if query.name not in registry.definitions:
        raise ValueError(f"unknown query: {query.name}")
    definition = registry.definitions[query.name]
    if query.scope != definition.scope:
        raise ValueError(f"query scope mismatch: {query.scope} != {definition.scope}")
    registry.ordered()
    start = monotonic()
    metrics = empty_query_metrics()
    selector_start = monotonic()
    raw = definition.executor(config, query)
    metrics["selector_ms"] = (monotonic() - selector_start) * 1000
    typed_collection = produce_records(query.scope, raw.get("items", []))
    typed_items = [entity.record.to_dict() for entity in typed_collection.entities]
    filter_start = monotonic()
    filtered = apply_filters(typed_items, query.filters)
    include_expired = query.scope in ARCHIVAL_SCOPES or any(
        item.field == "validity_state" and item.value == "expired"
        for item in query.filters
    )
    items = filter_expired(filtered, include_expired=include_expired)
    metrics["filter_ms"] = (monotonic() - filter_start) * 1000
    total = len(items)
    pagination_start = monotonic()
    page = paginate(items, query.pagination)
    typed_page = []
    for index, item in enumerate(page):
        item_id = str(
            item.get(
                "id", deterministic_id("query-item", f"{query.name}:{index}:{item}")
            )
        )
        item_type = str(item.get("type", query.name))
        typed_page.append(
            RuntimeRecord(
                record_id=item_id, record_type=item_type, payload=item
            ).to_dict()
        )
    metrics["pagination_ms"] = (monotonic() - pagination_start) * 1000
    duration_ms = (monotonic() - start) * 1000
    metrics["query_execution_ms"] = duration_ms
    if query.scope == "graph":
        metrics["graph_traversal_ms"] = metrics["selector_ms"]
    if query.scope == "replay":
        metrics["replay_query_ms"] = metrics["selector_ms"]
    evidence = [
        RuntimeQueryEvidence("query", query.name, f"scope={query.scope}"),
        RuntimeQueryEvidence(
            "dependencies", ",".join(definition.dependencies), "query dependencies"
        ),
    ]
    result = RuntimeQueryResult(
        query=query,
        items=typed_page,
        evidence=evidence,
        total=total,
        duration_ms=duration_ms,
        plan=_plan(definition, query),
        performance=metrics,
        freshness={
            "expired_filtered": len(filtered) - len(items),
            "include_expired": include_expired,
            "valid_items": len(
                [item for item in items if item.get("validity_state") == "valid"]
            ),
            "stale_items": len(
                [item for item in items if item.get("validity_state") == "stale"]
            ),
            "replay_only_items": len(
                [item for item in items if item.get("validity_state") == "replay_only"]
            ),
        },
    )
    record_timing(f"query.{query.name}", duration_ms)
    artifact = _persist_query_result(result)
    cache_meta = set_cache(
        "runtime-query", query.to_dict(), {"artifact": artifact, "total": total}
    )
    result.cache = cache_meta
    return result


def explain_query_system() -> dict[str, Any]:
    """Explain query registry, scopes, dependencies."""
    registry = default_query_registry()
    ordered = registry.ordered()
    return {
        "queries": [
            {
                "name": item.name,
                "scope": item.scope,
                "dependencies": list(item.dependencies),
                "replay_safe": item.replay_safe,
            }
            for item in ordered
        ],
        "scopes": [scope.to_dict() for scope in registry.scopes.values()],
        "dependencies": [edge.to_dict() for edge in registry.dependencies()],
    }
