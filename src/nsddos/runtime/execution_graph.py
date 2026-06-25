"""Runtime execution graph model."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.pipeline import build_execution_plan


def build_execution_graph(
    config: dict[str, Any], preset: str = "minimal-lab"
) -> dict[str, Any]:
    """Build canonical execution DAG."""
    plan = build_execution_plan(config, preset=preset)
    nodes = [
        {
            "id": phase.name,
            "type": "runtime_phase",
            "gate": phase.gate,
            "providers": phase.providers,
            "required": phase.required,
        }
        for phase in plan.phases
    ]
    edges = [
        {
            "source": dep.source,
            "target": dep.target,
            "type": "phase_dependency",
            "reason": dep.reason,
        }
        for dep in plan.dependencies
    ]
    return {"plan": plan.to_dict(), "nodes": nodes, "edges": edges}


def execution_graph_mermaid(graph: dict[str, Any]) -> str:
    """Render execution graph as Mermaid."""
    lines = ["graph TD"]
    for node in graph.get("nodes", []):
        node_id = str(node["id"]).replace("-", "_")
        lines.append(f"    {node_id}[{node['id']}]")
    for edge in graph.get("edges", []):
        source = str(edge["source"]).replace("-", "_")
        target = str(edge["target"]).replace("-", "_")
        lines.append(f"    {source} -->|{edge.get('reason', '')}| {target}")
    return "\n".join(lines) + "\n"


def export_execution_graph(
    config: dict[str, Any], preset: str = "minimal-lab"
) -> dict[str, str]:
    """Export execution graph artifacts."""
    export_dir = RUNTIME_DIR / "pipeline"
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    graph = build_execution_graph(config, preset=preset)
    json_path = export_dir / f"execution-pipeline-{stamp}.json"
    mermaid_path = export_dir / f"execution-pipeline-{stamp}.mmd"
    json_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    mermaid_path.write_text(execution_graph_mermaid(graph), encoding="utf-8")
    return {"json_path": str(json_path), "mermaid_path": str(mermaid_path)}
