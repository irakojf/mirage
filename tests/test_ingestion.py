"""Tests for mirage_core ingestion pipeline."""

import asyncio
from typing import Optional, Sequence

from mirage_core import (
    CaptureRequest,
    IngestionService,
    Task,
    TaskDraft,
    TaskId,
    TaskMutation,
    TaskStatus,
)
from mirage_core.ports import TaskRepository


class InMemoryTaskRepo(TaskRepository):
    """In-memory task repository for testing."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._counter = 0

    async def query(
        self, *, status: Optional[TaskStatus] = None, exclude_done: bool = False
    ) -> Sequence[Task]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if exclude_done:
            tasks = [
                t
                for t in tasks
                if t.status not in (TaskStatus.DONE, TaskStatus.WONT_DO)
            ]
        return tasks

    async def get(self, task_id: TaskId) -> Optional[Task]:
        return self._tasks.get(task_id.value)

    async def create(self, draft: TaskDraft) -> Task:
        self._counter += 1
        new_id = f"test-{self._counter}"
        created = Task(
            id=TaskId(new_id),
            name=draft.name,
            status=draft.status,
            mentioned=draft.mentioned,
            blocked_by=draft.blocked_by,
            energy=draft.energy,
            task_type=draft.task_type,
            complete_time_minutes=draft.complete_time_minutes,
            priority=draft.priority,
        )
        self._tasks[new_id] = created
        return created

    async def update(self, mutation: TaskMutation) -> Task:
        existing = self._tasks[mutation.task_id.value]
        self._tasks[mutation.task_id.value] = Task(
            id=existing.id,
            name=mutation.name or existing.name,
            status=mutation.status or existing.status,
            mentioned=mutation.mentioned if mutation.mentioned is not None else existing.mentioned,
            blocked_by=mutation.blocked_by if mutation.blocked_by is not None else existing.blocked_by,
            energy=mutation.energy or existing.energy,
            task_type=mutation.task_type or existing.task_type,
            complete_time_minutes=mutation.complete_time_minutes or existing.complete_time_minutes,
            priority=mutation.priority or existing.priority,
        )
        return self._tasks[mutation.task_id.value]

    async def increment_mentioned(self, task_id: TaskId) -> int:
        existing = self._tasks[task_id.value]
        new_count = existing.mentioned + 1
        self._tasks[task_id.value] = Task(
            id=existing.id,
            name=existing.name,
            status=existing.status,
            mentioned=new_count,
            blocked_by=existing.blocked_by,
            energy=existing.energy,
            task_type=existing.task_type,
            complete_time_minutes=existing.complete_time_minutes,
            priority=existing.priority,
        )
        return new_count


def test_ingest_new_task():
    repo = InMemoryTaskRepo()
    svc = IngestionService(repo)

    req = CaptureRequest(raw_content="- Call mom", status="action", source="test")
    result = asyncio.run(svc.ingest(req))

    assert result.was_created is True
    assert result.is_duplicate is False
    assert result.task.name == "Call mom"
    assert result.task.status == TaskStatus.TASKS


def test_ingest_duplicate_increments_mentioned():
    repo = InMemoryTaskRepo()
    svc = IngestionService(repo)

    req1 = CaptureRequest(raw_content="Call mom", status="action", source="test")
    r1 = asyncio.run(svc.ingest(req1))
    assert r1.was_created is True
    assert r1.task.mentioned == 1

    req2 = CaptureRequest(raw_content="call mom", status="action", source="test")
    r2 = asyncio.run(svc.ingest(req2))
    assert r2.is_duplicate is True
    assert r2.was_created is False
    assert r2.new_mentioned_count == 2


def test_ingest_batch():
    repo = InMemoryTaskRepo()
    svc = IngestionService(repo)

    requests = [
        CaptureRequest(raw_content="Buy groceries", status="action"),
        CaptureRequest(raw_content="Plan vacation", status="project"),
        CaptureRequest(raw_content="Buy groceries", status="action"),  # duplicate
    ]
    results = asyncio.run(svc.ingest_batch(requests))

    assert len(results) == 3
    assert results[0].was_created is True
    assert results[1].was_created is True
    assert results[2].is_duplicate is True
    assert results[2].new_mentioned_count == 2


def test_ingest_with_blocked():
    repo = InMemoryTaskRepo()
    svc = IngestionService(repo)

    req = CaptureRequest(
        raw_content="Get designs", status="blocked", blocked_by="Sarah"
    )
    result = asyncio.run(svc.ingest(req))

    assert result.task.status == TaskStatus.BLOCKED
    assert result.task.blocked_by == "Sarah"


def test_ingest_with_tag():
    repo = InMemoryTaskRepo()
    svc = IngestionService(repo)

    req = CaptureRequest(raw_content="Meditate", status="action", tag="Identity")
    result = asyncio.run(svc.ingest(req))

    from mirage_core import TaskType
    assert result.task.task_type == TaskType.IDENTITY


def test_normalization_strips_bullets():
    repo = InMemoryTaskRepo()
    svc = IngestionService(repo)

    for prefix in ["- ", "* ", "• ", "→ "]:
        req = CaptureRequest(raw_content=f"{prefix}Test task {prefix}", status="action")
        result = asyncio.run(svc.ingest(req))
        assert not result.task.name.startswith(prefix.strip())


if __name__ == "__main__":
    test_ingest_new_task()
    test_ingest_duplicate_increments_mentioned()
    test_ingest_batch()
    test_ingest_with_blocked()
    test_ingest_with_tag()
    test_normalization_strips_bullets()
    print("All ingestion tests passed!")
