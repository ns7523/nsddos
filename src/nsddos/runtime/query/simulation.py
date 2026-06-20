"""Simulation query adapters."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.simulation import build_simulation_diagnostics, generate_attack_traffic


def query_simulation(config: dict[str, Any], query) -> dict[str, Any]:
    contract = generate_attack_traffic(config)
    payload = contract.to_dict()
    return {
        "items": [
            {
                "id": "simulation",
                "type": "simulation",
                "attack_type": payload["attack_type"],
                "target_ip": payload["target_ip"],
                "packet_rate": payload["packet_rate"],
                "byte_rate": payload["byte_rate"],
                "duration_seconds": payload["duration_seconds"],
                "intensity_level": payload["intensity_level"],
                "timestamp": payload["timestamp"],
            }
        ],
        "contract": payload,
    }


def query_simulation_replay(config: dict[str, Any], query) -> dict[str, Any]:
    contract = generate_attack_traffic(config, replay_mode=True)
    return {
        "items": [
            {
                "id": "simulation-replay",
                "type": "simulation_replay",
                "attack_type": contract.attack_type,
                "target_ip": contract.target_ip,
                "replay_records": len(contract.replay_records),
                "duration_seconds": contract.duration_seconds,
                "timestamp": contract.timestamp.isoformat(),
            }
        ]
    }


def query_simulation_diagnostics(config: dict[str, Any], query) -> dict[str, Any]:
    contract = generate_attack_traffic(config, replay_mode=True)
    diagnostics = build_simulation_diagnostics(contract)
    payload = diagnostics.to_dict()
    return {
        "items": [
            {
                "id": "simulation-diagnostics",
                "type": "simulation_diagnostics",
                "attack_type": contract.attack_type,
                "packet_count": payload["packet_count"],
                "byte_count": payload["byte_count"],
                "schedule_duration_ms": payload["schedule_duration_ms"],
                "replay_drift_detected": payload["replay_drift_detected"],
                "timestamp": contract.timestamp.isoformat(),
            }
        ]
    }


def query_simulation_topology(config: dict[str, Any], query) -> dict[str, Any]:
    contract = generate_attack_traffic(config)
    return {
        "items": [
            {
                "id": "simulation-topology",
                "type": "simulation_topology",
                "attack_type": contract.attack_type,
                "target_ip": contract.target_ip,
                "topology_path": list(contract.topology_path),
                "timestamp": contract.timestamp.isoformat(),
            }
        ]
    }
