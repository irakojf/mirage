"""Domain models for Mirage core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Sequence

from .errors import ValidationError


class TaskStatus(str, Enum):
    TASKS = "Tasks"
    PROJECTS = "Projects"
    IDEAS = "Ideas"
    NOT_NOW = "Not Now"
    BLOCKED = "Blocked"
    WAITING_ON = "Waiting On"
    DONE = "Done"
    WONT_DO = "Won't Do"


class TaskType(str, Enum):
    IDENTITY = "Identity"
    COMPOUND = "Compound"
    DO_IT_NOW = "Do It Now"
    NEVER_MISS_2X = "Never Miss 2x"
    IMPORTANT_NOT_URGENT = "Important Not Urgent"
    UNBLOCKS = "Unblocks"


class EnergyLevel(str, Enum):
    RED = "Red"
    YELLOW = "Yellow"
    GREEN = "Green"


@dataclass(frozen=True)
class TaskId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValidationError("TaskId cannot be empty")


@dataclass(frozen=True)
class ProjectId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValidationError("ProjectId cannot be empty")


@dataclass(frozen=True)
class ReviewId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValidationError("ReviewId cannot be empty")


@dataclass(frozen=True)
class IdentityId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValidationError("IdentityId cannot be empty")


@dataclass(frozen=True)
class AvailabilityWindow:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValidationError("AvailabilityWindow end must be after start")


@dataclass(frozen=True)
class Availability:
    windows: Sequence[AvailabilityWindow]

    def __post_init__(self) -> None:
        if not self.windows:
            raise ValidationError("Availability requires at least one window")
        for window in self.windows:
            if not isinstance(window, AvailabilityWindow):
                raise ValidationError("Availability windows must be AvailabilityWindow")


@dataclass(frozen=True)
class Task:
    id: TaskId
    name: str
    status: TaskStatus
    mentioned: int = 1
    blocked_by: Optional[str] = None
    energy: Optional[EnergyLevel] = None
    task_type: Optional[TaskType] = None
    complete_time_minutes: Optional[int] = None
    priority: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    source: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Task name cannot be empty")
        if self.mentioned < 0:
            raise ValidationError("Task mentioned count cannot be negative")
        if self.complete_time_minutes is not None and self.complete_time_minutes <= 0:
            raise ValidationError("Task complete_time_minutes must be positive")
        if self.priority is not None and self.priority <= 0:
            raise ValidationError("Task priority must be positive")


@dataclass(frozen=True)
class TaskDraft:
    name: str
    status: TaskStatus
    mentioned: int = 1
    blocked_by: Optional[str] = None
    energy: Optional[EnergyLevel] = None
    task_type: Optional[TaskType] = None
    complete_time_minutes: Optional[int] = None
    priority: Optional[int] = None
    source: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("TaskDraft name cannot be empty")
        if self.mentioned < 0:
            raise ValidationError("TaskDraft mentioned count cannot be negative")
        if self.complete_time_minutes is not None and self.complete_time_minutes <= 0:
            raise ValidationError("TaskDraft complete_time_minutes must be positive")
        if self.priority is not None and self.priority <= 0:
            raise ValidationError("TaskDraft priority must be positive")


@dataclass(frozen=True)
class Project:
    id: ProjectId
    name: str
    tasks: Sequence[Task] = field(default_factory=tuple)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Project name cannot be empty")


@dataclass(frozen=True)
class Review:
    id: ReviewId
    week_of: datetime
    transcript: str
    wins: Optional[str] = None
    struggles: Optional[str] = None
    next_week_focus: Optional[str] = None
    tasks_completed: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.transcript.strip():
            raise ValidationError("Review transcript cannot be empty")
        if self.tasks_completed is not None and self.tasks_completed < 0:
            raise ValidationError("Review tasks_completed cannot be negative")


@dataclass(frozen=True)
class IdentityStatement:
    id: IdentityId
    text: str
    category: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValidationError("Identity statement cannot be empty")


@dataclass(frozen=True)
class IdentityProfile:
    statements: Sequence[IdentityStatement]

    def __post_init__(self) -> None:
        if not self.statements:
            raise ValidationError("Identity profile requires at least one statement")


@dataclass(frozen=True)
class TaskMutation:
    task_id: TaskId
    name: Optional[str] = None
    status: Optional[TaskStatus] = None
    mentioned: Optional[int] = None
    blocked_by: Optional[str] = None
    energy: Optional[EnergyLevel] = None
    task_type: Optional[TaskType] = None
    complete_time_minutes: Optional[int] = None
    priority: Optional[int] = None

    def __post_init__(self) -> None:
        if self.name is not None and not self.name.strip():
            raise ValidationError("TaskMutation name cannot be empty")
        if self.mentioned is not None and self.mentioned < 0:
            raise ValidationError("TaskMutation mentioned cannot be negative")
        if self.complete_time_minutes is not None and self.complete_time_minutes <= 0:
            raise ValidationError("TaskMutation complete_time_minutes must be positive")
        if self.priority is not None and self.priority <= 0:
            raise ValidationError("TaskMutation priority must be positive")
