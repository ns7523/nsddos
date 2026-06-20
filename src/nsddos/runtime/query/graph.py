"""Runtime graph querying."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.graph import build_runtime_graph
from nsddos.runtime.query.models import RuntimeQuery
from nsddos.runtime.query.selectors import select_graph_edges, select_graph_nodes


def query_graph(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query runtime graph nodes/edges."""
    graph = build_runtime_graph(config)
    node_type = None
    edge_type = None
    source = None
    target = None
    for query_filter in query.filters:
        if query_filter.field == "type":
            node_type = str(query_filter.value)
        if query_filter.field == "edge_type":
            edge_type = str(query_filter.value)
        if query_filter.field == "source":
            source = str(query_filter.value)
        if query_filter.field == "target":
            target = str(query_filter.value)
    nodes = select_graph_nodes(graph, node_type=node_type)
    edges = select_graph_edges(graph, edge_type=edge_type)
    if source is not None:
        edges = [item for item in edges if item.get("source") == source]
    if target is not None:
        edges = [item for item in edges if item.get("target") == target]
    items = [{"id": item.get("id", ""), **item} for item in nodes]
    relationships = [
        {
            "id": f"{item.get('source')}->{item.get('target')}",
            "edge_type": item.get("type", ""),
            **item,
        }
        for item in edges
    ]
    if source is not None or target is not None:
        items = relationships
    return {"items": items, "relationships": relationships, "graph": graph}
