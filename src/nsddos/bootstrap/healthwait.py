"""Wait for compose stack health."""

from __future__ import annotations

import time
from collections.abc import Callable

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from nsddos.bootstrap.stack import list_stack_services
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.bootstrap.state import ComposeBackend, StackHealthWaitResult


def wait_for_stack_health(
    console: Console,
    backend: ComposeBackend,
    timeout_seconds: int = DEFAULT_STARTUP_PROFILE.health_timeout_seconds,
    poll_interval_seconds: int = DEFAULT_STARTUP_PROFILE.health_poll_interval_seconds,
    *,
    render_progress: bool = True,
    status_callback: Callable[[str, str, str], None] | None = None,
) -> StackHealthWaitResult:
    """Wait until required containers become healthy."""

    progress = None
    task_id = None
    if render_progress:
        progress = Progress(
            SpinnerColumn(style="bright_cyan"),
            TextColumn("[bold white]Waiting for services[/bold white]"),
            BarColumn(
                bar_width=28, complete_style="bright_cyan", finished_style="bright_cyan"
            ),
            TextColumn(
                "[bright_black]{task.completed:.0f}s/{task.total:.0f}s[/bright_black]"
            ),
            TextColumn("[bright_cyan]{task.fields[pending]}[/bright_cyan]"),
            console=console,
        )
        task_id = progress.add_task(
            "healthwait", total=timeout_seconds, completed=0, pending="starting"
        )
        console.print(progress)

    deadline = time.monotonic() + timeout_seconds
    latest_services = ()
    while time.monotonic() < deadline:
        latest_services = list_stack_services(backend)
        pending = tuple(
            name
            for name in DEFAULT_STARTUP_PROFILE.container_names
            if not any(
                service.container_name == name and service.healthy
                for service in latest_services
            )
        )
        elapsed = max(timeout_seconds - max(deadline - time.monotonic(), 0), 0)
        pending_text = ", ".join(pending) if pending else "healthy"
        if progress is not None and task_id is not None:
            progress.update(
                task_id,
                completed=min(elapsed, timeout_seconds),
                pending=pending_text,
            )
        if status_callback is not None:
            status_callback("services", "pending" if pending else "ok", pending_text)
        if not pending:
            return StackHealthWaitResult(
                services=latest_services,
                success=True,
                timed_out=False,
                pending_services=(),
            )
        time.sleep(poll_interval_seconds)
    pending = tuple(
        name
        for name in DEFAULT_STARTUP_PROFILE.container_names
        if not any(
            service.container_name == name and service.healthy
            for service in latest_services
        )
    )
    return StackHealthWaitResult(
        services=latest_services,
        success=False,
        timed_out=True,
        pending_services=pending,
    )
