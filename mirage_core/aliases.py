"""Status and type alias resolution.

Maps user-facing / legacy names to canonical enum values.
Kept in sync with status_aliases in schema/tasks.yaml.
"""

from __future__ import annotations

from .models import TaskStatus, TaskType

STATUS_ALIASES: dict[str, TaskStatus] = {
    "Action": TaskStatus.TASKS,
    "action": TaskStatus.TASKS,
    "Project": TaskStatus.PROJECTS,
    "project": TaskStatus.PROJECTS,
    "Idea": TaskStatus.IDEAS,
    "idea": TaskStatus.IDEAS,
    "blocked": TaskStatus.BLOCKED,
    "done": TaskStatus.DONE,
    "Waiting On": TaskStatus.WAITING_ON,
    "Not Now": TaskStatus.NOT_NOW,
    "Won't Do": TaskStatus.WONT_DO,
}

TYPE_ALIASES: dict[str, TaskType] = {
    "Compounds": TaskType.COMPOUND,
}

# Maps AI-processor tag strings (e.g. from Claude prompts) to canonical TaskType.
TAG_ALIASES: dict[str, TaskType] = {
    "[DO IT]": TaskType.DO_IT_NOW,
    "[KEYSTONE]": TaskType.UNBLOCKS,
    "[COMPOUNDS]": TaskType.COMPOUND,
    "[IDENTITY]": TaskType.IDENTITY,
    "[IMPORTANT NOT URGENT]": TaskType.IMPORTANT_NOT_URGENT,
    "[NEVER MISS 2X]": TaskType.NEVER_MISS_2X,
    "[UNBLOCKS]": TaskType.UNBLOCKS,
}


def resolve_tag(raw: str) -> TaskType | None:
    """Resolve an AI-generated tag string to a TaskType, or None if unrecognised."""
    return TAG_ALIASES.get(raw.upper())


def resolve_status(raw: str) -> TaskStatus:
    """Resolve a raw status string to a canonical TaskStatus.

    Accepts canonical names (e.g. "Tasks"), aliases (e.g. "Action"),
    and case-insensitive variants (e.g. "action").
    Raises ValueError for unknown statuses.
    """
    try:
        return TaskStatus(raw)
    except ValueError:
        pass
    if raw in STATUS_ALIASES:
        return STATUS_ALIASES[raw]
    raise ValueError(f"Unknown status: {raw!r}")


def resolve_type(raw: str) -> TaskType:
    """Resolve a raw type string to a canonical TaskType."""
    try:
        return TaskType(raw)
    except ValueError:
        pass
    if raw in TYPE_ALIASES:
        return TYPE_ALIASES[raw]
    raise ValueError(f"Unknown task type: {raw!r}")
