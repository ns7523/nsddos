"""UI API client. API-only access."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from typing import Any

import httpx

from nsddos.api.app import create_app
from nsddos.runtime.domain.base import RuntimeRecord
from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.performance import record_timing


class UiApiClient:
    """Deterministic API client for UI surfaces."""

    def __init__(self) -> None:
        self._app = create_app()

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        start = monotonic()
        try:
            response = self._request_with_timeout(path, params or {})
            response.raise_for_status()
            payload = response.json()
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised through UI route fallback behavior
            duration_ms = (monotonic() - start) * 1000
            record_timing(f"ui.api.{path}", duration_ms)
            return {
                "payload": self._fallback_payload(path, exc),
                "duration_ms": duration_ms,
            }
        duration_ms = (monotonic() - start) * 1000
        record_timing(f"ui.api.{path}", duration_ms)
        typed_items = []
        for index, item in enumerate(payload.get("items", [])):
            typed_items.append(
                RuntimeRecord(
                    record_id=str(
                        item.get(
                            "id", deterministic_id("ui-item", f"{path}:{index}:{item}")
                        )
                    ),
                    record_type=str(item.get("type", path)),
                    payload=item,
                ).to_dict()
            )
        payload["items"] = typed_items
        return {"payload": payload, "duration_ms": duration_ms}

    def _request_with_timeout(
        self, path: str, params: dict[str, Any], timeout_seconds: float = 0.2
    ) -> httpx.Response:
        """Run API request with bounded wall-clock timeout."""

        result_queue: Queue[tuple[bool, httpx.Response | Exception]] = Queue(maxsize=1)

        def _runner() -> None:
            try:
                result_queue.put((True, asyncio.run(self._request(path, params))))
            except Exception as exc:  # pragma: no cover - worker failure path
                result_queue.put((False, exc))

        worker = Thread(target=_runner, daemon=True)
        worker.start()
        try:
            ok, payload = result_queue.get(timeout=timeout_seconds)
        except Empty as exc:
            raise TimeoutError(f"ui api timeout for {path}") from exc
        if ok:
            return payload  # type: ignore[return-value]
        raise payload  # type: ignore[misc]

    async def _request(self, path: str, params: dict[str, Any]) -> httpx.Response:
        transport = httpx.ASGITransport(app=self._app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://nsddos.local"
        ) as client:
            return await client.get(path, params=params)

    def _fallback_payload(self, path: str, exc: Exception) -> dict[str, Any]:
        """Return safe fallback payload when live API call stalls or fails."""

        timestamp = datetime.now(timezone.utc).isoformat()
        detail = str(exc) or "unavailable"
        base = {
            "items": [],
            "total": 0,
            "replay_safe": True,
            "timestamp": timestamp,
            "detail": detail,
        }
        fallbacks: dict[str, dict[str, Any]] = {
            "/runtime/detection": {
                "attack_detected": False,
                "attack_type": "unknown",
                "confidence": 0.0,
                "risk_level": "low",
                "evidence_hash": "ui-fallback",
                "classification_generation": "ui-fallback",
                "detail": detail,
                "timestamp": timestamp,
            },
            "/runtime/mitigation": {
                "mitigation_required": False,
                "mitigation_action": "alert_only",
                "target_ip": "",
                "execution_result": "unavailable",
                "mitigation_hash": "ui-fallback",
                "mitigation_generation": "ui-fallback",
                "detail": detail,
                "timestamp": timestamp,
            },
            "/runtime/ml/infer": {
                "attack_probability": 0.0,
                "predicted_attack_type": "unknown",
                "confidence_score": 0.0,
                "anomaly_score": 0.0,
                "drift_score": 0.0,
                "model_version": "unavailable",
                "retraining_required": False,
                "detail": detail,
                "timestamp": timestamp,
            },
            "/runtime/live-telemetry": {
                "provider_source": "ui-fallback",
                "packet_rate": 0.0,
                "byte_rate": 0.0,
                "active_flows": 0,
                "health_state": "degraded",
                "controller_status": "unavailable",
                "detail": detail,
                "timestamp": timestamp,
            },
            "/health": {
                "status": "degraded",
                "checks": {},
                "detail": detail,
                "timestamp": timestamp,
            },
            "/runtime/provider-health": base,
            "/runtime/policy/diagnostics": base,
            "/runtime/service": base,
            "/dashboard/report": {
                "reports": [],
                "detail": detail,
                "timestamp": timestamp,
            },
            "/dashboard/diagnostics": {
                "diagnostics": {"ui_fallback": detail},
                "timestamp": timestamp,
            },
            "/runtime/verification": base,
            "/runtime/convergence": base,
            "/runtime/graph": base,
            "/runtime/timeline": base,
            "/runtime/evidence": base,
            "/runtime/replay": base,
            "/runtime/drift": base,
        }
        return dict(fallbacks.get(path, base))
