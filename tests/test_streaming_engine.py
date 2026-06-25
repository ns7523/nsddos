from __future__ import annotations

from pathlib import Path

from nsddos.runtime.streaming.aggregation import aggregate_events
from nsddos.runtime.streaming.backpressure import evaluate_backpressure
from nsddos.runtime.streaming.buffer import build_buffer_state
from nsddos.runtime.streaming.checkpoint import latest_checkpoint
from nsddos.runtime.streaming.engine import process_stream_events
from nsddos.runtime.streaming.queue import build_queue_state
from nsddos.runtime.streaming.recovery import restore_checkpoint
from nsddos.runtime.streaming.validation import validate_stream_events
from nsddos.runtime.streaming.windowing import build_window_state


def _config() -> dict:
    return {
        "runtime": {
            "streaming": {
                "enabled": True,
                "batch_size": 4,
                "max_queue_depth": 6,
                "max_buffer_size": 3,
                "window_seconds": 10,
                "window_kind": "sliding",
                "checkpoint_every_events": 2,
                "overflow_policy": "drop_oldest",
            }
        }
    }


def _manual_events():
    from datetime import datetime, timezone

    from nsddos.runtime.streaming.contracts import StreamEvent

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return (
        StreamEvent(
            "e3",
            "collection",
            3.0,
            300.0,
            3.0,
            "tcp",
            "10.0.0.3",
            "10.0.0.1",
            base.replace(second=3),
            3,
            "valid",
        ),
        StreamEvent(
            "e1",
            "collection",
            1.0,
            100.0,
            1.0,
            "udp",
            "10.0.0.1",
            "10.0.0.1",
            base.replace(second=1),
            1,
            "valid",
        ),
        StreamEvent(
            "e2",
            "collection",
            2.0,
            200.0,
            2.0,
            "udp",
            "10.0.0.2",
            "10.0.0.1",
            base.replace(second=2),
            2,
            "valid",
        ),
        StreamEvent(
            "e4",
            "collection",
            4.0,
            400.0,
            4.0,
            "icmp",
            "10.0.0.4",
            "10.0.0.1",
            base.replace(second=4),
            4,
            "valid",
        ),
    )


def test_queue_ordering() -> None:
    queue = build_queue_state(_manual_events())
    assert [item.event_id for item in queue.events] == ["e1", "e2", "e3", "e4"]


def test_event_buffering() -> None:
    queue = build_queue_state(_manual_events())
    buffer_state = build_buffer_state(
        queue.events, max_size=3, overflow_policy="drop_oldest"
    )
    assert [item.event_id for item in buffer_state.events] == ["e2", "e3", "e4"]
    assert buffer_state.dropped_events == 1


def test_sliding_window_processing() -> None:
    buffer_state = build_buffer_state(
        build_queue_state(_manual_events()).events,
        max_size=4,
        overflow_policy="drop_oldest",
    )
    windows = build_window_state(
        buffer_state.events, window_kind="sliding", window_seconds=10
    )
    assert windows.window_kind == "sliding"
    assert windows.active_events == 4
    assert len(windows.windows[-1].events) == 4


def test_tumbling_window_processing() -> None:
    buffer_state = build_buffer_state(
        build_queue_state(_manual_events()).events,
        max_size=4,
        overflow_policy="drop_oldest",
    )
    windows = build_window_state(
        buffer_state.events, window_kind="tumbling", window_seconds=2
    )
    assert windows.window_kind == "tumbling"
    assert len(windows.windows) >= 2


def test_aggregation_correctness() -> None:
    buffer_state = build_buffer_state(
        build_queue_state(_manual_events()).events,
        max_size=4,
        overflow_policy="drop_oldest",
    )
    aggregation = aggregate_events(
        build_window_state(
            buffer_state.events, window_kind="sliding", window_seconds=10
        )
    )
    assert aggregation.total_packet_rate == 10.0
    assert aggregation.attack_pattern in {"udp_flood", "icmp_flood", "syn_flood"}


def test_backpressure_handling() -> None:
    queue = build_queue_state(_manual_events())
    buffer_state = build_buffer_state(
        queue.events, max_size=3, overflow_policy="drop_oldest"
    )
    state = evaluate_backpressure(queue, max_queue_depth=3, buffer_state=buffer_state)
    assert state.state == "overflow"
    assert state.throttled is True


def test_checkpoint_persistence(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.streaming import checkpoint as checkpoint_module
    from nsddos.runtime.streaming import engine as engine_module
    from nsddos.runtime.streaming import sessions as sessions_module

    monkeypatch.setattr(checkpoint_module, "CHECKPOINT_DIR", tmp_path / "checkpoints")
    monkeypatch.setattr(sessions_module, "SESSION_DIR", tmp_path / "sessions")
    monkeypatch.setattr(engine_module, "STREAMING_DIR", tmp_path / "streaming")
    evaluation = process_stream_events(_config(), events=_manual_events())
    assert evaluation.checkpoint.checkpoint_id
    assert latest_checkpoint()["checkpoint_id"] == evaluation.checkpoint.checkpoint_id


def test_recovery_restore(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.streaming import checkpoint as checkpoint_module
    from nsddos.runtime.streaming import engine as engine_module
    from nsddos.runtime.streaming import sessions as sessions_module

    monkeypatch.setattr(checkpoint_module, "CHECKPOINT_DIR", tmp_path / "checkpoints")
    monkeypatch.setattr(sessions_module, "SESSION_DIR", tmp_path / "sessions")
    monkeypatch.setattr(engine_module, "STREAMING_DIR", tmp_path / "streaming")
    process_stream_events(_config(), events=_manual_events())
    restored = restore_checkpoint()
    assert restored is not None
    assert restored.sequence_number >= 0


def test_duplicate_event_rejection() -> None:
    events = list(_manual_events())
    events[1] = events[0]
    errors = validate_stream_events(tuple(events))
    assert "duplicate_event_id" in errors


def test_dispatcher_trigger_correctness(tmp_path: Path, monkeypatch) -> None:
    from nsddos.runtime.streaming import checkpoint as checkpoint_module
    from nsddos.runtime.streaming import dispatcher as dispatcher_module
    from nsddos.runtime.streaming import engine as engine_module
    from nsddos.runtime.streaming import sessions as sessions_module

    monkeypatch.setattr(checkpoint_module, "CHECKPOINT_DIR", tmp_path / "checkpoints")
    monkeypatch.setattr(sessions_module, "SESSION_DIR", tmp_path / "sessions")
    monkeypatch.setattr(engine_module, "STREAMING_DIR", tmp_path / "streaming")
    monkeypatch.setattr(
        dispatcher_module,
        "evaluate_detection",
        lambda config, telemetry=None, reference_at=None: type(
            "Detection", (), {"to_dict": lambda self: {"attack_type": "udp_flood"}}
        )(),
    )
    monkeypatch.setattr(
        dispatcher_module,
        "evaluate_dynamic_policy",
        lambda config, detection=None, ml=None, telemetry=None, reference_at=None: type(
            "Policy",
            (),
            {
                "to_dict": lambda self: {
                    "recommended_action": "rate_limit",
                    "escalation_level": 1,
                }
            },
        )(),
    )
    monkeypatch.setattr(
        dispatcher_module,
        "evaluate_ml_detection",
        lambda config, detection=None, telemetry=None, reference_at=None: type(
            "ML",
            (),
            {
                "to_dict": lambda self: {
                    "attack_probability": 0.8,
                    "predicted_attack_type": "udp_flood",
                }
            },
        )(),
    )
    monkeypatch.setattr(
        dispatcher_module,
        "evaluate_mitigation",
        lambda config, detection=None, policy=None, telemetry=None, reference_at=None: type(
            "Mitigation",
            (),
            {"to_dict": lambda self: {"mitigation_action": "rate_limit"}},
        )(),
    )
    evaluation = process_stream_events(_config(), events=_manual_events())
    assert evaluation.detection_payload["attack_type"] == "udp_flood"
    assert evaluation.ml_payload["predicted_attack_type"] == "udp_flood"
    assert evaluation.policy_payload["recommended_action"] == "rate_limit"
    assert evaluation.mitigation_payload["mitigation_action"] == "rate_limit"
