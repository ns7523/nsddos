"""Runtime repair helpers."""

from __future__ import annotations

from nsddos.config import (
    ensure_default_config,
    ensure_runtime_directories,
    ensure_runtime_state,
)


def repair_runtime_state() -> tuple[str, ...]:
    """Reinitialize runtime state and directories."""

    ensure_runtime_directories()
    ensure_default_config()
    ensure_runtime_state()
    return ("runtime_dirs", "config", "state")
