"""Verification page renderer."""

from __future__ import annotations

from nsddos.ui.components.tables import render_items_table
from nsddos.ui.models import UiPagePayload


def render_verification_view(payload: UiPagePayload) -> str:
    return f"<h2>{payload.title}</h2><p>validator categories severity evidence refs</p>{render_items_table(payload.items)}"
