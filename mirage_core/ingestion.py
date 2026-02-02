"""Ingestion module: capture, normalize, deduplicate, and persist tasks.

This is the single entry point for all task intake surfaces (Slack, CLI,
Claude app). Adapters call `IngestionService.ingest()` with a `CaptureRequest`
and receive a `CaptureResult`.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .aliases import resolve_status, resolve_type
from .errors import ValidationError
from .models import Task, TaskDraft, TaskId, TaskStatus, TaskType
from .ports import TaskRepository
from .services import normalize_task_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Capture API contract
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CaptureRequest:
    """Input from any intake surface."""

    raw_content: str
    status: str = "action"
    blocked_by: Optional[str] = None
    tag: Optional[str] = None
    complete_time_minutes: Optional[int] = None
    source: str = "unknown"

    def __post_init__(self) -> None:
        if not self.raw_content or not self.raw_content.strip():
            raise ValidationError("CaptureRequest raw_content cannot be empty")


@dataclass(frozen=True)
class CaptureResult:
    """Output returned after ingestion."""

    task: Task
    is_duplicate: bool = False
    duplicate_of: Optional[TaskId] = None
    was_created: bool = True
    new_mentioned_count: Optional[int] = None


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------

DEDUP_SIMILARITY_THRESHOLD = 0.85


def _normalize_for_dedup(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for fuzzy matching."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def find_exact_duplicate(
    name: str, existing: Sequence[Task]
) -> Optional[Task]:
    """Return the first task whose normalized name matches exactly."""
    needle = _normalize_for_dedup(name)
    for task in existing:
        if _normalize_for_dedup(task.name) == needle:
            return task
    return None


# ---------------------------------------------------------------------------
# Ingestion service
# ---------------------------------------------------------------------------

class IngestionService:
    """Orchestrates the full capture pipeline.

    1. Normalize raw content
    2. Resolve status / type aliases
    3. Check for duplicates
    4. If duplicate → increment mentioned
    5. If new → create task
    """

    def __init__(self, repo: TaskRepository) -> None:
        self._repo = repo

    async def ingest(self, request: CaptureRequest) -> CaptureResult:
        """Process a single capture request end-to-end."""
        # 1. Normalize
        name = normalize_task_name(request.raw_content)

        # 2. Resolve aliases
        status = resolve_status(request.status)
        task_type = resolve_type(request.tag) if request.tag else None

        # 3. Check for duplicates among open tasks
        open_tasks = await self._repo.query(exclude_done=True)
        dup = find_exact_duplicate(name, open_tasks)

        if dup is not None:
            # 4a. Duplicate → increment mentioned counter
            new_count = await self._repo.increment_mentioned(dup.id)
            logger.info(
                "Duplicate detected: '%s' matches '%s' (mentioned=%d)",
                name, dup.name, new_count,
            )
            return CaptureResult(
                task=dup,
                is_duplicate=True,
                duplicate_of=dup.id,
                was_created=False,
                new_mentioned_count=new_count,
            )

        # 4b. New task → create
        draft = TaskDraft(
            name=name,
            status=status,
            mentioned=1,
            blocked_by=request.blocked_by or None,
            task_type=task_type,
            complete_time_minutes=request.complete_time_minutes,
            source=request.source,
        )
        created = await self._repo.create(draft)
        logger.info("Created task: '%s' [%s]", created.name, created.status.value)
        return CaptureResult(task=created, is_duplicate=False, was_created=True)

    async def ingest_batch(
        self, requests: Sequence[CaptureRequest]
    ) -> list[CaptureResult]:
        """Process multiple capture requests (e.g. brain dump)."""
        results = []
        for req in requests:
            result = await self.ingest(req)
            results.append(result)
        return results
