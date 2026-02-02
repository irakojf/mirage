"""Tests for mirage_core.telemetry error capture hooks."""

from mirage_core.telemetry import (
    ErrorEvent,
    capture_error,
    clear_handlers,
    register_handler,
)


def setup_function():
    clear_handlers()


def test_error_event_properties():
    event = ErrorEvent(
        error=ValueError("bad input"),
        source="notion_repo",
        operation="create_task",
    )
    assert event.error_type == "ValueError"
    assert event.message == "bad input"
    assert event.source == "notion_repo"
    assert event.operation == "create_task"


def test_error_event_to_dict():
    event = ErrorEvent(
        error=RuntimeError("timeout"),
        source="calendar",
        operation="get_free_time",
        context={"date": "2026-02-02"},
    )
    d = event.to_dict()
    assert d["error_type"] == "RuntimeError"
    assert d["message"] == "timeout"
    assert d["context"]["date"] == "2026-02-02"
    assert "timestamp" in d


def test_capture_error_returns_event():
    event = capture_error(
        ValueError("test"),
        source="test",
        operation="test_op",
    )
    assert isinstance(event, ErrorEvent)
    assert event.error_type == "ValueError"


def test_handler_receives_event():
    received = []
    register_handler(lambda e: received.append(e))

    capture_error(
        RuntimeError("fail"),
        source="slack",
        operation="capture",
    )

    assert len(received) == 1
    assert received[0].source == "slack"
    assert received[0].operation == "capture"


def test_multiple_handlers():
    counts = {"a": 0, "b": 0}
    register_handler(lambda e: counts.__setitem__("a", counts["a"] + 1))
    register_handler(lambda e: counts.__setitem__("b", counts["b"] + 1))

    capture_error(ValueError("x"), source="test", operation="op")

    assert counts["a"] == 1
    assert counts["b"] == 1


def test_handler_failure_does_not_crash():
    """A failing handler should not prevent other handlers or crash."""
    received = []

    def bad_handler(event):
        raise RuntimeError("handler crashed")

    register_handler(bad_handler)
    register_handler(lambda e: received.append(e))

    # Should not raise
    event = capture_error(ValueError("x"), source="test", operation="op")

    assert event is not None
    assert len(received) == 1


def test_clear_handlers():
    received = []
    register_handler(lambda e: received.append(e))
    clear_handlers()

    capture_error(ValueError("x"), source="test", operation="op")
    assert len(received) == 0


def test_context_passed_through():
    received = []
    register_handler(lambda e: received.append(e))

    capture_error(
        ValueError("x"),
        source="notion",
        operation="update_task",
        context={"task_id": "abc-123", "field": "status"},
    )

    assert received[0].context["task_id"] == "abc-123"
    assert received[0].context["field"] == "status"
