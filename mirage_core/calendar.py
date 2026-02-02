"""Calendar slotting: availability, buffering, and scheduling logic.

Pure functions that operate on domain models. No I/O — adapters provide
the actual calendar data via CalendarPort.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Sequence

from .config import MirageConfig
from .errors import SlottingError
from .models import Availability, AvailabilityWindow, Task

logger = logging.getLogger(__name__)


def apply_buffer(
    windows: Sequence[AvailabilityWindow],
    buffer_minutes: int,
) -> list[AvailabilityWindow]:
    """Shrink each window by buffer_minutes on both sides.

    If a window becomes too small after buffering, it's dropped.
    """
    if buffer_minutes <= 0:
        return list(windows)

    delta = timedelta(minutes=buffer_minutes)
    result = []
    for w in windows:
        new_start = w.start + delta
        new_end = w.end - delta
        if new_end > new_start:
            result.append(AvailabilityWindow(start=new_start, end=new_end))
    return result


def protect_morning(
    windows: Sequence[AvailabilityWindow],
    protection_end: str,
    date: datetime,
) -> tuple[Optional[AvailabilityWindow], list[AvailabilityWindow]]:
    """Split windows into a protected morning block and remaining.

    Args:
        windows: Free time windows for the day.
        protection_end: HH:MM string for when morning protection ends.
        date: The date (used to build the cutoff datetime).

    Returns:
        (morning_block, remaining_windows) — morning_block is the first
        window that starts before protection_end (reserved for top-priority
        task), remaining_windows are the rest.
    """
    hour, minute = map(int, protection_end.split(":"))
    cutoff = date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    morning_block = None
    remaining = []

    for w in windows:
        if morning_block is None and w.start < cutoff:
            # This window overlaps the morning — split if needed
            if w.end <= cutoff:
                morning_block = w
            else:
                morning_block = AvailabilityWindow(start=w.start, end=cutoff)
                remaining.append(AvailabilityWindow(start=cutoff, end=w.end))
        else:
            remaining.append(w)

    return morning_block, remaining


def task_fits_calendar(
    task: Task,
    availability: Availability,
    buffer_minutes: int = 0,
) -> bool:
    """Check if a task's estimated time fits in any available slot.

    Returns True if:
    - Task has no complete_time_minutes (we can't enforce without estimate)
    - A slot exists that fits the task after applying buffer
    """
    if task.complete_time_minutes is None:
        return True

    windows = apply_buffer(availability.windows, buffer_minutes)
    for w in windows:
        if w.fits(task.complete_time_minutes):
            return True
    return False


def find_slot(
    task: Task,
    availability: Availability,
    buffer_minutes: int = 0,
) -> Optional[AvailabilityWindow]:
    """Find the best slot for a task.

    Strategy: first-fit — returns the first window large enough.
    Returns None if no slot fits.
    """
    if task.complete_time_minutes is None:
        # No estimate — return the largest window
        windows = apply_buffer(availability.windows, buffer_minutes)
        if not windows:
            return None
        return max(windows, key=lambda w: w.duration_minutes)

    windows = apply_buffer(availability.windows, buffer_minutes)
    for w in windows:
        if w.fits(task.complete_time_minutes):
            return w
    return None


def require_slot(
    task: Task,
    availability: Availability,
    buffer_minutes: int = 0,
) -> AvailabilityWindow:
    """Return a slot or raise SlottingError if none fits."""
    slot = find_slot(task, availability, buffer_minutes)
    if slot is None:
        raise SlottingError("No available calendar slot fits the task")
    return slot


def detect_conflicts(
    tasks: Sequence[Task],
    availability: Availability,
    buffer_minutes: int = 0,
) -> list[Task]:
    """Return tasks that won't fit in today's remaining availability.

    Simulates first-fit allocation: as each task claims a slot,
    remaining availability shrinks.
    """
    windows = list(apply_buffer(availability.windows, buffer_minutes))
    conflicts = []

    for task in tasks:
        if task.complete_time_minutes is None:
            continue

        placed = False
        for i, w in enumerate(windows):
            if w.fits(task.complete_time_minutes):
                # Consume the slot: shrink the window
                new_start = w.start + timedelta(minutes=task.complete_time_minutes)
                if new_start < w.end:
                    windows[i] = AvailabilityWindow(start=new_start, end=w.end)
                else:
                    windows.pop(i)
                placed = True
                break

        if not placed:
            conflicts.append(task)

    return conflicts


def filter_calendar_fit(
    tasks: Sequence[Task],
    availability: Availability,
    buffer_minutes: int = 0,
) -> tuple[list[Task], list[Task]]:
    """Partition tasks into those that fit today's calendar and those that don't.

    Returns (fits, no_fit). Tasks without a time estimate are assumed to fit.
    """
    fits: list[Task] = []
    no_fit: list[Task] = []
    for task in tasks:
        if task_fits_calendar(task, availability, buffer_minutes):
            fits.append(task)
        else:
            no_fit.append(task)
    return fits, no_fit


async def safe_get_availability(
    calendar_port,
    query,
) -> Optional[Availability]:
    """Fetch availability with graceful fallback on error.

    Returns None if the calendar API is unavailable, letting callers
    proceed without calendar enforcement.
    """
    try:
        report = await calendar_port.get_availability(query)
        return Availability(windows=list(report.windows), date=report.date)
    except Exception:
        logger.warning("Calendar unavailable, skipping calendar enforcement", exc_info=True)
        return None


async def safe_get_week_overview(
    calendar_port,
    query,
):
    """Fetch week overview with graceful fallback.

    Returns None if the calendar API is unavailable.
    """
    try:
        return await calendar_port.get_week_overview(query)
    except Exception:
        logger.warning("Calendar unavailable for week overview", exc_info=True)
        return None
