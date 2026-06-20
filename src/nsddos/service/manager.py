"""Authoritative runtime service manager."""

from __future__ import annotations

from time import monotonic
from uuid import uuid4

from nsddos.config import load_runtime_state
from nsddos.runtime.performance import record_timing
from nsddos.runtime.query.engine import execute_query
from nsddos.runtime.query.models import RuntimeQuery, RuntimeQueryPagination
from nsddos.service.capabilities import detect_service_capabilities
from nsddos.service.diagnostics import collect_service_diagnostics
from nsddos.service.heartbeat import emit_heartbeat
from nsddos.service.lifecycle import mark_degraded, mark_started, mark_stopped
from nsddos.service.locks import acquire_lock, current_lock_owner, release_lock
from nsddos.service.models import ServiceState
from nsddos.service.persistence import load_service_state, save_service_state
from nsddos.service.recovery import recover_service_state
from nsddos.service.replay import replay_service_events
from nsddos.service.sessions import create_session, list_sessions, stop_session
from nsddos.service.streaming import ServiceStream
from nsddos.service.subscriptions import default_subscriptions
from nsddos.service.synchronization import synchronize_service
from nsddos.runtime.streaming import latest_checkpoint, latest_session


class RuntimeServiceManager:
    """Single authoritative runtime service coordinator."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.stream = ServiceStream()
        self.lock_token = f"lock-{uuid4()}"

    def start(self, owner: str = "cli") -> ServiceState:
        start = monotonic()
        state = load_service_state()
        if state.state == "running":
            return state
        lock = acquire_lock(owner, self.lock_token)
        session = create_session(owner=owner, metadata={"subscriptions": [item.to_dict() for item in default_subscriptions()]})
        mark_started(state, owner=owner, session_id=session.session_id, lock_owner=lock.owner)
        sync = synchronize_service(load_runtime_state().to_dict(), {"subscriptions": [item.to_dict() for item in default_subscriptions()]})
        state.synchronization = sync
        state.streaming = {"latest_sequence": 0, "subscriptions": [item.to_dict() for item in default_subscriptions()]}
        state.performance["service_startup_ms"] = (monotonic() - start) * 1000
        save_service_state(state)
        event = self.stream.emit("service.lifecycle", "started", "runtime service started", session_id=session.session_id)
        state.streaming["latest_sequence"] = event.sequence
        save_service_state(state)
        emit_heartbeat(state, synchronization_state=sync["state"], replay_state="fresh", detail="service-start")
        record_timing("service.start", (monotonic() - start) * 1000)
        return state

    def stop(self) -> ServiceState:
        start = monotonic()
        state = load_service_state()
        if state.active_session_id:
            stop_session(state.active_session_id, state="stopped")
        self.stream.emit("service.lifecycle", "stopped", "runtime service stopped", session_id=state.active_session_id)
        release_lock(state.owner, self.lock_token)
        mark_stopped(state)
        state.performance["service_stop_ms"] = (monotonic() - start) * 1000
        save_service_state(state)
        emit_heartbeat(state, synchronization_state="stopped", replay_state="stopped", detail="service-stop")
        return state

    def status(self) -> dict:
        state = load_service_state()
        diagnostics = collect_service_diagnostics()
        return {
            "state": state.to_dict(),
            "diagnostics": diagnostics,
            "lock_owner": current_lock_owner(),
            "streaming": {
                "session": latest_session(),
                "checkpoint": latest_checkpoint(),
            },
        }

    def synchronize(self) -> dict:
        start = monotonic()
        state = load_service_state()
        sync = synchronize_service(load_runtime_state().to_dict(), {"service_state": state.to_dict()})
        state.synchronization = sync
        state.performance["service_sync_ms"] = (monotonic() - start) * 1000
        save_service_state(state)
        self.stream.emit("service.sync", "synchronized", "service state synchronized", session_id=state.active_session_id, details=sync)
        emit_heartbeat(state, synchronization_state=sync["state"], replay_state="fresh", detail="service-sync")
        return sync

    def sessions(self) -> list[dict]:
        return [item.to_dict() for item in list_sessions()]

    def replay(self, from_sequence: int = 0) -> dict:
        start = monotonic()
        result = replay_service_events(from_sequence)
        record_timing("service.replay", (monotonic() - start) * 1000)
        return result

    def explain(self) -> dict:
        state = load_service_state()
        session_query = execute_query(
            self.config,
            RuntimeQuery(name="verification", scope="verification", pagination=RuntimeQueryPagination(limit=10)),
        )
        return {
            "service": state.to_dict(),
            "capabilities": detect_service_capabilities(self.config),
            "subscriptions": [item.to_dict() for item in default_subscriptions()],
            "query_backed_verification": session_query.plan,
            "recovery": recover_service_state(),
            "streaming": {
                "session": latest_session(),
                "checkpoint": latest_checkpoint(),
            },
        }

    def diagnostics(self) -> dict:
        return collect_service_diagnostics()

    def degrade(self, reason: str) -> ServiceState:
        state = load_service_state()
        mark_degraded(state, reason)
        save_service_state(state)
        self.stream.emit("service.degraded", "degraded", "service degraded", session_id=state.active_session_id, details={"reason": reason})
        return state
