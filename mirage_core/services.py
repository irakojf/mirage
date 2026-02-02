"""Pure business logic services orchestrating domain models and ports."""

from __future__ import annotations

from typing import Optional, Sequence

from .aliases import resolve_status, resolve_type
from .calendar import filter_calendar_fit, safe_get_availability
from .config import MirageConfig
from .models import (
    Availability,
    AvailabilityQuery,
    Task,
    TaskDraft,
    TaskId,
    TaskStatus,
    TaskType,
)
from .ports import CalendarPort, ReviewRepository, TaskRepository

PROCRASTINATION_THRESHOLD = 3


def flag_procrastinating(tasks: Sequence[Task]) -> list[Task]:
    """Return tasks that have been mentioned >= threshold times."""
    return [t for t in tasks if t.mentioned >= PROCRASTINATION_THRESHOLD]


def normalize_task_name(raw: str) -> str:
    """Clean raw capture into actionable task phrasing."""
    name = raw.strip()
    for prefix in ("- ", "* ", "• ", "→ "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return " ".join(name.split())


def sort_by_priority(tasks: Sequence[Task]) -> list[Task]:
    """Sort tasks: explicit priority first (ascending), then by mentioned desc."""

    def key(t: Task) -> tuple:
        has_priority = t.priority is not None
        priority_val = t.priority if t.priority is not None else 999
        return (not has_priority, priority_val, -t.mentioned)

    return sorted(tasks, key=key)


def filter_actionable(tasks: Sequence[Task]) -> list[Task]:
    """Return only tasks in Tasks status (single-sitting, clear next step)."""
    return [t for t in tasks if t.status == TaskStatus.TASKS]


class TaskCaptureService:
    """Handles task creation with dedup and mention-incrementing."""

    def __init__(self, repo: TaskRepository) -> None:
        self._repo = repo

    async def capture(
        self,
        content: str,
        status: str,
        *,
        blocked_by: Optional[str] = None,
        tag: Optional[str] = None,
        complete_time: Optional[int] = None,
    ) -> Task:
        """Create a new task, resolving aliases and setting defaults."""
        resolved = resolve_status(status)
        task_type = resolve_type(tag) if tag else None
        name = normalize_task_name(content)

        draft = TaskDraft(
            name=name,
            status=resolved,
            mentioned=1,
            blocked_by=blocked_by or None,
            task_type=task_type,
            complete_time_minutes=complete_time,
        )
        return await self._repo.create(draft)

    async def increment_mention(self, task_id: str) -> int:
        """Increment mention counter. Returns new count."""
        return await self._repo.increment_mentioned(TaskId(task_id))

    async def get_open_tasks(self) -> Sequence[Task]:
        """Return all non-done tasks for dedup matching."""
        return await self._repo.query(exclude_done=True)


class MirageOrchestrator:
    """Coordinator that routes capture/prioritize/review flows."""

    def __init__(
        self,
        tasks: TaskRepository,
        reviews: ReviewRepository,
        calendar: Optional[CalendarPort] = None,
        config: Optional[MirageConfig] = None,
    ) -> None:
        self.tasks = tasks
        self.reviews = reviews
        self.calendar = calendar
        self.config = config or MirageConfig()
        self.capture = TaskCaptureService(tasks)

    async def get_do_now_list(
        self,
        *,
        date: Optional[str] = None,
        enforce_calendar: bool = True,
    ) -> list[Task]:
        """Return prioritized actionable tasks, optionally filtered by calendar fit.

        When enforce_calendar is True and a CalendarPort is available,
        tasks that don't fit in today's free time are excluded.
        If the calendar is unavailable, all actionable tasks are returned.
        """
        all_tasks = await self.tasks.query(exclude_done=True)
        actionable = filter_actionable(list(all_tasks))
        sorted_tasks = sort_by_priority(actionable)

        if not enforce_calendar or self.calendar is None:
            return sorted_tasks

        query = AvailabilityQuery(
            date=date or _today_str(),
            work_start=self.config.work_start,
            work_end=self.config.work_end,
            timezone=self.config.timezone,
        )
        availability = await safe_get_availability(self.calendar, query)
        if availability is None:
            return sorted_tasks

        fits, _ = filter_calendar_fit(
            sorted_tasks, availability, self.config.buffer_minutes
        )
        return fits

    async def get_procrastination_list(self) -> list[Task]:
        """Return tasks flagged for procrastination (mentioned >= 3)."""
        all_tasks = await self.tasks.query(exclude_done=True)
        return flag_procrastinating(list(all_tasks))

    async def get_blocked_tasks(self) -> Sequence[Task]:
        """Return tasks in Blocked or Waiting On status."""
        blocked = await self.tasks.query(status=TaskStatus.BLOCKED)
        waiting = await self.tasks.query(status=TaskStatus.WAITING_ON)
        return list(blocked) + list(waiting)


def _today_str() -> str:
    """Return today's date as YYYY-MM-DD."""
    from datetime import date

    return date.today().isoformat()
