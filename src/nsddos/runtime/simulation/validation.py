"""Simulation validation."""

from __future__ import annotations

import ipaddress

from nsddos.runtime.simulation.contracts import (
    AttackTrafficContract,
    INTENSITY_LEVELS,
    PATTERN_NAMES,
    SIMULATION_ATTACK_TYPES,
    TARGET_KINDS,
)


def validate_attack_contract(contract: AttackTrafficContract) -> list[str]:
    errors: list[str] = []
    if contract.attack_type not in SIMULATION_ATTACK_TYPES:
        errors.append("malformed_attack_generator_state")
    if contract.intensity_level not in INTENSITY_LEVELS:
        errors.append("malformed_attack_config")
    if contract.target_kind not in TARGET_KINDS:
        errors.append("invalid_target_kind")
    if contract.pattern_name not in PATTERN_NAMES:
        errors.append("invalid_packet_scheduling")
    if (
        contract.packet_rate <= 0
        or contract.byte_rate <= 0
        or contract.connection_rate < 0
    ):
        errors.append("invalid_packet_rate")
    if contract.duration_seconds <= 0:
        errors.append("invalid_duration")
    if not contract.topology_path:
        errors.append("invalid_topology_route")
    if contract.target_kind != "subnet":
        try:
            ipaddress.ip_address(contract.target_ip)
        except ValueError:
            errors.append("invalid_target_ip")
    if contract.replay_mode and not contract.replay_records:
        errors.append("invalid_replay_payload")
    return errors
