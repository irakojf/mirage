from __future__ import annotations

from datetime import datetime

import pytest

from mirage_core.calendar import (
    apply_buffer,
    detect_conflicts,
    find_slot,
    protect_morning,
    require_slot,
    task_fits_calendar,
)
from mirage_core.errors import SlottingError
from mirage_core.models import Availability, AvailabilityWindow, Task, TaskId, TaskStatus


def _window(start: str, end: str) -> AvailabilityWindow:
    return AvailabilityWindow(
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
    )


def _task(task_id: str, minutes: int | None) -> Task:
    return Task(
        id=TaskId(task_id),
        name="Test task",
        status=TaskStatus.TASKS,
        complete_time_minutes=minutes,
    )


def test_apply_buffer_trims_windows():
    windows = [_window("2026-02-02T09:00:00", "2026-02-02T12:00:00")]
    buffered = apply_buffer(windows, 15)
    assert buffered[0].start == datetime.fromisoformat("2026-02-02T09:15:00")
    assert buffered[0].end == datetime.fromisoformat("2026-02-02T11:45:00")


def test_protect_morning_splits_window():
    windows = [_window("2026-02-02T08:00:00", "2026-02-02T11:00:00")]
    morning, remaining = protect_morning(
        windows, protection_end="10:00", date=datetime(2026, 2, 2)
    )
    assert morning is not None
    assert morning.end == datetime.fromisoformat("2026-02-02T10:00:00")
    assert remaining[0].start == datetime.fromisoformat("2026-02-02T10:00:00")


def test_task_fits_calendar_with_buffer():
    availability = Availability(
        windows=[_window("2026-02-02T09:00:00", "2026-02-02T10:00:00")]
    )
    task = _task("t1", 45)
    assert task_fits_calendar(task, availability, buffer_minutes=5)
    assert not task_fits_calendar(task, availability, buffer_minutes=10)


def test_find_slot_returns_none_when_too_small():
    availability = Availability(
        windows=[_window("2026-02-02T09:00:00", "2026-02-02T09:30:00")]
    )
    task = _task("t1", 45)
    assert find_slot(task, availability) is None


def test_require_slot_raises_when_no_fit():
    availability = Availability(
        windows=[_window("2026-02-02T09:00:00", "2026-02-02T09:30:00")]
    )
    task = _task("t1", 45)
    with pytest.raises(SlottingError):
        require_slot(task, availability)


def test_detect_conflicts_marks_unplaceable_tasks():
    availability = Availability(
        windows=[_window("2026-02-02T09:00:00", "2026-02-02T10:00:00")]
    )
    tasks = [_task("t1", 30), _task("t2", 45)]
    conflicts = detect_conflicts(tasks, availability)
    assert [t.id.value for t in conflicts] == ["t2"]
