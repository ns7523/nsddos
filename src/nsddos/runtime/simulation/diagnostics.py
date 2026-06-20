"""Simulation diagnostics."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import AttackTrafficContract, SimulationDiagnostics


def build_simulation_diagnostics(contract: AttackTrafficContract) -> SimulationDiagnostics:
    packet_count = len(contract.packet_metadata)
    byte_count = sum(item.size_bytes for item in contract.packet_metadata)
    schedule_duration_ms = max((item.emit_at_ms for item in contract.packet_schedule), default=0)
    invalid_bursts = []
    if contract.packet_rate <= 0:
        invalid_bursts.append("invalid_packet_rate")
    if contract.duration_seconds <= 0:
        invalid_bursts.append("invalid_duration")
    replay_drift_detected = any(
        item.preserved_timestamp_ms != contract.packet_schedule[index].emit_at_ms
        for index, item in enumerate(contract.replay_records[: len(contract.packet_schedule)])
    )
    return SimulationDiagnostics(
        packet_count=packet_count,
        byte_count=byte_count,
        schedule_duration_ms=schedule_duration_ms,
        invalid_packet_bursts=tuple(invalid_bursts),
        replay_drift_detected=replay_drift_detected,
    )
