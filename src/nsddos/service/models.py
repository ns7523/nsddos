"""Typed runtime service models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from nsddos.runtime.models import SCHEMA_VERSION

SessionState = Literal["created", "active", "synchronizing", "degraded", "replaying", "stopped", "failed"]
SessionLifecycle = Literal["startup", "steady", "syncing", "recovery", "shutdown"]


@dataclass(frozen=True)
class SessionCapabilities:
    daemon_support: bool = True
    replay_support: bool = True
    synchronization_support: bool = True
    degraded_runtime_support: bool = True
    streaming_support: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SessionReplayState:
    replay_safe: bool = True
    cursor: int = 0
    last_replay_at: str | None = None
    reconstructed_events: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SessionSynchronizationState:
    sync_state: str = "unknown"
    runtime_checksum: str = ""
    query_checksum: str = ""
    evidence_checksum: str = ""
    synchronized_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeSession:
    session_id: str
    owner: str
    state: SessionState = "created"
    lifecycle: SessionLifecycle = "startup"
    capabilities: SessionCapabilities = field(default_factory=SessionCapabilities)
    replay: SessionReplayState = field(default_factory=SessionReplayState)
    synchronization: SessionSynchronizationState = field(default_factory=SessionSynchronizationState)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeSession":
        return cls(
            session_id=str(payload.get("session_id", "")),
            owner=str(payload.get("owner", "unknown")),
            state=payload.get("state", "created"),
            lifecycle=payload.get("lifecycle", "startup"),
            capabilities=SessionCapabilities(**(payload.get("capabilities", {}) or {})),
            replay=SessionReplayState(**(payload.get("replay", {}) or {})),
            synchronization=SessionSynchronizationState(**(payload.get("synchronization", {}) or {})),
            created_at=str(payload.get("created_at", datetime.now(timezone.utc).isoformat())),
            updated_at=str(payload.get("updated_at", datetime.now(timezone.utc).isoformat())),
            metadata=payload.get("metadata", {}) or {},
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = self.capabilities.to_dict()
        payload["replay"] = self.replay.to_dict()
        payload["synchronization"] = self.synchronization.to_dict()
        return payload


@dataclass
class ServiceEvent:
    sequence: int
    event_type: str
    status: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ServiceHeartbeat:
    heartbeat_id: str
    service_state: str
    session_count: int
    synchronization_state: str
    replay_state: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ServiceState:
    schema_version: str = SCHEMA_VERSION
    service_id: str = "nsddos-runtime-service"
    state: str = "stopped"
    owner: str = ""
    active_session_id: str | None = None
    startup_count: int = 0
    degraded: bool = False
    lock_owner: str | None = None
    replay_safe: bool = True
    last_error: str | None = None
    started_at: str | None = None
    updated_at: str | None = None
    performance: dict[str, float] = field(default_factory=dict)
    streaming: dict[str, Any] = field(default_factory=dict)
    synchronization: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ServiceState":
        return cls(
            schema_version=str(payload.get("schema_version", SCHEMA_VERSION)),
            service_id=str(payload.get("service_id", "nsddos-runtime-service")),
            state=str(payload.get("state", "stopped")),
            owner=str(payload.get("owner", "")),
            active_session_id=payload.get("active_session_id"),
            startup_count=int(payload.get("startup_count", 0)),
            degraded=bool(payload.get("degraded", False)),
            lock_owner=payload.get("lock_owner"),
            replay_safe=bool(payload.get("replay_safe", True)),
            last_error=payload.get("last_error"),
            started_at=payload.get("started_at"),
            updated_at=payload.get("updated_at"),
            performance=payload.get("performance", {}) or {},
            streaming=payload.get("streaming", {}) or {},
            synchronization=payload.get("synchronization", {}) or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
