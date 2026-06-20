from __future__ import annotations

from datetime import datetime, timezone

from nsddos.runtime.persistence import atomic_write_json
from nsddos.runtime.query.engine import execute_query, explain_query_system
from nsddos.runtime.query.filters import apply_filters
from nsddos.runtime.query.models import RuntimeQuery, RuntimeQueryFilter, RuntimeQueryPagination
from nsddos.runtime.query.pagination import paginate
from nsddos.runtime.query.registry import RuntimeQueryDefinition, RuntimeQueryRegistry, default_query_registry
from nsddos.runtime.query.selectors import select_graph_edges, select_graph_nodes


def test_query_registry_orders_dependencies():
    registry = RuntimeQueryRegistry()
    registry.register(RuntimeQueryDefinition("base", "runtime", lambda config, query: {"items": []}))
    registry.register(RuntimeQueryDefinition("child", "graph", lambda config, query: {"items": []}, ("base",)))

    assert [item.name for item in registry.ordered()] == ["base", "child"]
    assert registry.dependencies()[0].source == "base"


def test_query_registry_rejects_unknown_scope():
    registry = RuntimeQueryRegistry()
    try:
        registry.register(RuntimeQueryDefinition("bad", "unknown", lambda config, query: {"items": []}))
    except ValueError as exc:
        assert "unknown query scope" in str(exc)
    else:
        raise AssertionError("unknown scope must fail")


def test_filters_and_pagination_stable_ordering():
    items = [
        {"id": "b", "kind": "switch", "timestamp": "2"},
        {"id": "a", "kind": "host", "timestamp": "1"},
        {"id": "c", "kind": "switch", "timestamp": "3"},
    ]
    filtered = apply_filters(items, (RuntimeQueryFilter("kind", "switch"),))
    page = paginate(filtered, RuntimeQueryPagination(limit=1, offset=0))

    assert [item["id"] for item in filtered] == ["b", "c"]
    assert page[0]["id"] == "b"


def test_graph_selectors_filter_nodes_and_edges():
    graph = {
        "nodes": [{"id": "n2", "type": "query"}, {"id": "n1", "type": "switch"}],
        "edges": [{"source": "n1", "target": "n2", "type": "query_dependency"}],
    }

    assert select_graph_nodes(graph, "query")[0]["id"] == "n2"
    assert select_graph_edges(graph, "query_dependency")[0]["target"] == "n2"


def test_snapshot_query_executes_with_cache_and_artifact(tmp_path, monkeypatch):
    from nsddos.runtime import cache as cache_module
    from nsddos.runtime.query import engine as engine_module
    from nsddos.runtime.query import snapshots as snapshots_module

    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    atomic_write_json(
        snapshot_dir / "snapshot-1.json",
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "convergence_state": {"status": "converged"},
            "runtime_profile": {"name": "linux-native"},
        },
    )
    monkeypatch.setattr(snapshots_module, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(engine_module, "QUERY_DIR", tmp_path / "query")
    monkeypatch.setattr(cache_module, "CACHE_DIR", tmp_path / "cache")

    result = execute_query({}, RuntimeQuery(name="snapshots", scope="persistence"))

    assert result.total == 1
    assert result.items[0]["convergence"] == "converged"
    assert result.cache["key"].startswith("runtime-query")


def test_evidence_query_reads_schema_checked_bundle(tmp_path, monkeypatch):
    from nsddos.runtime.query import evidence as evidence_module

    evidence_dir = tmp_path / "evidence" / "run"
    evidence_dir.mkdir(parents=True)
    atomic_write_json(
        evidence_dir / "evidence.json",
        {
            "snapshot": {"timestamp": "2026-01-01T00:00:00Z"},
            "convergence": {"status": "partially_converged"},
            "verification": [{"name": "x"}],
        },
    )
    monkeypatch.setattr(evidence_module, "EVIDENCE_DIR", tmp_path / "evidence")

    payload = evidence_module.query_evidence({}, RuntimeQuery(name="evidence", scope="evidence"))

    assert payload["items"][0]["verification_count"] == 1
    assert payload["relationships"][0]["type"] == "evidence_convergence"


def test_explain_query_system_contains_required_queries():
    explanation = explain_query_system()
    names = {item["name"] for item in explanation["queries"]}

    assert {
        "snapshots",
        "evidence",
        "verification",
        "timeline",
        "graph",
        "replay",
        "detection",
        "stream_status",
        "policy_evaluate",
        "ml_infer",
    } <= names
    assert explanation["dependencies"]


def test_default_registry_missing_dependency_detection():
    registry = RuntimeQueryRegistry()
    registry.register(RuntimeQueryDefinition("broken", "runtime", lambda config, query: {"items": []}, ("missing",)))

    try:
        registry.ordered()
    except ValueError as exc:
        assert "missing query dependency" in str(exc)
    else:
        raise AssertionError("missing dependency must fail")


def test_default_query_registry_replay_safe_flags():
    registry = default_query_registry()

    assert all(item.replay_safe for item in registry.ordered())


def test_streaming_query_registry_dependencies():
    registry = default_query_registry()
    ordered = [item.name for item in registry.ordered()]

    assert ordered.index("stream_status") < ordered.index("stream_checkpoint") < ordered.index("stream_diagnostics")


def test_policy_query_registry_dependencies() -> None:
    registry = default_query_registry()
    ordered = [item.name for item in registry.ordered()]

    assert ordered.index("policy_evaluate") < ordered.index("policy_history") < ordered.index("policy_diagnostics")
    assert ordered.index("policy_history") < ordered.index("policy_rollback")


def test_ml_query_registry_dependencies() -> None:
    registry = default_query_registry()
    ordered = [item.name for item in registry.ordered()]

    assert ordered.index("ml_infer") < ordered.index("ml_diagnostics")
    assert ordered.index("ml_infer") < ordered.index("ml_train") < ordered.index("ml_retrain")
