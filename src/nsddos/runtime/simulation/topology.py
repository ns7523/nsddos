"""Simulation topology routing."""

from __future__ import annotations

from nsddos.runtime.simulation.contracts import TargetSelection, TopologyPathRecord


def resolve_topology_path(target: TargetSelection) -> TopologyPathRecord:
    if target.target_kind == "controller":
        return TopologyPathRecord("controller_route", ("attacker", "s1", "controller"))
    if target.target_kind == "switch":
        return TopologyPathRecord("switch_route", ("attacker", "s1"))
    if target.target_kind == "subnet":
        return TopologyPathRecord(
            "subnet_route", ("attacker", "s1", target.identifier or target.target_ip)
        )
    return TopologyPathRecord(
        "host_route", ("attacker", "s1", target.identifier or target.target_ip)
    )
