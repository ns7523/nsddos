"""CLI-facing startup orchestration entrypoint."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from nsddos.bootstrap.orchestrator import orchestrate_startup
from nsddos.bootstrap.startup_profiles import DEFAULT_STARTUP_PROFILE
from nsddos.bootstrap.state import StartupResult
from nsddos.bootstrap.terminal import create_console
from . import theme

STARTUP_STEPS = (
    ("environment", "ENV", "checking environment"),
    ("compose", "COMPOSE", "detecting compose backend"),
    ("stack", "STACK", "starting container stack"),
    ("services", "SERVICES", "waiting for service health"),
    ("runtime", "RUNTIME", "validating runtime"),
    ("ui", "UI", "launching operator console"),
)

BOOT_BANNER = (
    "███╗   ██╗███████╗██████╗ ██████╗  ██████╗ ███████╗",
    "████╗  ██║██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔════╝",
    "██╔██╗ ██║███████╗██║  ██║██║  ██║██║   ██║███████╗",
    "██║╚██╗██║╚════██║██║  ██║██║  ██║██║   ██║╚════██║",
    "██║ ╚████║███████║██████╔╝██████╔╝╚██████╔╝███████║",
    "╚═╝  ╚═══╝╚══════╝╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝",
)


@dataclass
class StartupDisplayState:
    """In-memory startup display state."""

    ui_url: str = DEFAULT_STARTUP_PROFILE.ui_url
    active_step: str = "environment"
    failed_checks: tuple[str, ...] = ()
    completed: set[str] = field(default_factory=set)
    boot_started_at: float = 0.0
    boot_lines: list[str] = field(default_factory=list)
    current_detail: str = "boot sequence started"


def _format_uptime(started_at: float) -> str:
    elapsed = max(int(time.monotonic() - started_at), 0)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _level(state: StartupDisplayState) -> str:
    if state.failed_checks:
        return "CRITICAL"
    if state.active_step in {"stack", "services", "runtime"}:
        return "ELEVATED"
    return "LOW"


def _system_state(state: StartupDisplayState) -> str:
    if state.failed_checks:
        return "OFFLINE"
    if "ui" in state.completed:
        return "ONLINE"
    return "BOOTING"


def _append_line(state: StartupDisplayState, channel: str, message: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    state.boot_lines.append(f"[{stamp}] {channel:<10} {message}")
    state.boot_lines = state.boot_lines[-18:]


def _status_line(state: StartupDisplayState) -> Text:
    text = Text()
    fields = (
        ("SYSTEM", _system_state(state)),
        ("THREAT", _level(state)),
        ("UPTIME", _format_uptime(state.boot_started_at)),
        ("UI", state.ui_url.replace("http://", "")),
    )
    for index, (label, value) in enumerate(fields):
        if index:
            text.append("  ")
        text.append(f"{label}: ", style=f"bold {theme.SUCCESS}")
        color = theme.DANGER if value in {"OFFLINE", "CRITICAL"} else theme.WARNING if value in {"BOOTING", "ELEVATED"} else theme.SUCCESS
        text.append(value, style=f"bold {color}")
    return text


def _service_table(state: StartupDisplayState) -> Table:
    table = Table(expand=True, box=None, pad_edge=False, show_header=True)
    table.add_column("SERVICE", style=f"bold {theme.SUCCESS}")
    table.add_column("STATE", width=12)
    table.add_column("DETAIL", style=theme.MUTED)
    for key, label, default_detail in STARTUP_STEPS:
        if key in state.failed_checks:
            status = "OFFLINE"
            color = theme.DANGER
        elif key in state.completed:
            status = "ONLINE"
            color = theme.SUCCESS
        elif key == state.active_step:
            status = "BOOTING"
            color = theme.WARNING
        else:
            status = "WAIT"
            color = theme.MUTED
        detail = state.current_detail if key == state.active_step else default_detail
        table.add_row(label, Text(status, style=f"bold {color}"), detail)
    return table


def _stage_matrix(state: StartupDisplayState) -> Table:
    table = Table(expand=True, box=None, pad_edge=False, show_header=False)
    table.add_column("stage")
    table.add_column("value")
    for key, label, _detail in STARTUP_STEPS:
        if key in state.failed_checks:
            status = Text("OFFLINE", style=f"bold {theme.DANGER}")
        elif key in state.completed:
            status = Text("ONLINE", style=f"bold {theme.SUCCESS}")
        elif key == state.active_step:
            status = Text("BOOTING", style=f"bold {theme.WARNING}")
        else:
            status = Text("WAIT", style=theme.MUTED)
        table.add_row(Text(label, style=f"bold {theme.MUTED}"), status)
    return table


def _boot_log(state: StartupDisplayState) -> Text:
    lines = state.boot_lines or ["[--:--:--] SYSTEM     boot sequence started"]
    log = Text()
    for index, line in enumerate(lines):
        if index:
            log.append("\n")
        if "FAILED" in line or "error" in line.lower():
            log.append(line, style=theme.DANGER)
        elif "BOOTING" in line or "launching" in line.lower():
            log.append(line, style=theme.WARNING)
        else:
            log.append(line, style=theme.SUCCESS)
    return log


def _startup_renderable(state: StartupDisplayState) -> RenderableType:
    banner = Text("\n".join(BOOT_BANNER), style=f"bold {theme.SUCCESS}")
    return Group(
        banner,
        Text("NSDDOS BOOT MONITOR", style=f"bold {theme.SUCCESS}"),
        Rule(style=theme.SUCCESS),
        Text("COMMAND CENTER STARTUP MATRIX", style=f"bold {theme.MUTED}"),
        _status_line(state),
        Text(""),
        _stage_matrix(state),
        Text(""),
        Text("BOOT LOG", style=f"bold {theme.MUTED}"),
        _boot_log(state),
        Text(""),
        Text("SERVICE BRING-UP", style=f"bold {theme.MUTED}"),
        _service_table(state),
    )


def _render_static(console: Console, state: StartupDisplayState) -> None:
    console.print(_startup_renderable(state))


def run_startup_command(console: Console | None = None) -> StartupResult:
    """Run one-command startup orchestration."""

    active_console = console or create_console()
    state = StartupDisplayState(boot_started_at=time.monotonic())
    _append_line(state, "SYSTEM", "boot sequence armed")

    def _on_status(step: str, status: str, detail: str) -> None:
        state.active_step = step
        state.current_detail = detail
        label = dict((key, short) for key, short, _detail in STARTUP_STEPS).get(step, step.upper())
        if status == "ok":
            state.completed.add(step)
            _append_line(state, label, f"ONLINE {detail}")
        elif status == "fail":
            state.failed_checks = (step,)
            _append_line(state, label, f"FAILED {detail}")
        else:
            _append_line(state, label, f"BOOTING {detail}")

    if active_console.is_terminal and not active_console.record:
        with Live(_startup_renderable(state), console=active_console, refresh_per_second=12, transient=False) as live:
            def _live_status(step: str, status: str, detail: str) -> None:
                _on_status(step, status, detail)
                live.update(_startup_renderable(state))

            result = orchestrate_startup(active_console, status_callback=_live_status)
            if not result.failed_checks:
                state.completed.add("ui")
                state.ui_url = result.ui_url
                _append_line(state, "SYSTEM", f"ONLINE ui available at {result.ui_url}")
            else:
                state.failed_checks = result.failed_checks
                _append_line(state, "SYSTEM", f"FAILED checks={','.join(result.failed_checks)}")
            live.update(_startup_renderable(state))
            return result

    result = orchestrate_startup(active_console, status_callback=_on_status)
    if not result.failed_checks:
        state.completed.add("ui")
        state.ui_url = result.ui_url
        _append_line(state, "SYSTEM", f"ONLINE ui available at {result.ui_url}")
    else:
        state.failed_checks = result.failed_checks
        _append_line(state, "SYSTEM", f"FAILED checks={','.join(result.failed_checks)}")
    _render_static(active_console, state)
    return result
