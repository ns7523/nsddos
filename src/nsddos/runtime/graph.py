"""Runtime graph export."""

from __future__ import annotations

import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.correlation import correlate_runtime_events
from nsddos.runtime.controller import normalize_controller_topology
from nsddos.runtime.convergence import validate_convergence
from nsddos.runtime.environment import validate_runtime_environment
from nsddos.runtime.execution_graph import build_execution_graph
from nsddos.runtime.identity import build_identity_map
from nsddos.runtime.interfaces import correlate_interfaces
from nsddos.runtime.models import GraphArtifact
from nsddos.runtime.openflow import correlate_openflow_ports
from nsddos.runtime.paths import correlate_paths
from nsddos.runtime.profiles import detect_runtime_profile
from nsddos.runtime.reconcile import reconcile_runtime
from nsddos.runtime.reproducibility import analyze_reproducibility
from nsddos.runtime.stability import analyze_runtime_stability
from nsddos.runtime.timeline import build_runtime_history_timeline
from nsddos.runtime.topology import correlate_topology
from nsddos.runtime.transitions import load_transition_history
from nsddos.runtime.verification.replay import replay_verification_runs
from nsddos.runtime.verification.validators import default_registry
from nsddos.runtime.query.engine import explain_query_system
from nsddos.runtime.domain.graph import RuntimeEntity
from nsddos.runtime.domain.identifiers import graph_id
from nsddos.runtime.domain.relationships import RuntimeRelationship
from nsddos.runtime.domain.serialization import to_canonical_dict
from nsddos.runtime.performance import record_timing
from nsddos.service.persistence import load_heartbeat, load_service_state
from nsddos.service.replay import replay_service_events
from nsddos.service.sessions import list_sessions


def build_runtime_graph(config: dict[str, Any]) -> dict[str, Any]:
    """Build normalized runtime graph payload."""
    identity = build_identity_map(config)
    interfaces = correlate_interfaces(config)
    controller = normalize_controller_topology(config)
    convergence = validate_convergence(config)
    profile = detect_runtime_profile()
    environment = validate_runtime_environment(config)
    reproducibility = analyze_reproducibility(config)
    execution = build_execution_graph(config)
    timeline = build_runtime_history_timeline()
    transitions = load_transition_history()
    correlation = correlate_runtime_events()
    stability = analyze_runtime_stability()
    openflow = correlate_openflow_ports(config)
    paths = correlate_paths(config)
    topology = correlate_topology(config)
    reconciliation = reconcile_runtime(config)
    verification_registry = default_registry()
    verification_replay = replay_verification_runs()
    query_system = explain_query_system()
    service_state = load_service_state()
    service_sessions = list_sessions()
    service_heartbeat = load_heartbeat()
    service_replay = replay_service_events()
    try:
        from nsddos.api.app import get_route_summary

        api_summary = get_route_summary()
    except Exception:
        api_summary = {"routes": []}

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    profile_id = f"profile:{profile.name}"
    nodes.append(
        {"id": profile_id, "type": "runtime_profile", "platform": profile.platform}
    )
    for capability in profile.supported_capabilities:
        capability_id = f"capability:{capability}"
        nodes.append({"id": capability_id, "type": "capability"})
        edges.append(
            {"source": profile_id, "target": capability_id, "type": "supports"}
        )
    repro_id = f"reproducibility:{reproducibility.status}"
    nodes.append({"id": repro_id, "type": "reproducibility"})
    edges.append(
        {"source": profile_id, "target": repro_id, "type": "profile_reproducibility"}
    )
    for provider, status in environment.provider_support.items():
        provider_id = f"provider:{provider}"
        nodes.append(
            {"id": provider_id, "type": "provider_capability", "status": status}
        )
        edges.append(
            {"source": profile_id, "target": provider_id, "type": "provider_support"}
        )
    for phase in execution.get("nodes", []):
        phase_id = f"phase:{phase['id']}"
        nodes.append(
            {"id": phase_id, "type": "execution_phase", "gate": phase.get("gate", "")}
        )
    for edge in execution.get("edges", []):
        edges.append(
            {
                "source": f"phase:{edge['source']}",
                "target": f"phase:{edge['target']}",
                "type": "execution_dependency",
            }
        )
    for rule in verification_registry.ordered_rules():
        validator_id = f"validator:{rule.name}"
        category_id = f"verification_category:{rule.category}"
        nodes.append(
            {
                "id": validator_id,
                "type": "verification_validator",
                "category": rule.category,
            }
        )
        nodes.append({"id": category_id, "type": "verification_category"})
        edges.append(
            {"source": category_id, "target": validator_id, "type": "owns_validator"}
        )
        for dependency in rule.dependencies:
            edges.append(
                {
                    "source": f"validator:{dependency}",
                    "target": validator_id,
                    "type": "validator_dependency",
                }
            )
    for index, run in enumerate(verification_replay.get("runs", [])):
        run_id = f"verification_run:{index}"
        nodes.append(
            {
                "id": run_id,
                "type": "verification_run",
                "severity": run.get("severity", "unknown"),
            }
        )
        edges.append(
            {
                "source": "phase:verification_execute",
                "target": run_id,
                "type": "verification_replay",
            }
        )
    for query in query_system.get("queries", []):
        query_id = f"query:{query['name']}"
        scope_id = f"query_scope:{query['scope']}"
        nodes.append({"id": query_id, "type": "runtime_query", "scope": query["scope"]})
        nodes.append({"id": scope_id, "type": "runtime_query_scope"})
        edges.append({"source": scope_id, "target": query_id, "type": "query_scope"})
        edges.append(
            {
                "source": "phase:query_execute",
                "target": query_id,
                "type": "query_execution",
            }
        )
        for dependency in query.get("dependencies", []):
            edges.append(
                {
                    "source": f"query:{dependency}",
                    "target": query_id,
                    "type": "query_dependency",
                }
            )
    for route in api_summary.get("routes", []):
        route_id = f"api:{route['path']}:{','.join(route['methods'])}"
        nodes.append(
            {
                "id": route_id,
                "type": "api_endpoint",
                "path": route["path"],
                "methods": route["methods"],
            }
        )
        edges.append(
            {
                "source": "phase:api_query_bind",
                "target": route_id,
                "type": "api_route_binding",
            }
        )
        if route["path"].startswith("/runtime/query"):
            edges.append(
                {
                    "source": route_id,
                    "target": "query:snapshots",
                    "type": "api_query_surface",
                }
            )
        elif "/verification" in route["path"]:
            edges.append(
                {
                    "source": route_id,
                    "target": "query:verification",
                    "type": "api_query_surface",
                }
            )
        elif "/graph" in route["path"]:
            edges.append(
                {
                    "source": route_id,
                    "target": "query:graph",
                    "type": "api_query_surface",
                }
            )
        elif "/evidence" in route["path"]:
            edges.append(
                {
                    "source": route_id,
                    "target": "query:evidence",
                    "type": "api_query_surface",
                }
            )
        elif "/timeline" in route["path"]:
            edges.append(
                {
                    "source": route_id,
                    "target": "query:timeline",
                    "type": "api_query_surface",
                }
            )
        elif "/snapshots" in route["path"]:
            edges.append(
                {
                    "source": route_id,
                    "target": "query:snapshots",
                    "type": "api_query_surface",
                }
            )
        elif "/replay" in route["path"]:
            edges.append(
                {
                    "source": route_id,
                    "target": "query:replay",
                    "type": "api_query_surface",
                }
            )
    service_id = f"service:{service_state.service_id}"
    nodes.append(
        {
            "id": service_id,
            "type": "service_node",
            "state": service_state.state,
            "degraded": service_state.degraded,
        }
    )
    edges.append(
        {
            "source": "phase:service_start",
            "target": service_id,
            "type": "service_lifecycle",
        }
    )
    for session in service_sessions:
        session_id = f"service_session:{session.session_id}"
        nodes.append(
            {
                "id": session_id,
                "type": "session_node",
                "state": session.state,
                "lifecycle": session.lifecycle,
            }
        )
        edges.append(
            {"source": service_id, "target": session_id, "type": "service_session"}
        )
        edges.append(
            {
                "source": "phase:service_sync",
                "target": session_id,
                "type": "synchronization_edge",
            }
        )
    for index, heartbeat in enumerate(service_heartbeat.get("heartbeats", [])[-20:]):
        heartbeat_id = f"heartbeat:{index}"
        nodes.append(
            {
                "id": heartbeat_id,
                "type": "heartbeat_node",
                "service_state": heartbeat.get("service_state", "unknown"),
            }
        )
        edges.append(
            {"source": service_id, "target": heartbeat_id, "type": "heartbeat_edge"}
        )
    stream_id = "service_stream:internal"
    nodes.append(
        {
            "id": stream_id,
            "type": "stream_node",
            "events": service_replay.get("event_count", 0),
        }
    )
    edges.append({"source": service_id, "target": stream_id, "type": "stream_edge"})
    edges.append(
        {
            "source": "phase:service_finalize",
            "target": stream_id,
            "type": "replay_session_edge",
        }
    )

    for switch in identity.switches:
        nodes.append(
            {"id": switch.canonical_id, "type": "switch", "aliases": switch.aliases}
        )
    for switch in controller.switches:
        nodes.append(
            {
                "id": switch.canonical_id,
                "type": "controller_switch",
                "datapath_id": switch.datapath_id,
                "connected": switch.connected,
            }
        )
        if switch.datapath_id:
            edges.append(
                {
                    "source": switch.canonical_id,
                    "target": f"switch:{switch.datapath_id}",
                    "type": "controller_identity",
                }
            )
    for host in topology.expected_hosts:
        nodes.append({"id": f"host:{host}", "type": "host"})
        edges.append({"source": "switch:s1", "target": f"host:{host}", "type": "link"})
    for interface in interfaces.interfaces:
        nodes.append(
            {
                "id": interface.canonical_id,
                "type": "interface",
                "visible_in_ovs": interface.visible_in_ovs,
                "visible_in_sflow": interface.visible_in_sflow,
            }
        )
        if interface.switch_id:
            edges.append(
                {
                    "source": interface.switch_id,
                    "target": interface.canonical_id,
                    "type": "has_interface",
                }
            )
    for port in openflow.ports:
        nodes.append(
            {
                "id": port.canonical_id,
                "type": "openflow_port",
                "datapath_id": port.datapath_id,
                "port_no": port.port_no,
                "visible_in_controller": port.visible_in_controller,
                "visible_in_sflow": port.visible_in_sflow,
            }
        )
        if port.switch_id:
            edges.append(
                {
                    "source": port.switch_id,
                    "target": port.canonical_id,
                    "type": "has_port",
                }
            )
        if port.ovs_name:
            edges.append(
                {
                    "source": port.canonical_id,
                    "target": f"iface:{port.ovs_name}",
                    "type": "maps_interface",
                }
            )
    for switch in controller.switches:
        for port in switch.ports:
            controller_port_id = (
                f"{switch.canonical_id}:port:{port.port_no or 'unknown'}"
            )
            nodes.append(
                {
                    "id": controller_port_id,
                    "type": "controller_port",
                    "name": port.name,
                    "port_no": port.port_no,
                }
            )
            edges.append(
                {
                    "source": switch.canonical_id,
                    "target": controller_port_id,
                    "type": "has_controller_port",
                }
            )
            if port.name:
                edges.append(
                    {
                        "source": controller_port_id,
                        "target": f"iface:{port.name}",
                        "type": "controller_port_map",
                    }
                )
    for path in paths.observed_paths:
        nodes.append(
            {
                "id": path.canonical_id,
                "type": "path",
                "visible_in_controller": path.visible_in_controller,
                "visible_in_telemetry": path.visible_in_telemetry,
            }
        )
        edges.append(
            {
                "source": path.source_id,
                "target": path.canonical_id,
                "type": "path_source",
            }
        )
        edges.append(
            {
                "source": path.canonical_id,
                "target": path.target_id,
                "type": "path_target",
            }
        )
        if path.port_id:
            edges.append(
                {
                    "source": path.port_id,
                    "target": path.canonical_id,
                    "type": "path_port",
                }
            )
    for link in controller.links:
        if link.source_dpid and link.target_dpid:
            edges.append(
                {
                    "source": f"controller:{link.source_dpid}",
                    "target": f"controller:{link.target_dpid}",
                    "type": "controller_link",
                }
            )
    for index, item in enumerate(transitions):
        node_id = f"transition:{index}"
        nodes.append({"id": node_id, "type": "transition"})
        for entity in item.get("runtime", {}).get("affected_entities", []):
            edges.append(
                {"source": node_id, "target": str(entity), "type": "transition_affects"}
            )

    graph_start = monotonic()
    typed_nodes = tuple(
        RuntimeEntity(
            entity_id=str(
                node.get("id", graph_id(str(node.get("type", "node")), str(node)))
            ),
            entity_type=str(node.get("type", "node")),
            label=str(node.get("id", "")),
            detail=str(
                {key: value for key, value in node.items() if key not in {"id", "type"}}
            ),
        )
        for node in nodes
    )
    typed_relationships = tuple(
        RuntimeRelationship(
            relationship_type=str(edge.get("type", "relationship")),
            source_id=str(edge.get("source", "")),
            target_id=str(edge.get("target", "")),
            detail=str(
                {
                    key: value
                    for key, value in edge.items()
                    if key not in {"source", "target", "type"}
                }
            ),
        )
        for edge in edges
    )
    typed_node_payload = []
    for index, item in enumerate(typed_nodes):
        payload = to_canonical_dict(item)
        payload["id"] = nodes[index].get("id", payload.get("entity_id", ""))
        payload["type"] = nodes[index].get("type", payload.get("entity_type", ""))
        for key, value in nodes[index].items():
            if key not in {"id", "type"}:
                payload[key] = value
        typed_node_payload.append(payload)
    typed_edge_payload = []
    for index, item in enumerate(typed_relationships):
        payload = to_canonical_dict(item)
        payload["source"] = edges[index].get("source", payload.get("source_id", ""))
        payload["target"] = edges[index].get("target", payload.get("target_id", ""))
        payload["type"] = edges[index].get("type", payload.get("relationship_type", ""))
        typed_edge_payload.append(payload)
    record_timing("domain.graph.typing", (monotonic() - graph_start) * 1000)

    return {
        "nodes": typed_node_payload,
        "edges": typed_edge_payload,
        "controller": controller.to_dict(),
        "runtime_profile": profile.to_dict(),
        "environment": environment.to_dict(),
        "reproducibility": reproducibility.to_dict(),
        "execution_graph": execution,
        "convergence": convergence.to_dict(),
        "timeline": [item.to_dict() for item in timeline],
        "transitions": transitions,
        "correlation": correlation,
        "stability": stability,
        "topology": topology.to_dict(),
        "interfaces": interfaces.to_dict(),
        "openflow": openflow.to_dict(),
        "paths": paths.to_dict(),
        "identity": identity.to_dict(),
        "reconciliation": reconciliation.to_dict(),
        "verification": {
            "validators": [
                rule.to_dict() for rule in verification_registry.ordered_rules()
            ],
            "replay": verification_replay,
        },
        "query": query_system,
        "api": api_summary,
        "service": {
            "state": service_state.to_dict(),
            "sessions": [item.to_dict() for item in service_sessions],
            "heartbeat": service_heartbeat,
            "replay": service_replay,
        },
    }


def _graph_as_mermaid(graph: dict[str, Any]) -> str:
    """Render Mermaid graph."""
    lines = ["graph TD"]
    for node in graph.get("nodes", []):
        lines.append(
            f"    {node['id'].replace(':', '_').replace('-', '_')}[{node['id']}]"
        )
    for edge in graph.get("edges", []):
        source = edge["source"].replace(":", "_").replace("-", "_")
        target = edge["target"].replace(":", "_").replace("-", "_")
        lines.append(f"    {source} -->|{edge['type']}| {target}")
    return "\n".join(lines) + "\n"


def _graph_as_dot(graph: dict[str, Any]) -> str:
    """Render Graphviz DOT graph."""
    lines = ["digraph nsddos_runtime {"]
    for node in graph.get("nodes", []):
        lines.append(f'  "{node["id"]}" [label="{node["id"]}"];')
    for edge in graph.get("edges", []):
        lines.append(
            f'  "{edge["source"]}" -> "{edge["target"]}" [label="{edge["type"]}"];'
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def export_runtime_graph(config: dict[str, Any]) -> GraphArtifact:
    """Export graph JSON, Mermaid, DOT."""
    graph_dir = RUNTIME_DIR / "graphs"
    graph_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    graph = build_runtime_graph(config)

    json_path = graph_dir / f"runtime-graph-{timestamp}.json"
    mermaid_path = graph_dir / f"runtime-graph-{timestamp}.mmd"
    dot_path = graph_dir / f"runtime-graph-{timestamp}.dot"

    json_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    mermaid_path.write_text(_graph_as_mermaid(graph), encoding="utf-8")
    dot_path.write_text(_graph_as_dot(graph), encoding="utf-8")

    return GraphArtifact(
        json_path=str(json_path),
        mermaid_path=str(mermaid_path),
        dot_path=str(dot_path),
    )


def export_runtime_bundle(config: dict[str, Any]) -> Path:
    """Export portable runtime archive."""
    from nsddos.runtime.telemetry import build_runtime_snapshot

    export_dir = RUNTIME_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_path = export_dir / f"runtime-bundle-{timestamp}.tar.gz"

    graph = export_runtime_graph(config)
    snapshot = build_runtime_snapshot(config)
    snapshot_path = export_dir / f"runtime-snapshot-{timestamp}.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    with tarfile.open(bundle_path, "w:gz") as archive:
        archive.add(snapshot_path, arcname=snapshot_path.name)
        archive.add(graph.json_path, arcname=Path(graph.json_path).name)
        archive.add(graph.mermaid_path, arcname=Path(graph.mermaid_path).name)
        archive.add(graph.dot_path, arcname=Path(graph.dot_path).name)
    return bundle_path


def export_runtime_relationships(config: dict[str, Any]) -> dict[str, str]:
    """Export relationship-focused artifacts."""
    rel_dir = RUNTIME_DIR / "relationships"
    rel_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    graph = build_runtime_graph(config)
    json_path = rel_dir / f"runtime-relationships-{timestamp}.json"
    mermaid_path = rel_dir / f"runtime-relationships-{timestamp}.mmd"
    json_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    mermaid_path.write_text(_graph_as_mermaid(graph), encoding="utf-8")
    return {"json_path": str(json_path), "mermaid_path": str(mermaid_path)}


def export_runtime_history(config: dict[str, Any]) -> dict[str, str]:
    """Export runtime history artifacts."""
    history_dir = RUNTIME_DIR / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "timeline": [item.to_dict() for item in build_runtime_history_timeline()],
        "transitions": load_transition_history(),
        "correlation": correlate_runtime_events(),
        "stability": analyze_runtime_stability(),
    }
    json_path = history_dir / f"runtime-history-{timestamp}.json"
    mermaid_path = history_dir / f"runtime-history-{timestamp}.mmd"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    mermaid_lines = ["graph TD"]
    for index, item in enumerate(payload["timeline"]):
        mermaid_lines.append(f"    ev{index}[\"{item['event_type']}\"]")
        if index:
            mermaid_lines.append(f"    ev{index-1} --> ev{index}")
    mermaid_path.write_text("\n".join(mermaid_lines) + "\n", encoding="utf-8")
    return {"json_path": str(json_path), "mermaid_path": str(mermaid_path)}
