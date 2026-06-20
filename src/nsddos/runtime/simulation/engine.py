"""Deterministic simulation engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import atomic_write_json, read_json_checked
from nsddos.runtime.simulation.contracts import AttackTrafficContract
from nsddos.runtime.simulation.diagnostics import build_simulation_diagnostics
from nsddos.runtime.simulation.patterns import (
    burst_pattern,
    exponential_ramp_up_pattern,
    random_burst_pattern,
    sustained_pattern,
    wave_attack_pattern,
)
from nsddos.runtime.simulation.registry import build_registry
from nsddos.runtime.simulation.replay import build_replay_records
from nsddos.runtime.simulation.scheduler import build_schedule
from nsddos.runtime.simulation.targets import select_target
from nsddos.runtime.simulation.topology import resolve_topology_path
from nsddos.runtime.simulation.traffic import generate_packet_metadata
from nsddos.runtime.simulation.validation import validate_attack_contract

SIMULATION_DIR = RUNTIME_DIR / "simulation"


def _settings(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("runtime", {}).get("simulation", {})


def _pattern_offsets(name: str, packet_rate: float, duration_seconds: int) -> tuple[int, ...]:
    if name == "burst":
        return burst_pattern(packet_rate, duration_seconds)
    if name == "sustained":
        return sustained_pattern(packet_rate, duration_seconds)
    if name == "exponential_ramp_up":
        return exponential_ramp_up_pattern(packet_rate, duration_seconds)
    if name == "random_burst":
        return random_burst_pattern(packet_rate, duration_seconds)
    return wave_attack_pattern(packet_rate, duration_seconds)


def _persist_contract(contract: AttackTrafficContract) -> None:
    SIMULATION_DIR.mkdir(parents=True, exist_ok=True)
    payload = contract.to_dict()
    stamp = contract.timestamp.isoformat().replace(":", "").replace("-", "")
    atomic_write_json(SIMULATION_DIR / f"simulation-{stamp}.json", payload)
    atomic_write_json(SIMULATION_DIR / "latest.json", payload)


def latest_simulation_contract() -> dict[str, Any]:
    path = SIMULATION_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def generate_attack_traffic(
    config: dict[str, Any],
    *,
    attack_type: str | None = None,
    target_kind: str | None = None,
    target_value: str = "",
    intensity_level: str | None = None,
    duration_seconds: int | None = None,
    replay_mode: bool | None = None,
) -> AttackTrafficContract:
    settings = _settings(config)
    selected_attack = attack_type or settings.get("default_attack_type", "syn_flood")
    selected_intensity = intensity_level or settings.get("default_intensity_level", "medium")
    selected_duration = int(duration_seconds or settings.get("default_duration_seconds", 10))
    selected_replay = bool(settings.get("default_replay_mode", False) if replay_mode is None else replay_mode)
    selected_target_kind = target_kind or settings.get("targets", {}).get("default_kind", "host")

    registry = build_registry()
    entry = registry.lookup(selected_attack)
    profile = entry.generator(selected_intensity, selected_duration)
    target = select_target(config, target_kind=selected_target_kind, target_value=target_value)
    packets = generate_packet_metadata(profile, target)
    offsets = _pattern_offsets(profile.pattern_name, profile.packet_rate, profile.duration_seconds)
    schedule = build_schedule(
        offsets,
        start_delay_seconds=int(settings.get("scheduler", {}).get("start_delay_seconds", 0)),
        repeat_interval_seconds=int(settings.get("scheduler", {}).get("repeat_interval_seconds", 0)),
    )
    topology = resolve_topology_path(target)
    replay_records = build_replay_records(packets, schedule) if selected_replay else ()
    timestamp = datetime.now(timezone.utc)
    contract = AttackTrafficContract(
        attack_type=profile.attack_type,
        target_ip=target.target_ip,
        packet_rate=profile.packet_rate,
        byte_rate=profile.byte_rate,
        connection_rate=profile.connection_rate,
        duration_seconds=profile.duration_seconds,
        source_ip_pool=profile.source_ip_pool,
        target_ports=target.target_ports or profile.target_ports,
        intensity_level=profile.intensity_level,
        replay_mode=selected_replay,
        topology_path=topology.hops,
        timestamp=timestamp,
        packet_schedule=schedule,
        packet_metadata=packets,
        replay_records=replay_records,
        target_kind=target.target_kind,
        pattern_name=profile.pattern_name,
        diagnostics=build_simulation_diagnostics(
            AttackTrafficContract(
                attack_type=profile.attack_type,
                target_ip=target.target_ip,
                packet_rate=profile.packet_rate,
                byte_rate=profile.byte_rate,
                connection_rate=profile.connection_rate,
                duration_seconds=profile.duration_seconds,
                source_ip_pool=profile.source_ip_pool,
                target_ports=target.target_ports or profile.target_ports,
                intensity_level=profile.intensity_level,
                replay_mode=selected_replay,
                topology_path=topology.hops,
                timestamp=timestamp,
                packet_schedule=schedule,
                packet_metadata=packets,
                replay_records=replay_records,
                target_kind=target.target_kind,
                pattern_name=profile.pattern_name,
                created_at=timestamp.isoformat(),
            )
        ),
        created_at=timestamp.isoformat(),
    )
    errors = validate_attack_contract(contract)
    if errors:
        raise ValueError(f"simulation contract invalid: {','.join(errors)}")
    _persist_contract(contract)
    return contract
