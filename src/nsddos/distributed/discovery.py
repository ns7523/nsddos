"""Deterministic node discovery."""

from __future__ import annotations

import socket
from typing import Any

from nsddos.deployment.registry import latest_deployment_payload
from nsddos.runtime.verification.replay import replay_verification_runs


def discover_candidate_nodes(config: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Discover candidate nodes from config and local persisted state."""
    configured = config.get("distributed", {}).get("nodes", [])
    if isinstance(configured, list) and configured:
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(configured):
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "node_id": str(item.get("node_id") or f"node-{index + 1}"),
                    "hostname": str(item.get("hostname") or item.get("node_id") or f"node-{index + 1}"),
                    "roles": tuple(sorted(str(role) for role in item.get("roles", []))) or ("runtime",),
                    "capabilities": tuple(sorted(str(cap) for cap in item.get("capabilities", []))) or ("runtime",),
                    "worker_capacity": int(item.get("worker_capacity", 5)),
                    "state": str(item.get("state", "healthy")),
                    "source": "config",
                }
            )
        if normalized:
            return tuple(normalized)
    deployment = latest_deployment_payload()
    host = socket.gethostname() or "localhost"
    capabilities = ["runtime", "deployment"]
    if deployment.get("container_contracts"):
        capabilities.extend(["streaming", "policy", "ml"])
    replay = replay_verification_runs(limit=1)
    latest_verify = replay.get("runs", [{}])[-1] if replay.get("runs") else {}
    if latest_verify.get("severity") in {"failed", "critical"}:
        state = "degraded"
    else:
        state = "healthy"
    return (
        {
            "node_id": str(config.get("distributed", {}).get("local_node_id", host)),
            "hostname": host,
            "roles": ("runtime", "control"),
            "capabilities": tuple(sorted(set(capabilities))),
            "worker_capacity": 5,
            "source": "local",
            "state": state,
        },
    )
