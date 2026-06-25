"""Controller event normalization."""

from __future__ import annotations

from nsddos.runtime.providers.live.contracts import (
    ControllerEventRecord,
    ProviderDiscoveryRecord,
    ProviderHealthRecord,
)


def normalize_controller_events(
    discovery: tuple[ProviderDiscoveryRecord, ...],
    health: tuple[ProviderHealthRecord, ...],
) -> tuple[ControllerEventRecord, ...]:
    events: list[ControllerEventRecord] = []
    for item in discovery:
        if item.controllers:
            for controller in item.controllers:
                events.append(
                    ControllerEventRecord(
                        "controller_discovery", item.provider, controller, "visible"
                    )
                )
        for switch in item.switches:
            events.append(
                ControllerEventRecord(
                    "switch_discovery", item.provider, switch, "visible"
                )
            )
    for item in health:
        events.append(
            ControllerEventRecord(
                "provider_health", item.provider, item.provider, item.state
            )
        )
    return tuple(events)
