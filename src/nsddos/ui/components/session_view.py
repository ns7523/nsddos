"""Session page renderer."""

from __future__ import annotations

from nsddos.ui.components.tables import render_items_table
from nsddos.ui.models import UiPagePayload


def render_session_view(payload: UiPagePayload) -> str:
    return f"<h2>{payload.title}</h2><p>ownership heartbeat sync replay state</p>{render_items_table(payload.items)}"
