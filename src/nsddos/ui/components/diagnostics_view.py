"""Diagnostics page renderer."""

from __future__ import annotations

from nsddos.ui.components.tables import render_items_table
from nsddos.ui.models import UiPagePayload


def render_diagnostics_view(payload: UiPagePayload) -> str:
    return f"<h2>{payload.title}</h2><p>runtime sync verification degraded replay diagnostics</p>{render_items_table(payload.items)}"
