"""UI state manager."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.ui.models import UiState


def build_ui_state() -> UiState:
    return UiState(
        refresh_metadata={
            "poll_interval_seconds": 5,
            "deterministic_ordering": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
