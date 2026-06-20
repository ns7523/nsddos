"""Reusable runtime query selectors."""

from __future__ import annotations

from typing import Any


def select_fields(items: list[dict[str, Any]], fields: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Select stable subset of fields."""
    if not fields:
        return items
    return [{field: item.get(field) for field in fields} for item in items]


def select_graph_nodes(graph: dict[str, Any], node_type: str | None = None) -> list[dict[str, Any]]:
    """Select graph nodes."""
    nodes = list(graph.get("nodes", []))
    if node_type:
        nodes = [node for node in nodes if node.get("type") == node_type]
    return sorted(nodes, key=lambda item: str(item.get("id", "")))


def select_graph_edges(graph: dict[str, Any], edge_type: str | None = None) -> list[dict[str, Any]]:
    """Select graph edges."""
    edges = list(graph.get("edges", []))
    if edge_type:
        edges = [edge for edge in edges if edge.get("type") == edge_type]
    return sorted(edges, key=lambda item: f"{item.get('source', '')}->{item.get('target', '')}:{item.get('type', '')}")
