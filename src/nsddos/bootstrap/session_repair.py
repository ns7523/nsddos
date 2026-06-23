"""Session integrity repair helpers."""

from __future__ import annotations

from nsddos.bootstrap.orchestrator import build_startup_session, persist_startup_session
from nsddos.bootstrap.stack import detect_compose_backend, list_stack_services
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.bootstrap.ui_launcher import ui_reachable
from nsddos.bootstrap.state import StartupSession


def recreate_startup_session() -> StartupSession:
    """Recreate startup session from current state."""

    backend = detect_compose_backend()
    services = list_stack_services(backend) if backend is not None else ()
    running = tuple(service.container_name for service in services if service.container_name)
    health_state = "healthy" if ui_reachable(DEFAULT_STARTUP_PROFILE.ui_url) else "degraded"
    session = build_startup_session(running, health_state, DEFAULT_STARTUP_PROFILE.ui_url)
    persist_startup_session(session)
    return session
