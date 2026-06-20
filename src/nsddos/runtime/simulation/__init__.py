"""Deterministic attack simulation subsystem."""

from nsddos.runtime.simulation.diagnostics import build_simulation_diagnostics
from nsddos.runtime.simulation.engine import generate_attack_traffic, latest_simulation_contract
from nsddos.runtime.simulation.validation import validate_attack_contract


def contract_to_detection_telemetry(contract) -> dict[str, object]:
    top_source = contract.source_ip_pool[0] if contract.source_ip_pool else "10.0.0.254"
    top_port = contract.target_ports[0] if contract.target_ports else 80
    return {
        "provider_source": "simulation-engine",
        "timestamp": contract.timestamp.isoformat(),
        "sample_window_seconds": 1.0,
        "flows": [
            {
                "source": top_source,
                "destination_port": top_port,
                "packets": contract.packet_rate,
                "bytes": contract.byte_rate,
                "connections": contract.connection_rate,
                "syn_rate": contract.packet_rate if contract.attack_type == "syn_flood" else 0.0,
                "udp_rate": contract.packet_rate if contract.attack_type == "udp_flood" else 0.0,
                "icmp_rate": contract.packet_rate if contract.attack_type == "icmp_flood" else 0.0,
                "duration": 1.0,
                "protocol": contract.attack_type.split("_")[0],
            }
        ],
        "flow_state": {
            "flow_count": len(contract.packet_metadata),
            "telemetry_present": True,
            "detail": f"simulation attack={contract.attack_type}",
        },
        "telemetry_state": {
            "collector_reachable": True,
            "active_flow_count": len(contract.packet_metadata),
        },
        "freshness_state": {
            "sample_interval_seconds": 1.0,
            "stale": False,
        },
    }


def contract_to_collection_state(contract) -> dict[str, dict[str, object]]:
    return {
        "provider_status": {
            "simulation": {
                "provider": "simulation",
                "enabled": True,
                "attack_type": contract.attack_type,
                "target_ip": contract.target_ip,
                "packet_rate": contract.packet_rate,
                "ready": True,
            }
        },
        "flow_state": {
            "collector_reachable": True,
            "telemetry_present": True,
            "flow_count": len(contract.packet_metadata),
            "switches_visible": list(contract.topology_path),
            "interfaces_visible": list(contract.source_ip_pool),
            "metrics_changed": True,
            "detail": f"simulation attack={contract.attack_type}",
        },
        "freshness_state": {
            "last_flow_timestamp": contract.timestamp.isoformat(),
            "sample_interval_seconds": 1.0,
            "stale": False,
            "detail": "simulation-generated",
        },
        "telemetry_state": {
            "collector_reachable": True,
            "flow_api_ready": True,
            "metrics_available": True,
            "topology_published": bool(contract.topology_path),
            "active_flow_count": len(contract.packet_metadata),
            "last_flow_timestamp": contract.timestamp.isoformat(),
            "update_interval_seconds": 1.0,
            "stale": False,
            "visible_interfaces": list(contract.source_ip_pool),
        },
    }

__all__ = [
    "generate_attack_traffic",
    "latest_simulation_contract",
    "build_simulation_diagnostics",
    "validate_attack_contract",
    "contract_to_detection_telemetry",
    "contract_to_collection_state",
]
