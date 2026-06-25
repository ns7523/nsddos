"""LAB CONSOLE control surface helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
import pty
import subprocess
import threading
from typing import Any

from fastapi import WebSocket, WebSocketException
from fastapi import WebSocketDisconnect

from nsddos.config import load_config
from nsddos.providers.docker_helper import helper_running
from nsddos.providers.mininet.provider import HOST_IPS, MininetProvider
from nsddos.runtime.attack import latest_attack_report, run_live_attack_suite
from nsddos.runtime.attack import engine as attack_engine

LAB_HOSTS = ("h1", "h2", "h3")
ATTACK_ACTIONS = {
    "run-syn-flood": "syn_flood",
    "run-udp-flood": "udp_flood",
    "run-icmp-flood": "icmp_flood",
    "run-http-flood": "http_flood",
    "run-slowloris": "slowloris",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LabTerminalSession:
    """Persistent PTY-backed shell session for one Mininet host."""

    def __init__(self, host: str, command: list[str]) -> None:
        self.host = host
        self.command = command
        self.master_fd, self.slave_fd = pty.openpty()
        self.process = subprocess.Popen(
            command,
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            text=False,
            close_fds=True,
        )
        self._lock = threading.Lock()
        self._buffer = ""
        self._subscribers: list[
            tuple[asyncio.AbstractEventLoop, asyncio.Queue[str]]
        ] = []
        self._reader = threading.Thread(target=self._pump_output, daemon=True)
        self._reader.start()

    def _pump_output(self) -> None:
        try:
            while True:
                chunk = os.read(self.master_fd, 4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", "ignore")
                with self._lock:
                    self._buffer = (self._buffer + text)[-20000:]
                    subscribers = list(self._subscribers)
                for loop, queue in subscribers:
                    try:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
                    except RuntimeError:
                        continue
        except OSError:
            pass
        finally:
            self.close()

    def add_subscriber(
        self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[str]
    ) -> str:
        with self._lock:
            self._subscribers.append((loop, queue))
            return self._buffer

    def remove_subscriber(self, queue: asyncio.Queue[str]) -> None:
        with self._lock:
            self._subscribers = [
                item for item in self._subscribers if item[1] is not queue
            ]

    def write(self, data: str) -> None:
        if self.process.poll() is not None:
            raise RuntimeError(f"{self.host} shell is not running")
        os.write(self.master_fd, data.encode("utf-8"))

    def is_alive(self) -> bool:
        return self.process.poll() is None

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                self.process.terminate()
            except OSError:
                pass
        for fd in (self.master_fd, self.slave_fd):
            try:
                os.close(fd)
            except OSError:
                pass


class LabTerminalManager:
    """Manage persistent LAB terminal sessions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, LabTerminalSession] = {}

    def build_command(self, host: str) -> list[str]:
        if helper_running():
            return attack_engine._helper_host_command(host, "exec sh -i")
        prefix = attack_engine._namespace_runner(host)
        return [*prefix, "sh", "-lc", "exec sh -i"]

    def open_session(self, host: str) -> LabTerminalSession:
        if host not in LAB_HOSTS:
            raise ValueError(f"Unsupported LAB host: {host}")
        with self._lock:
            session = self._sessions.get(host)
            if session is not None and session.is_alive():
                return session
            session = LabTerminalSession(host, self.build_command(host))
            self._sessions[host] = session
            return session


class LabControlManager:
    """Dispatch LAB quick actions and track latest status."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._status = {
            "action": "idle",
            "state": "ready",
            "detail": "Awaiting operator command.",
            "timestamp": _now_iso(),
        }

    def latest_status(self) -> dict[str, str]:
        with self._lock:
            return dict(self._status)

    def _set_status(self, action: str, state: str, detail: str) -> dict[str, str]:
        status = {
            "action": action,
            "state": state,
            "detail": detail,
            "timestamp": _now_iso(),
        }
        with self._lock:
            self._status = status
        return status

    def _ping_all_hosts(self) -> dict[str, Any]:
        config = load_config()
        provider = MininetProvider(
            controller_port=config.get("lab", {}).get("controller_port", 6653),
            topology=config.get("lab", {}).get("mininet_topology", "single,3"),
        )
        results = []
        for source in LAB_HOSTS:
            for target, ip in HOST_IPS.items():
                if source == target:
                    continue
                probe = provider.probe_connectivity(source, ip)
                results.append(probe)
        reachable = sum(1 for item in results if item.get("reachable"))
        status = self._set_status(
            "ping-all-hosts",
            "completed",
            f"{reachable}/{len(results)} host probes reachable.",
        )
        return {**status, "results": results}

    def _run_attack(self, action: str, attack_type: str) -> None:
        try:
            config = load_config()
            report = run_live_attack_suite(
                config,
                attack=attack_type,
                warmup=3,
                attack_seconds=12,
                cooldown=5,
                stop_event=self._stop_event,
            )
            scenarios = report.get("scenarios", [])
            detail = f"{attack_type} finished with {len(scenarios)} scenario."
            self._set_status(action, "completed", detail)
        except Exception as exc:
            self._set_status(action, "failed", str(exc))
        finally:
            with self._lock:
                self._active_thread = None
                self._stop_event = None

    def _start_attack(self, action: str, attack_type: str) -> dict[str, str]:
        with self._lock:
            if self._active_thread is not None and self._active_thread.is_alive():
                return dict(self._status)
            self._stop_event = threading.Event()
            self._active_thread = threading.Thread(
                target=self._run_attack, args=(action, attack_type), daemon=True
            )
            self._active_thread.start()
        return self._set_status(
            action, "started", f"{attack_type} launched in LAB runtime."
        )

    def _stop_attack(self) -> dict[str, Any]:
        with self._lock:
            stop_event = self._stop_event
            active = self._active_thread is not None and self._active_thread.is_alive()
        if active and stop_event is not None:
            stop_event.set()
            attack_engine.stop_active_attack("h1", "h2", 8081)
            status = self._set_status(
                "stop-attack", "stopping", "Active LAB attack stop requested."
            )
            return {**status, "report": latest_attack_report()}
        status = self._set_status("stop-attack", "idle", "No active LAB attack.")
        return {**status, "report": latest_attack_report()}

    def run_action(
        self, action: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        del payload
        if action == "ping-all-hosts":
            return self._ping_all_hosts()
        if action in ATTACK_ACTIONS:
            return self._start_attack(action, ATTACK_ACTIONS[action])
        if action == "stop-attack":
            return self._stop_attack()
        return self._set_status(
            action, "unsupported", f"Unsupported LAB action: {action}"
        )


async def stream_terminal(
    websocket: WebSocket, host: str, manager: LabTerminalManager
) -> None:
    if host not in LAB_HOSTS:
        raise WebSocketException(code=1008, reason="invalid host")
    session = manager.open_session(host)
    queue: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    snapshot = session.add_subscriber(loop, queue)
    await websocket.accept()
    if snapshot:
        await websocket.send_text(snapshot)

    async def sender() -> None:
        while True:
            chunk = await queue.get()
            await websocket.send_text(chunk)

    async def receiver() -> None:
        while True:
            payload = await websocket.receive_text()
            session.write(payload)

    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())
    try:
        done, pending = await asyncio.wait(
            {sender_task, receiver_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        for task in done:
            task.result()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        session.remove_subscriber(queue)
        sender_task.cancel()
        receiver_task.cancel()


terminal_manager = LabTerminalManager()
control_manager = LabControlManager()
