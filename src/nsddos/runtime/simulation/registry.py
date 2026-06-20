"""Simulation registry."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class SimulationRegistryEntry:
    attack_type: str
    replay_capable: bool
    generator: object


@dataclass
class SimulationRegistry:
    entries: dict[str, SimulationRegistryEntry]

    def lookup(self, attack_type: str) -> SimulationRegistryEntry:
        if attack_type not in self.entries:
            raise ValueError(f"unknown simulation attack: {attack_type}")
        return self.entries[attack_type]

    def capabilities(self) -> dict[str, dict[str, object]]:
        return {
            name: {"replay_capable": entry.replay_capable}
            for name, entry in sorted(self.entries.items())
        }


def build_registry() -> SimulationRegistry:
    from nsddos.runtime.simulation.connection_exhaustion import build_connection_exhaustion_profile
    from nsddos.runtime.simulation.http_flood import build_http_flood_profile
    from nsddos.runtime.simulation.icmp_flood import build_icmp_flood_profile
    from nsddos.runtime.simulation.slowloris import build_slowloris_profile
    from nsddos.runtime.simulation.syn_flood import build_syn_flood_profile
    from nsddos.runtime.simulation.udp_flood import build_udp_flood_profile

    entries = {
        "syn_flood": SimulationRegistryEntry("syn_flood", True, build_syn_flood_profile),
        "udp_flood": SimulationRegistryEntry("udp_flood", True, build_udp_flood_profile),
        "icmp_flood": SimulationRegistryEntry("icmp_flood", True, build_icmp_flood_profile),
        "http_flood": SimulationRegistryEntry("http_flood", True, build_http_flood_profile),
        "slowloris": SimulationRegistryEntry("slowloris", True, build_slowloris_profile),
        "connection_exhaustion": SimulationRegistryEntry("connection_exhaustion", True, build_connection_exhaustion_profile),
    }
    return SimulationRegistry(entries)
