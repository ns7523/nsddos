"""Deterministic internal event streaming foundation."""

from __future__ import annotations

from nsddos.service.events import append_service_event, load_service_events
from nsddos.service.models import ServiceEvent


class ServiceStream:
    """Replay-safe ordered event stream."""

    def __init__(self) -> None:
        self._sequence = 0
        existing = load_service_events()
        if existing:
            self._sequence = max(int(item.get("sequence", 0)) for item in existing)

    def emit(
        self,
        event_type: str,
        status: str,
        message: str,
        session_id: str | None = None,
        details: dict | None = None,
    ) -> ServiceEvent:
        self._sequence += 1
        event = ServiceEvent(
            sequence=self._sequence,
            event_type=event_type,
            status=status,
            message=message,
            session_id=session_id,
            details=details or {},
        )
        append_service_event(event)
        return event

    def replay(self, from_sequence: int = 0) -> list[dict]:
        return [item for item in load_service_events() if int(item.get("sequence", 0)) >= from_sequence]
