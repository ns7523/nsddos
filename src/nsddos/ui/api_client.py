"""UI API client. API-only access."""

from __future__ import annotations

from time import monotonic
from typing import Any

from fastapi.testclient import TestClient

from nsddos.api.app import create_app
from nsddos.runtime.domain.base import RuntimeRecord
from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.performance import record_timing


class UiApiClient:
    """Deterministic API client for UI surfaces."""

    def __init__(self) -> None:
        self._client = TestClient(create_app())

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        start = monotonic()
        response = self._client.get(path, params=params or {})
        response.raise_for_status()
        duration_ms = (monotonic() - start) * 1000
        record_timing(f"ui.api.{path}", duration_ms)
        payload = response.json()
        typed_items = []
        for index, item in enumerate(payload.get("items", [])):
            typed_items.append(
                RuntimeRecord(
                    record_id=str(item.get("id", deterministic_id("ui-item", f"{path}:{index}:{item}"))),
                    record_type=str(item.get("type", path)),
                    payload=item,
                ).to_dict()
            )
        payload["items"] = typed_items
        return {"payload": payload, "duration_ms": duration_ms}
