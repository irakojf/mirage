"""Interfaces for external dependencies (storage, calendar, etc.).

Adapters (Notion MCP, Slack bot, Google Calendar) implement these
protocols. Core services depend only on these abstractions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from .models import (
    Availability,
    IdentityProfile,
    Review,
    Task,
    TaskDraft,
    TaskId,
    TaskMutation,
    TaskStatus,
)


class TaskRepository(ABC):
    """Read/write access to the task store (e.g. Notion)."""

    @abstractmethod
    async def query(
        self,
        *,
        status: Optional[TaskStatus] = None,
        exclude_done: bool = False,
    ) -> Sequence[Task]:
        """Return tasks matching the filter criteria."""

    @abstractmethod
    async def get(self, task_id: TaskId) -> Optional[Task]:
        """Return a single task by ID, or None if not found."""

    @abstractmethod
    async def create(self, task: TaskDraft) -> Task:
        """Persist a new task. Returns the task with its assigned ID."""

    @abstractmethod
    async def update(self, mutation: TaskMutation) -> Task:
        """Apply a mutation to an existing task. Returns the updated task."""

    @abstractmethod
    async def increment_mentioned(self, task_id: TaskId) -> int:
        """Increment the mentioned counter. Returns the new count."""


class ReviewRepository(ABC):
    """Read/write access to review records."""

    @abstractmethod
    async def create(self, review: Review) -> Review:
        """Persist a new weekly review."""


class IdentityRepository(ABC):
    """Read/write access to identity statements."""

    @abstractmethod
    async def get_profile(self) -> IdentityProfile:
        """Return the current identity profile."""

    @abstractmethod
    async def update_profile(self, profile: IdentityProfile) -> None:
        """Replace the identity profile."""


class CalendarPort(ABC):
    """Read access to calendar availability."""

    @abstractmethod
    async def get_availability(self, date: str) -> Availability:
        """Return free time blocks for a given date (YYYY-MM-DD)."""

    @abstractmethod
    async def get_week_overview(self) -> dict:
        """Return busy/free summary for the current week."""
