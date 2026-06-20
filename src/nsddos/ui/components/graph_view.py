"""Graph page renderer."""

from __future__ import annotations

from nsddos.ui.components.tables import render_items_table
from nsddos.ui.models import UiPagePayload


def render_graph_view(payload: UiPagePayload) -> str:
    return f"<h2>{payload.title}</h2><p>graph relationships replay-safe</p>{render_items_table(payload.items)}"
