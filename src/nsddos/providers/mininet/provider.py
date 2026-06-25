"""Mininet provider runtime helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from nsddos.config import load_runtime_state, write_runtime_state
from nsddos.constants import DEFAULT_FLOODLIGHT_OF_PORT, LOG_DIR, MININET_BIN
from nsddos.providers.base import BaseProvider
from nsddos.runtime.executor import RuntimeExecutor
from nsddos.runtime.models import TopologyMetadata

HOST_IPS = {
    "h1": "10.0.0.1",
    "h2": "10.0.0.2",
    "h3": "10.0.0.3",
}


class MininetProvider(BaseProvider):
    """Mininet provider for labhost topology lifecycle."""

    def __init__(
        self,
        mininet_bin: Path = MININET_BIN,
        controller_host: str = "127.0.0.1",
        controller_port: int = DEFAULT_FLOODLIGHT_OF_PORT,
        topology: str = "single,3",
        ovs_protocol: str = "OpenFlow13",
    ) -> None:
        self.mininet_bin = mininet_bin
        self.executor = RuntimeExecutor()
        self.controller_host = (
            "floodlight" if controller_host == "127.0.0.1" else controller_host
        )
        self.controller_port = controller_port
        self.topology = topology
        self.ovs_protocol = ovs_protocol
        self.log_file = LOG_DIR / "mininet.log"

    @staticmethod
    def has_passwordless_sudo() -> bool:
        """Legacy compatibility shim."""

        return False

    @staticmethod
    def is_root() -> bool:
        """Legacy compatibility shim."""

        return False

    def is_installed(self) -> bool:
        """Check Mininet availability through labhost container."""

        return self.executor.lab_container_running()

    def _ensure_lab_runtime(self) -> None:
        """Raise when labhost runtime unavailable."""

        if not self.executor.lab_container_running():
            raise RuntimeError("Labhost container not running.")

    def _namespace_attach(self, host: str, command: str) -> list[str]:
        """Return mnexec attach command for Mininet host namespace."""

        attach = (
            "pid=$(ps -eo pid,args | awk '/mininet:"
            f"{host}"
            "$/ {print $1; exit}'); "
            '[ -n "$pid" ] || { echo missing_mininet_host >&2; exit 1; }; '
            'mnexec -a "$pid" sh -lc '
            f"'{command}'"
        )
        return ["sh", "-lc", attach]

    def controller_reachable(self) -> bool:
        """Check remote controller TCP reachability from labhost."""

        if not self.is_installed():
            return False
        result = self.executor.execute_lab(
            [
                "python3",
                "-c",
                (
                    "import socket; "
                    "sock=socket.create_connection(('{}', {}), 3); "
                    "sock.close()"
                ).format(self.controller_host, self.controller_port),
            ],
            timeout=5,
        )
        return result.returncode == 0

    def start(self) -> None:
        """Start simple Mininet topology in labhost container."""

        self._ensure_lab_runtime()
        state = load_runtime_state()
        if state.topology_state == "running":
            return
        cleanup_kill = self.executor.execute_lab(
            ["sh", "-lc", "pkill -f '[l]abhost-mininet.py' || true"], timeout=10
        )
        cleanup = self.executor.execute_lab(["sh", "-lc", "mn -c"], timeout=30)
        logger.info(
            "Mininet helper cleanup kill_rc={} cleanup_rc={}",
            cleanup_kill.returncode,
            cleanup.returncode,
        )
        process = self.executor.execute_lab(
            [
                "sh",
                "-lc",
                (
                    "nohup python3 /usr/local/bin/labhost-mininet.py "
                    "{host} {port} {fanout} {protocol} "
                    ">/var/log/mininet.log 2>&1 </dev/null &"
                ).format(
                    host=self.controller_host,
                    port=self.controller_port,
                    fanout=self.topology.split(",")[-1],
                    protocol=self.ovs_protocol,
                ),
            ],
            timeout=10,
        )
        if process.returncode != 0:
            raise RuntimeError(
                process.stderr.strip()
                or process.stdout.strip()
                or "Mininet helper start failed."
            )
        state.topology_state = "running"
        state.topology_pid = None
        state.updated_at = datetime.now(timezone.utc).isoformat()
        state.last_error = None
        state.provider_status["mininet"] = self.status()
        write_runtime_state(state)

    def stop(self) -> None:
        """Stop Mininet topology in labhost container."""

        state = load_runtime_state()
        if self.executor.lab_container_running():
            self.executor.execute_lab(
                ["sh", "-lc", "pkill -f '[l]abhost-mininet.py' || true"], timeout=10
            )
            self.executor.execute_lab(["sh", "-lc", "mn -c"], timeout=30)
        state.topology_state = "stopped"
        state.topology_pid = None
        state.updated_at = datetime.now(timezone.utc).isoformat()
        state.provider_status["mininet"] = self.status()
        write_runtime_state(state)

    def pingall_test(self) -> dict[str, Any]:
        """Run one-shot Mininet pingall test inside labhost."""

        self._ensure_lab_runtime()
        result = self.executor.execute_lab(
            [
                "mn",
                f"--controller=remote,ip={self.controller_host},port={self.controller_port}",
                f"--topo={self.topology}",
                f"--switch=ovsk,protocols={self.ovs_protocol}",
                "--test",
                "pingall",
            ],
            timeout=90,
        )
        output = f"{result.stdout}\n{result.stderr}".strip()
        return {
            "ok": result.returncode == 0 and "0% dropped" in output,
            "detail": output[-500:] or "no output",
        }

    def topology_metadata(self) -> TopologyMetadata:
        """Return fixed topology metadata."""

        switches = ["s1"]
        hosts = ["h1", "h2", "h3"]
        links = ["s1-h1", "s1-h2", "s1-h3"]
        return TopologyMetadata(
            topology=self.topology,
            switches=switches,
            hosts=hosts,
            links=links,
            controller=f"{self.controller_host}:{self.controller_port}",
            controller_reachable=self.controller_reachable(),
            switch_count=len(switches),
        )

    def probe_traffic_drop(
        self, source_host: str, destination_ip: str
    ) -> dict[str, Any]:
        """Probe host connectivity and report whether traffic is blocked."""

        self._ensure_lab_runtime()
        result = self.executor.execute_lab(
            self._namespace_attach(source_host, f"ping -c 1 -W 1 {destination_ip}"),
            timeout=10,
        )
        output = f"{result.stdout}\n{result.stderr}".strip()
        blocked = (
            result.returncode != 0
            or "100% packet loss" in output
            or "Destination Host Unreachable" in output
        )
        return {
            "attempted": True,
            "blocked": blocked,
            "detail": output[-500:] or "no output",
            "source_host": source_host,
            "destination_ip": destination_ip,
        }

    def probe_connectivity(
        self, source_host: str, destination_ip: str
    ) -> dict[str, Any]:
        """Probe host connectivity and report whether traffic reaches destination."""

        probe = self.probe_traffic_drop(source_host, destination_ip)
        return {
            "attempted": probe["attempted"],
            "reachable": not probe["blocked"],
            "detail": probe["detail"],
            "source_host": source_host,
            "destination_ip": destination_ip,
        }

    def status(self) -> dict[str, Any]:
        """Return topology provider status."""

        state = load_runtime_state()
        running = False
        detail = "labhost unavailable"
        if self.executor.lab_container_running():
            result = self.executor.execute_lab(
                ["pgrep", "-af", "labhost-mininet.py"], timeout=5
            )
            running = result.returncode == 0
            detail = (result.stdout or result.stderr or "").strip() or (
                "running" if running else "stopped"
            )
        controller_reachable = self.controller_reachable()
        return {
            "provider": "mininet",
            "installed": self.is_installed(),
            "requires_root": False,
            "passwordless_sudo": False,
            "topology": self.topology,
            "controller": f"{self.controller_host}:{self.controller_port}",
            "controller_reachable": controller_reachable,
            "reachable": controller_reachable,
            "running": running,
            "pid": None,
            "detail": detail,
            "topology_ready": running and controller_reachable,
            "ready": running and controller_reachable,
            "metadata": self.topology_metadata().to_dict(),
            "state": state.topology_state,
        }
