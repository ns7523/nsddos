"""Rich terminal helpers for onboarding."""

from __future__ import annotations

from rich.align import Align
from rich.box import ROUNDED
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from nsddos.bootstrap.diagnostics import DiagnosticItem, QuickCommand

from . import theme


def create_console(record: bool = False) -> Console:
    """Create onboarding console."""

    return Console(record=record)


def threat_text(level: str) -> Text:
    """Build styled threat label."""

    normalized = level.upper()
    palette = {
        "LOW": theme.SUCCESS,
        "MODERATE": theme.WARNING,
        "MEDIUM": theme.WARNING,
        "HIGH": theme.DANGER,
        "CRITICAL": theme.DANGER,
    }
    color = palette.get(normalized, theme.ACCENT)
    return Text.assemble(
        (f"{theme.GLYPH_THREAT} ", color),
        (normalized, f"bold {color}"),
    )


def status_text(status: str) -> Text:
    """Build styled status badge text."""

    palette = {
        theme.STATUS_OK: theme.SUCCESS,
        theme.STATUS_WARN: theme.WARNING,
        theme.STATUS_MISSING: theme.DANGER,
        theme.STATUS_PENDING: theme.ACCENT_SOFT,
        theme.STATUS_ACTIVE: theme.ACCENT_ALT,
    }
    color = palette.get(status, theme.TEXT)
    glyph = {
        theme.STATUS_OK: theme.GLYPH_OK,
        theme.STATUS_WARN: theme.GLYPH_WARN,
        theme.STATUS_MISSING: theme.GLYPH_MISSING,
        theme.STATUS_PENDING: theme.GLYPH_PENDING,
        theme.STATUS_ACTIVE: theme.GLYPH_ACTIVE,
    }.get(status, theme.GLYPH_WARN)
    return Text.assemble((f"{glyph} ", color), (status, f"bold {color}"))


def build_environment_table(items: list[DiagnosticItem]) -> Table:
    """Build environment summary table."""

    table = Table(expand=True, box=None, pad_edge=False)
    table.add_column("Check", style=f"bold {theme.TEXT}")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style=theme.MUTED)
    for item in items:
        table.add_row(item.label, status_text(item.status), item.detail)
    return table


def build_operator_table(
    title: str,
    columns: tuple[str, ...],
    rows: list[tuple[RenderableType, ...]] | tuple[tuple[RenderableType, ...], ...],
) -> Panel:
    """Build premium operator table."""

    table = Table(expand=True, box=None, pad_edge=False)
    for index, column in enumerate(columns):
        style = f"bold {theme.ACCENT}" if index == 0 else theme.TEXT
        if index > 1:
            style = theme.MUTED
        table.add_column(column, style=style)
    for row in rows:
        table.add_row(*row)
    return Panel(
        table,
        title=title,
        border_style=theme.SECTION_BORDER_STYLE,
        padding=(1, 2),
        box=ROUNDED,
    )


def build_quick_commands_table(commands: list[QuickCommand]) -> Table:
    """Build quick commands table."""

    table = Table(expand=True, box=None, pad_edge=False)
    table.add_column("Command", style=f"bold {theme.ACCENT}")
    table.add_column("Purpose", style=theme.MUTED)
    for command in commands:
        table.add_row(f"{theme.GLYPH_COMMAND} {command.name}", command.description)
    return table


def build_readiness_progress(completed: int, total: int) -> Progress:
    """Build static readiness progress."""

    progress = Progress(
        TextColumn("[bold white]Foundation[/bold white]"),
        BarColumn(
            bar_width=None, complete_style=theme.ACCENT, finished_style=theme.ACCENT
        ),
        TextColumn("[bold cyan]{task.completed}/{task.total}[/bold cyan]"),
        expand=True,
    )
    progress.add_task("readiness", total=total, completed=completed)
    return progress


def build_operator_header(eyebrow: str, title: str, subtitle: str) -> Panel:
    """Build shared operator header."""

    copy = Text(justify="center")
    copy.append(f"{eyebrow}\n", style=f"bold {theme.ACCENT_ALT}")
    copy.append(f"{title}\n", style=f"bold {theme.TEXT_SOFT}")
    copy.append(subtitle, style=theme.MUTED)
    return Panel(
        Align.center(copy),
        border_style=theme.HERO_BORDER_STYLE,
        padding=(1, 4),
        box=ROUNDED,
    )


def build_operator_chips(items: tuple[tuple[str, str], ...]) -> Columns:
    """Build small status chips."""

    chips: list[Panel] = []
    for label, value in items:
        body = Text()
        body.append(f"{label}\n", style=f"bold {theme.ACCENT}")
        body.append(value, style=theme.TEXT)
        chips.append(
            Panel(
                body,
                border_style=theme.GRID_STYLE,
                box=ROUNDED,
                padding=(0, 1),
            )
        )
    return Columns(chips, expand=True, equal=True)


def build_scene_frame(lines: tuple[str, ...], footer: str | None = None) -> Panel:
    """Build centered ASCII scene frame."""

    art = Text(justify="center")
    for line in lines:
        art.append(f"{line}\n", style=theme.ACCENT)
    if footer:
        art.append(f"\n{footer}", style=theme.MUTED)
    return Panel(
        Align.center(art),
        title=f"{theme.APP_DISPLAY_NAME} {theme.APP_DISPLAY_VERSION}",
        subtitle=theme.APP_DISPLAY_SUBTITLE,
        border_style=theme.HERO_BORDER_STYLE,
        padding=(1, 3),
        box=ROUNDED,
    )


def build_command_deck(commands: list[QuickCommand]) -> Panel:
    """Build command deck panel."""

    rows = [
        (f"{theme.GLYPH_COMMAND} {command.name}", command.description)
        for command in commands
    ]
    return build_operator_table(
        "Command Deck",
        ("Command", "Purpose"),
        rows,
    )


def build_status_matrix(title: str, items: tuple[tuple[str, str, str], ...]) -> Panel:
    """Build status matrix panel."""

    rows = [(label, status_text(status), detail) for label, status, detail in items]
    return build_operator_table(title, ("System", "State", "Detail"), rows)


def section_panel(title: str, renderable: RenderableType) -> Panel:
    """Wrap section in themed panel."""

    return Panel(
        renderable,
        title=title,
        border_style=theme.SECTION_BORDER_STYLE,
        padding=(1, 2),
        box=ROUNDED,
    )


def build_operator_screen(
    header: RenderableType,
    primary: RenderableType,
    secondary: RenderableType,
    footer: RenderableType | None = None,
) -> RenderableType:
    """Build full-screen operator layout."""

    layout = Layout()
    layout.split_column(
        Layout(header, name="header", size=7),
        Layout(name="body"),
        Layout(footer or Rule(style=theme.GRID_STYLE), name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(primary, name="primary", ratio=7),
        Layout(secondary, name="secondary", ratio=5),
    )
    return layout


def build_footer_line(message: str) -> RenderableType:
    """Build footer line."""

    return Group(
        Rule(style=theme.GRID_STYLE),
        Align.center(Text(message, style=theme.MUTED)),
    )
