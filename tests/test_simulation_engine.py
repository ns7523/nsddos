from __future__ import annotations

from pathlib import Path

from nsddos.runtime.simulation import (
    contract_to_collection_state,
    contract_to_detection_telemetry,
)


def _config() -> dict:
    return {
        "lab": {
            "controller_port": 6653,
            "mininet_topology": "single,3",
        },
        "runtime": {
            "simulation": {
                "default_attack_type": "syn_flood",
                "default_duration_seconds": 10,
                "default_intensity_level": "medium",
                "default_replay_mode": False,
                "scheduler": {"start_delay_seconds": 0, "repeat_interval_seconds": 0},
                "targets": {"default_kind": "host"},
            }
        },
    }


def _evaluate(tmp_path: Path, monkeypatch, **kwargs):
    from nsddos.runtime import simulation as simulation_pkg
    from nsddos.runtime.simulation import engine as simulation_engine

    monkeypatch.setattr(simulation_engine, "SIMULATION_DIR", tmp_path / "simulation")
    return simulation_pkg.generate_attack_traffic(_config(), **kwargs)


def test_syn_flood_generation(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(tmp_path, monkeypatch, attack_type="syn_flood")
    assert contract.attack_type == "syn_flood"
    assert contract.packet_rate == 1200.0


def test_udp_flood_generation(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(tmp_path, monkeypatch, attack_type="udp_flood")
    assert contract.attack_type == "udp_flood"
    assert contract.target_ports[0] == 80


def test_icmp_flood_generation(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(tmp_path, monkeypatch, attack_type="icmp_flood")
    assert contract.attack_type == "icmp_flood"
    assert contract.packet_metadata[0].protocol == "icmp"


def test_http_flood_generation(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(tmp_path, monkeypatch, attack_type="http_flood")
    assert contract.attack_type == "http_flood"
    assert contract.packet_metadata[0].payload_kind == "http_flood"


def test_slowloris_generation(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(tmp_path, monkeypatch, attack_type="slowloris")
    assert contract.attack_type == "slowloris"
    assert contract.connection_rate > contract.packet_rate


def test_connection_exhaustion_generation(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(tmp_path, monkeypatch, attack_type="connection_exhaustion")
    assert contract.attack_type == "connection_exhaustion"
    assert contract.connection_rate > 0


def test_replay_traffic_generation(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(
        tmp_path, monkeypatch, attack_type="syn_flood", replay_mode=True
    )
    assert len(contract.replay_records) == len(contract.packet_metadata)


def test_target_validation(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(
        tmp_path,
        monkeypatch,
        attack_type="syn_flood",
        target_kind="host",
        target_value="10.0.0.9",
    )
    assert contract.target_ip == "10.0.0.9"


def test_topology_path_generation(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(
        tmp_path, monkeypatch, attack_type="syn_flood", target_kind="controller"
    )
    assert contract.topology_path[-1] == "controller"


def test_deterministic_packet_scheduling(tmp_path: Path, monkeypatch) -> None:
    first = _evaluate(tmp_path, monkeypatch, attack_type="syn_flood", replay_mode=True)
    second = _evaluate(tmp_path, monkeypatch, attack_type="syn_flood", replay_mode=True)
    assert [item.emit_at_ms for item in first.packet_schedule] == [
        item.emit_at_ms for item in second.packet_schedule
    ]


def test_contract_to_detection_payload(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(tmp_path, monkeypatch, attack_type="udp_flood")
    telemetry = contract_to_detection_telemetry(contract)
    assert telemetry["flows"][0]["destination_port"] == contract.target_ports[0]


def test_contract_to_collection_state(tmp_path: Path, monkeypatch) -> None:
    contract = _evaluate(tmp_path, monkeypatch, attack_type="icmp_flood")
    state = contract_to_collection_state(contract)
    assert state["provider_status"]["simulation"]["attack_type"] == "icmp_flood"
    assert state["telemetry_state"]["active_flow_count"] == len(
        contract.packet_metadata
    )
