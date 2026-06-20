"""Evidence page renderer."""

from __future__ import annotations

from nsddos.ui.components.tables import render_items_table
from nsddos.ui.models import UiPagePayload


def render_evidence_view(payload: UiPagePayload) -> str:
    return f"<h2>{payload.title}</h2><p>lineage verification replay convergence snapshots</p>{render_items_table(payload.items)}"
