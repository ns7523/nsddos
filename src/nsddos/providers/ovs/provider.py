"""OVS runtime validation and sFlow wiring."""

from __future__ import annotations

from typing import Any

from nsddos.constants import DEFAULT_SFLOW_PORT
from nsddos.providers.base import BaseProvider
from nsddos.providers.ovs.utils import ovs_process_running, run_ovs_ofctl, run_ovs_vsctl
from nsddos.runtime.executor import RuntimeExecutor
from nsddos.runtime.models import OVSBridgeState, OVSState


class OVSProvider(BaseProvider):
    """Open vSwitch provider."""

    def __init__(
        self,
        collector_target: str = f"127.0.0.1:{DEFAULT_SFLOW_PORT}",
        agent_interface: str = "lo",
        sampling: int = 10,
        polling: int = 20,
        expected_protocol: str = "OpenFlow13",
    ) -> None:
        if collector_target == f"127.0.0.1:{DEFAULT_SFLOW_PORT}":
            collector_target = f"sflowrt:{DEFAULT_SFLOW_PORT}"
        self.collector_target = collector_target
        self.agent_interface = agent_interface
        self.sampling = sampling
        self.polling = polling
        self.expected_protocol = expected_protocol
        self.executor = RuntimeExecutor()

    def is_installed(self) -> bool:
        """Check labhost runtime availability."""

        return self.executor.lab_container_running()

    @staticmethod
    def service_running() -> bool:
        """Check OVS daemon process."""

        return ovs_process_running()

    def list_bridges(self) -> list[str]:
        """List OVS bridges."""

        result = run_ovs_vsctl(["--timeout=1", "list-br"], timeout=5)
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def list_interfaces(self, bridge: str) -> list[str]:
        """List bridge interfaces."""

        result = run_ovs_vsctl(["list-ports", bridge], timeout=5)
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def bridge_exists(self, bridge: str) -> bool:
        """Check bridge existence."""

        return bridge in self.list_bridges()

    def bridge_protocols(self, bridge: str) -> list[str]:
        """Return configured bridge protocols."""

        if not self.bridge_exists(bridge):
            return []
        result = run_ovs_vsctl(["get", "bridge", bridge, "protocols"], timeout=5)
        if result.returncode != 0:
            return []
        raw = result.stdout.strip()
        if raw in {"", "[]"}:
            return []
        cleaned = raw.strip("[]")
        return [item.strip().strip('"') for item in cleaned.split(",") if item.strip()]

    def bridge_has_protocol(self, bridge: str, protocol: str | None = None) -> bool:
        """Check whether bridge is pinned to expected OpenFlow protocol."""

        target = protocol or self.expected_protocol
        return target in self.bridge_protocols(bridge)

    def bridge_has_sflow(self, bridge: str) -> bool:
        """Check bridge sFlow attachment."""

        if not self.bridge_exists(bridge):
            return False
        result = run_ovs_vsctl(["get", "bridge", bridge, "sflow"], timeout=5)
        if result.returncode != 0:
            return False
        return result.stdout.strip() not in {"[]", ""}

    def any_controller_connected(self) -> bool:
        """Check OVS controller connectivity."""

        result = run_ovs_vsctl(["show"], timeout=5)
        return result.returncode == 0 and "is_connected: true" in result.stdout

    def attach_sflow(self, bridge: str) -> bool:
        """Attach sFlow collector to bridge."""

        if not self.bridge_exists(bridge):
            return False
        result = run_ovs_vsctl(
            [
                "--",
                "--id=@sflow",
                "create",
                "sflow",
                f"agent={self.agent_interface}",
                f'target="{self.collector_target}"',
                f"sampling={self.sampling}",
                f"polling={self.polling}",
                "--",
                "set",
                "bridge",
                bridge,
                "sflow=@sflow",
            ],
            timeout=10,
        )
        return result.returncode == 0

    @staticmethod
    def _is_table_miss_flow(line: str) -> bool:
        """Return whether dumped flow line is default packet-in rule."""

        compact = " ".join(line.split())
        return "priority=0" in compact and "actions=CONTROLLER:65535" in compact

    def forwarding_programmed(self, bridge: str) -> bool:
        """Check whether bridge has forwarding rules beyond table-miss."""

        dump = self.dump_flows(bridge)
        if not dump:
            return False
        flow_lines = [
            line.strip()
            for line in dump.splitlines()
            if line.strip() and not line.startswith("NXST_FLOW")
        ]
        return any(not self._is_table_miss_flow(line) for line in flow_lines)

    def ovs_state(self) -> OVSState:
        """Return structured OVS state."""

        bridges = [
            OVSBridgeState(
                name=bridge,
                interfaces=self.list_interfaces(bridge),
                controller_connected=self.any_controller_connected(),
                sflow_attached=self.bridge_has_sflow(bridge),
                protocols=self.bridge_protocols(bridge),
                forwarding_programmed=self.forwarding_programmed(bridge),
            )
            for bridge in self.list_bridges()
        ]
        return OVSState(
            installed=self.is_installed(),
            service_running=self.service_running(),
            bridges=bridges,
            detail=(
                "ovs-vswitchd running"
                if self.service_running()
                else "ovs-vswitchd not running"
            ),
        )

    def install_drop_flow(self, bridge: str, flow: str) -> bool:
        """Insert drop rule into bridge."""

        if not self.bridge_exists(bridge):
            return False
        return run_ovs_ofctl(["add-flow", bridge, flow], timeout=10).returncode == 0

    def install_normal_flow(self, bridge: str, priority: int = 0) -> bool:
        """Insert baseline NORMAL forwarding rule using expected OpenFlow version."""

        if not self.bridge_exists(bridge):
            return False
        flow = f"table=0,priority={priority},actions=NORMAL"
        args = ["-O", self.expected_protocol, "add-flow", bridge, flow]
        return run_ovs_ofctl(args, timeout=10).returncode == 0

    def dump_flows(self, bridge: str) -> str:
        """Dump bridge flows."""

        if not self.bridge_exists(bridge):
            return ""
        result = run_ovs_ofctl(
            ["-O", self.expected_protocol, "dump-flows", bridge], timeout=10
        )
        return result.stdout if result.returncode == 0 else ""

    def has_flow(self, bridge: str, match_fields: dict[str, str]) -> bool:
        """Check dumped flow contains expected fields."""

        dump = self.dump_flows(bridge)
        if not dump:
            return False
        return all(
            f"{key}={value}" in dump or value in dump
            for key, value in match_fields.items()
        )

    def start(self) -> None:
        """Validate base OVS readiness."""

        if not self.is_installed():
            raise RuntimeError("Labhost container not running.")
        if not self.service_running():
            raise RuntimeError("Open vSwitch service not running.")

    def stop(self) -> None:
        """No-op for containerized OVS lifecycle."""

    def status(self) -> dict[str, Any]:
        """Return OVS status."""

        payload = self.ovs_state().to_dict()
        payload["expected_protocol"] = self.expected_protocol
        payload["ready"] = payload["installed"] and payload["service_running"]
        payload["protocol_ready"] = any(
            self.expected_protocol in item.get("protocols", [])
            for item in payload.get("bridges", [])
        )
        payload["forwarding_programmed"] = any(
            item.get("forwarding_programmed", False)
            for item in payload.get("bridges", [])
        )
        return payload
