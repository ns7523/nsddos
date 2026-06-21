"""Mininet provider runtime helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import os
import signal
import socket
import subprocess
from pathlib import Path
from shutil import which
from typing import Any

from loguru import logger

from nsddos.config import load_runtime_state, write_runtime_state
from nsddos.constants import DEFAULT_FLOODLIGHT_OF_PORT, LOG_DIR, MININET_BIN
from nsddos.providers.base import BaseProvider
from nsddos.providers.docker_helper import helper_exec, helper_running
from nsddos.runtime.models import TopologyMetadata

HOST_IPS = {
    "h1": "10.0.0.1",
    "h2": "10.0.0.2",
    "h3": "10.0.0.3",
}


class MininetProvider(BaseProvider):
    """Mininet provider for local topology lifecycle."""

    def __init__(
        self,
        mininet_bin: Path = MININET_BIN,
        controller_host: str = "127.0.0.1",
        controller_port: int = DEFAULT_FLOODLIGHT_OF_PORT,
        topology: str = "single,3",
    ) -> None:
        self.mininet_bin = mininet_bin
        self.controller_host = controller_host
        if helper_running() and self.controller_host == "127.0.0.1":
            self.controller_host = "floodlight"
        self.controller_port = controller_port
        self.topology = topology
        self.log_file = LOG_DIR / "mininet.log"

    @staticmethod
    def has_passwordless_sudo() -> bool:
        """Check if sudo can run non-interactively."""
        if which("sudo") is None:
            return False
        try:
            result = subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        return result.returncode == 0

    @staticmethod
    def is_root() -> bool:
        """Check current privilege level."""
        geteuid = getattr(os, "geteuid", None)
        return bool(geteuid and geteuid() == 0)

    def is_installed(self) -> bool:
        """Check Mininet binary availability."""
        if helper_running():
            return True
        return self.mininet_bin.exists() or which("mn") is not None

    def controller_reachable(self) -> bool:
        """Check remote controller TCP reachability."""
        if helper_running():
            result = helper_exec(
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
        try:
            with socket.create_connection(
                (self.controller_host, self.controller_port),
                timeout=3,
            ):
                return True
        except OSError:
            return False

    def _command_prefix(self) -> list[str]:
        """Return privilege prefix."""
        if self.is_root():
            return []
        if self.has_passwordless_sudo():
            return ["sudo", "-n"]
        raise RuntimeError("Mininet requires root or passwordless sudo.")

    def _binary(self) -> str:
        """Resolve Mininet binary."""
        if self.mininet_bin.exists():
            return str(self.mininet_bin)
        resolved = which("mn")
        if resolved:
            return resolved
        raise RuntimeError("Mininet binary not found.")

    def start(self) -> None:
        """Start simple Mininet topology."""
        if not self.is_installed():
            raise RuntimeError("Mininet not installed.")

        state = load_runtime_state()
        if state.topology_state == "running" and state.topology_pid:
            return

        if helper_running():
            cleanup = helper_exec(["sh", "-lc", "pkill -f labhost-mininet.py || true; mn -c"], timeout=30)
            logger.info("Mininet helper cleanup rc={}", cleanup.returncode)
            process = helper_exec(
                [
                    "sh",
                    "-lc",
                    (
                        "nohup python3 /usr/local/bin/labhost-mininet.py "
                        "{host} {port} {fanout} "
                        ">/var/log/mininet.log 2>&1 </dev/null &"
                    ).format(
                        host=self.controller_host,
                        port=self.controller_port,
                        fanout=self.topology.split(",")[-1],
                    ),
                ],
                detached=False,
                timeout=10,
            )
            if process.returncode != 0:
                raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "Mininet helper start failed.")
            state.topology_state = "running"
            state.topology_pid = None
            state.updated_at = datetime.now(timezone.utc).isoformat()
            state.last_error = None
            state.provider_status["mininet"] = self.status()
            write_runtime_state(state)
            return

        command = [
            *self._command_prefix(),
            self._binary(),
            f"--controller=remote,ip={self.controller_host},port={self.controller_port}",
            f"--topo={self.topology}",
            "--switch=ovsk",
        ]
        logger.info("Starting Mininet: {}", " ".join(command))
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = self.log_file.open("a", encoding="utf-8")
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
        state.topology_state = "running"
        state.topology_pid = process.pid
        state.updated_at = datetime.now(timezone.utc).isoformat()
        state.last_error = None
        state.provider_status["mininet"] = self.status()
        write_runtime_state(state)

    def stop(self) -> None:
        """Stop Mininet topology."""
        state = load_runtime_state()
        if helper_running():
            helper_exec(["sh", "-lc", "pkill -f labhost-mininet.py || true; mn -c"], timeout=30)
            state.topology_state = "stopped"
            state.topology_pid = None
            state.updated_at = datetime.now(timezone.utc).isoformat()
            state.provider_status["mininet"] = self.status()
            write_runtime_state(state)
            return
        if state.topology_pid:
            try:
                os.killpg(state.topology_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        if self.is_installed():
            cleanup = [*self._command_prefix(), self._binary(), "-c"]
            subprocess.run(cleanup, capture_output=True, text=True, check=False)
        state.topology_state = "stopped"
        state.topology_pid = None
        state.updated_at = datetime.now(timezone.utc).isoformat()
        state.provider_status["mininet"] = self.status()
        write_runtime_state(state)

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

    def probe_traffic_drop(self, source_host: str, destination_ip: str) -> dict[str, Any]:
        """Probe host connectivity and report whether traffic is blocked."""
        command = ["ip", "netns", "exec", source_host, "ping", "-c", "1", "-W", "1", destination_ip]
        if helper_running():
            attach = (
                "pid=$(ps -eo pid,args | awk '/mininet:"
                f"{source_host}"
                "$/ {print $1; exit}'); "
                "[ -n \"$pid\" ] || { echo missing_mininet_host >&2; exit 1; }; "
                f"mnexec -a \"$pid\" ping -c 1 -W 1 {destination_ip}"
            )
            result = helper_exec(["sh", "-lc", attach], timeout=10)
        else:
            result = subprocess.run(
                [*self._command_prefix(), *command],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        output = f"{result.stdout}\n{result.stderr}".strip()
        blocked = result.returncode != 0 or "100% packet loss" in output or "Destination Host Unreachable" in output
        return {
            "attempted": True,
            "blocked": blocked,
            "detail": output[-500:] or "no output",
            "source_host": source_host,
            "destination_ip": destination_ip,
        }

    def status(self) -> dict[str, Any]:
        """Return topology provider status."""
        state = load_runtime_state()
        running = False
        if helper_running():
            result = helper_exec(["pgrep", "-af", "labhost-mininet.py"], timeout=5)
            running = result.returncode == 0
        elif state.topology_pid:
            try:
                os.kill(state.topology_pid, 0)
                running = True
            except OSError:
                running = False
        controller_reachable = self.controller_reachable()
        return {
            "provider": "mininet",
            "installed": self.is_installed(),
            "requires_root": True,
            "passwordless_sudo": self.has_passwordless_sudo() or self.is_root(),
            "topology": self.topology,
            "controller": f"{self.controller_host}:{self.controller_port}",
            "controller_reachable": controller_reachable,
            "reachable": controller_reachable,
            "running": running,
            "pid": state.topology_pid,
            "topology_ready": running and controller_reachable,
            "ready": running and controller_reachable,
            "metadata": self.topology_metadata().to_dict(),
        }
