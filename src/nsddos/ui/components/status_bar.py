"""UI status bar."""

from __future__ import annotations


def render_status_bar(summary: dict) -> str:
    parts = " | ".join(f"{key}={value}" for key, value in summary.items())
    return f"<section><code>{parts}</code></section><hr>"
