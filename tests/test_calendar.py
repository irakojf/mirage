"""Tests for mirage_core calendar slotting, buffering, and enforcement."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from mirage_core.calendar import (
    apply_buffer,
    detect_conflicts,
    filter_calendar_fit,
    find_slot,
    protect_morning,
    require_slot,
    safe_get_availability,
    safe_get_week_overview,
    task_fits_calendar,
)
from mirage_core.config import MirageConfig
from mirage_core.errors import SlottingError
from mirage_core.models import (
    Availability,
    AvailabilityQuery,
    AvailabilityReport,
    AvailabilityWindow,
    Task,
    TaskId,
    TaskStatus,
    WeekOverview,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _window(start: str, end: str) -> AvailabilityWindow:
    return AvailabilityWindow(
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
    )


def _task(task_id: str = "t1", minutes: int | None = None) -> Task:
    return Task(
        id=TaskId(task_id),
        name="Test task",
        status=TaskStatus.TASKS,
        complete_time_minutes=minutes,
    )


def _availability(*windows: AvailabilityWindow) -> Availability:
    return Availability(windows=list(windows))


# ---------------------------------------------------------------------------
# apply_buffer
# ---------------------------------------------------------------------------

def test_apply_buffer_trims_windows():
    windows = [_window("2026-02-02T09:00:00", "2026-02-02T12:00:00")]
    buffered = apply_buffer(windows, 15)
    assert buffered[0].start == datetime.fromisoformat("2026-02-02T09:15:00")
    assert buffered[0].end == datetime.fromisoformat("2026-02-02T11:45:00")


def test_apply_buffer_drops_small_windows():
    windows = [_window("2026-02-02T09:00:00", "2026-02-02T10:00:00")]
    result = apply_buffer(windows, buffer_minutes=30)
    assert len(result) == 0


def test_apply_buffer_zero_is_noop():
    windows = [
        _window("2026-02-02T09:00:00", "2026-02-02T12:00:00"),
        _window("2026-02-02T13:00:00", "2026-02-02T15:00:00"),
    ]
    result = apply_buffer(windows, buffer_minutes=0)
    assert len(result) == 2
    assert result[0].start == datetime.fromisoformat("2026-02-02T09:00:00")


def test_apply_buffer_negative_is_noop():
    windows = [_window("2026-02-02T09:00:00", "2026-02-02T12:00:00")]
    result = apply_buffer(windows, buffer_minutes=-5)
    assert len(result) == 1


def test_apply_buffer_multiple_windows():
    windows = [
        _window("2026-02-02T09:00:00", "2026-02-02T11:00:00"),
        _window("2026-02-02T13:00:00", "2026-02-02T17:00:00"),
    ]
    result = apply_buffer(windows, buffer_minutes=15)
    assert len(result) == 2
    assert result[0].duration_minutes == 90  # 120 - 30
    assert result[1].duration_minutes == 210  # 240 - 30


# ---------------------------------------------------------------------------
# protect_morning
# ---------------------------------------------------------------------------

def test_protect_morning_splits_window():
    windows = [_window("2026-02-02T08:00:00", "2026-02-02T11:00:00")]
    morning, remaining = protect_morning(
        windows, protection_end="10:00", date=datetime(2026, 2, 2)
    )
    assert morning is not None
    assert morning.end == datetime.fromisoformat("2026-02-02T10:00:00")
    assert remaining[0].start == datetime.fromisoformat("2026-02-02T10:00:00")


def test_protect_morning_window_before_cutoff():
    windows = [_window("2026-02-02T08:00:00", "2026-02-02T09:00:00")]
    morning, remaining = protect_morning(
        windows, protection_end="10:00", date=datetime(2026, 2, 2)
    )
    assert morning is not None
    assert morning.end == datetime.fromisoformat("2026-02-02T09:00:00")
    assert len(remaining) == 0


def test_protect_morning_window_after_cutoff():
    windows = [_window("2026-02-02T11:00:00", "2026-02-02T14:00:00")]
    morning, remaining = protect_morning(
        windows, protection_end="10:00", date=datetime(2026, 2, 2)
    )
    assert morning is None
    assert len(remaining) == 1


def test_protect_morning_multiple_windows():
    windows = [
        _window("2026-02-02T08:00:00", "2026-02-02T09:00:00"),
        _window("2026-02-02T10:00:00", "2026-02-02T12:00:00"),
        _window("2026-02-02T13:00:00", "2026-02-02T15:00:00"),
    ]
    morning, remaining = protect_morning(
        windows, protection_end="10:00", date=datetime(2026, 2, 2)
    )
    assert morning is not None
    assert morning.start == datetime.fromisoformat("2026-02-02T08:00:00")
    assert len(remaining) == 2


# ---------------------------------------------------------------------------
# task_fits_calendar
# ---------------------------------------------------------------------------

def test_task_fits_calendar_with_buffer():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00")
    )
    task = _task("t1", 45)
    assert task_fits_calendar(task, availability, buffer_minutes=5)
    assert not task_fits_calendar(task, availability, buffer_minutes=10)


def test_task_fits_exact():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00")
    )
    task = _task("t1", 60)
    assert task_fits_calendar(task, availability) is True


def test_task_no_estimate_always_fits():
    availability = _availability()  # empty
    task = _task("t1", None)
    assert task_fits_calendar(task, availability) is True


def test_task_does_not_fit():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00")
    )
    task = _task("t1", 90)
    assert task_fits_calendar(task, availability) is False


# ---------------------------------------------------------------------------
# find_slot
# ---------------------------------------------------------------------------

def test_find_slot_first_fit():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00"),
        _window("2026-02-02T13:00:00", "2026-02-02T16:00:00"),
    )
    task = _task("t1", 120)
    slot = find_slot(task, availability)
    assert slot is not None
    assert slot.start == datetime.fromisoformat("2026-02-02T13:00:00")


def test_find_slot_returns_none_when_too_small():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T09:30:00")
    )
    task = _task("t1", 45)
    assert find_slot(task, availability) is None


def test_find_slot_no_estimate_returns_largest():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00"),
        _window("2026-02-02T13:00:00", "2026-02-02T17:00:00"),
    )
    task = _task("t1", None)
    slot = find_slot(task, availability)
    assert slot is not None
    assert slot.duration_minutes == 240


def test_find_slot_empty_availability_no_estimate():
    availability = _availability()
    task = _task("t1", None)
    assert find_slot(task, availability) is None


# ---------------------------------------------------------------------------
# require_slot
# ---------------------------------------------------------------------------

def test_require_slot_success():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T12:00:00")
    )
    task = _task("t1", 60)
    slot = require_slot(task, availability)
    assert slot.duration_minutes >= 60


def test_require_slot_raises_when_no_fit():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T09:30:00")
    )
    task = _task("t1", 45)
    with pytest.raises(SlottingError):
        require_slot(task, availability)


# ---------------------------------------------------------------------------
# detect_conflicts
# ---------------------------------------------------------------------------

def test_detect_conflicts_all_fit():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T17:00:00")
    )
    tasks = [_task("t1", 60), _task("t2", 60)]
    conflicts = detect_conflicts(tasks, availability)
    assert len(conflicts) == 0


def test_detect_conflicts_marks_unplaceable_tasks():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00")
    )
    tasks = [_task("t1", 30), _task("t2", 45)]
    conflicts = detect_conflicts(tasks, availability)
    assert [t.id.value for t in conflicts] == ["t2"]


def test_detect_conflicts_no_estimate_skipped():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00")
    )
    tasks = [_task("t1", None), _task("t2", 60)]
    conflicts = detect_conflicts(tasks, availability)
    assert len(conflicts) == 0


def test_detect_conflicts_with_buffer():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T11:00:00")
    )
    tasks = [_task("t1", 60), _task("t2", 60)]
    conflicts = detect_conflicts(tasks, availability, buffer_minutes=15)
    assert len(conflicts) == 1


# ---------------------------------------------------------------------------
# filter_calendar_fit
# ---------------------------------------------------------------------------

def test_filter_calendar_fit_partitions():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T11:00:00")
    )
    tasks = [_task("t1", 60), _task("t2", 180), _task("t3", None)]
    fits, no_fit = filter_calendar_fit(tasks, availability)
    assert len(fits) == 2  # t1 fits, t3 has no estimate
    assert len(no_fit) == 1
    assert no_fit[0].id.value == "t2"


def test_filter_calendar_fit_all_fit():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T17:00:00")
    )
    tasks = [_task("t1", 60), _task("t2", 60)]
    fits, no_fit = filter_calendar_fit(tasks, availability)
    assert len(fits) == 2
    assert len(no_fit) == 0


def test_filter_calendar_fit_none_fit():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00")
    )
    tasks = [_task("t1", 120), _task("t2", 180)]
    fits, no_fit = filter_calendar_fit(tasks, availability)
    assert len(fits) == 0
    assert len(no_fit) == 2


def test_filter_calendar_fit_with_buffer():
    availability = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T11:00:00")  # 120 - 30 = 90
    )
    tasks = [_task("t1", 90), _task("t2", 100)]
    fits, no_fit = filter_calendar_fit(tasks, availability, buffer_minutes=15)
    assert len(fits) == 1
    assert len(no_fit) == 1


# ---------------------------------------------------------------------------
# safe_get_availability
# ---------------------------------------------------------------------------

def test_safe_get_availability_success():
    async def _run():
        mock_port = AsyncMock()
        mock_port.get_availability.return_value = AvailabilityReport(
            date="2026-02-02",
            total_free_minutes=180,
            total_free_hours=3.0,
            windows=[_window("2026-02-02T09:00:00", "2026-02-02T12:00:00")],
        )
        query = AvailabilityQuery(date="2026-02-02")
        result = await safe_get_availability(mock_port, query)
        assert result is not None
        assert len(result.windows) == 1

    asyncio.run(_run())


def test_safe_get_availability_error_returns_none():
    async def _run():
        mock_port = AsyncMock()
        mock_port.get_availability.side_effect = Exception("API down")
        query = AvailabilityQuery(date="2026-02-02")
        result = await safe_get_availability(mock_port, query)
        assert result is None

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# safe_get_week_overview
# ---------------------------------------------------------------------------

def test_safe_get_week_overview_success():
    async def _run():
        mock_port = AsyncMock()
        mock_port.get_week_overview.return_value = WeekOverview(
            week_start="2026-02-02",
            total_free_hours=20.0,
            days=[],
        )
        result = await safe_get_week_overview(mock_port, None)
        assert result is not None
        assert result.total_free_hours == 20.0

    asyncio.run(_run())


def test_safe_get_week_overview_error_returns_none():
    async def _run():
        mock_port = AsyncMock()
        mock_port.get_week_overview.side_effect = Exception("API down")
        result = await safe_get_week_overview(mock_port, None)
        assert result is None

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------

def test_config_calendar_defaults():
    cfg = MirageConfig()
    assert cfg.timezone == "America/Los_Angeles"
    assert cfg.buffer_minutes == 15
    assert cfg.morning_protection_end == "10:00"
    assert cfg.work_start == "09:00"
    assert cfg.work_end == "18:00"


# ---------------------------------------------------------------------------
# AvailabilityWindow model
# ---------------------------------------------------------------------------

def test_window_duration():
    w = _window("2026-02-02T09:00:00", "2026-02-02T12:00:00")
    assert w.duration_minutes == 180


def test_window_fits():
    w = _window("2026-02-02T09:00:00", "2026-02-02T10:00:00")
    assert w.fits(60) is True
    assert w.fits(61) is False


def test_window_invalid_raises():
    with pytest.raises(Exception):
        AvailabilityWindow(
            start=datetime.fromisoformat("2026-02-02T12:00:00"),
            end=datetime.fromisoformat("2026-02-02T09:00:00"),
        )


# ---------------------------------------------------------------------------
# Availability model
# ---------------------------------------------------------------------------

def test_availability_total_free():
    avail = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T11:00:00"),
        _window("2026-02-02T13:00:00", "2026-02-02T15:00:00"),
    )
    assert avail.total_free_minutes == 240


def test_availability_is_empty():
    assert _availability().is_empty is True
    assert _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00")
    ).is_empty is False


def test_availability_find_slot():
    avail = _availability(
        _window("2026-02-02T09:00:00", "2026-02-02T10:00:00"),
        _window("2026-02-02T13:00:00", "2026-02-02T16:00:00"),
    )
    assert avail.find_slot(120) is not None
    assert avail.find_slot(200) is None
