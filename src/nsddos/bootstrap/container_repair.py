"""Container repair helpers."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from nsddos.bootstrap.stack import detect_compose_backend, start_stack


def repair_containers(console: Console) -> bool:
    """Rebuild/restart compose stack."""

    backend = detect_compose_backend()
    if backend is None:
        console.print(Panel("Compose backend unavailable.", title="Container Repair", border_style="red"))
        return False
    result = start_stack(backend, rebuild=True)
    if result.returncode != 0:
        console.print(
            Panel(
                result.stderr or result.stdout or "Compose repair failed.",
                title="Container Repair",
                border_style="red",
            )
        )
        return False
    return True
