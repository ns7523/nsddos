"""Service state helpers."""

from __future__ import annotations

from nsddos.service.models import ServiceState
from nsddos.service.persistence import load_service_state, save_service_state


def get_service_state() -> ServiceState:
    return load_service_state()


def persist_service_state(state: ServiceState) -> ServiceState:
    save_service_state(state)
    return state
