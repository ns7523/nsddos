"""Reset execution engine."""

from __future__ import annotations

import shutil

from rich.console import Console

from nsddos.bootstrap.questions import confirm_install
from nsddos.bootstrap.runtime_repair import repair_runtime_state
from nsddos.bootstrap.stack import detect_compose_backend, run_compose_command
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.bootstrap.state import ResetResult
from nsddos.constants import CONFIG_PATH, LOG_DIR, RUNTIME_DIR


def execute_reset(console: Console) -> ResetResult:
    """Reset runtime state while preserving config."""

    if not confirm_install(console, "Reset NSDDOS runtime state?"):
        return ResetResult((), (), str(CONFIG_PATH), False)

    stopped_services: tuple[str, ...] = ()
    backend = detect_compose_backend()
    if backend is not None:
        services = run_compose_command(backend, ("ps", "--format", "json"))
        down = run_compose_command(backend, ("down", "-v"))
        if down.returncode == 0 and services.returncode == 0:
            stopped_services = DEFAULT_STARTUP_PROFILE.container_names

    deleted: list[str] = []
    for path in (RUNTIME_DIR, LOG_DIR):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            deleted.append(str(path))
    session_path = DEFAULT_STARTUP_PROFILE.session_path
    if session_path.exists():
        session_path.unlink()
        deleted.append(str(session_path))
    repair_runtime_state()
    return ResetResult(
        stopped_services=stopped_services,
        deleted_paths=tuple(deleted),
        preserved_config_path=str(CONFIG_PATH),
        success=True,
    )
