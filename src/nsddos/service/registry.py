"""Service registry."""

from __future__ import annotations

from nsddos.service.sessions import list_sessions


def service_registry() -> dict:
    sessions = list_sessions()
    return {
        "session_ids": [item.session_id for item in sessions],
        "owners": sorted({item.owner for item in sessions}),
        "active": [item.session_id for item in sessions if item.state == "active"],
    }
