"""Live provider registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nsddos.providers.floodlight.provider import FloodlightProvider
from nsddos.providers.mininet.provider import MininetProvider
from nsddos.providers.ovs.provider import OVSProvider
from nsddos.providers.sflow.provider import SFlowProvider, resolve_sflowrt_api_url
from nsddos.runtime.providers.live.connection_pool import ConnectionPolicy, DeterministicConnectionPool


@dataclass(frozen=True)
class LiveProviderRegistry:
    pool: DeterministicConnectionPool
    sflowrt: SFlowProvider
    ovs: OVSProvider
    mininet: MininetProvider
    floodlight: FloodlightProvider

    def as_mapping(self) -> dict[str, object]:
        return {
            "sflowrt": self.sflowrt,
            "ovs": self.ovs,
            "mininet": self.mininet,
            "floodlight": self.floodlight,
        }


def build_live_provider_registry(config: dict[str, Any]) -> LiveProviderRegistry:
    live_config = config.get("runtime", {}).get("live", {})
    providers = live_config.get("providers", {})
    lab = config.get("lab", {})
    pool = DeterministicConnectionPool(
        ConnectionPolicy(
            timeout_seconds=float(live_config.get("timeout_seconds", 3.0)),
            retry_count=int(live_config.get("retry_count", 1)),
        )
    )
    sflow_endpoint = providers.get("sflowrt", {}).get("endpoint", resolve_sflowrt_api_url(config))
    floodlight_endpoint = providers.get("floodlight", {}).get("endpoint", f"http://127.0.0.1:{lab.get('floodlight_port', 8080)}")
    mininet_host = providers.get("mininet", {}).get("controller_host", "127.0.0.1")
    mininet_port = int(providers.get("mininet", {}).get("controller_port", lab.get("controller_port", 6653)))
    ovs_settings = providers.get("ovs", {})
    return LiveProviderRegistry(
        pool=pool,
        sflowrt=SFlowProvider(api_url=sflow_endpoint),
        ovs=OVSProvider(
            collector_target=ovs_settings.get("collector_target", lab.get("ovs_sflow_target", "127.0.0.1:6343")),
            agent_interface=ovs_settings.get("agent_interface", lab.get("ovs_agent_interface", "lo")),
            sampling=int(lab.get("ovs_sampling", 10)),
            polling=int(lab.get("ovs_polling", 20)),
        ),
        mininet=MininetProvider(
            controller_host=mininet_host,
            controller_port=mininet_port,
            topology=lab.get("mininet_topology", "single,3"),
        ),
        floodlight=FloodlightProvider(
            api_url=floodlight_endpoint,
            controller_host=mininet_host,
            controller_port=mininet_port,
        ),
    )
