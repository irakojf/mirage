"""Tests for mirage_core weekly review service."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Sequence

from mirage_core import (
    Review,
    ReviewId,
    Task,
    TaskDraft,
    TaskId,
    TaskMutation,
    TaskStatus,
    EnergyLevel,
)
from mirage_core.ports import ReviewRepository, TaskRepository
from mirage_core.review import (
    CompletedSummary,
    EnergyBreakdown,
    ProcrastinationItem,
    ReviewData,
    ReviewService,
)


# -- In-memory repos for testing -------------------------------------------


class InMemoryTaskRepo(TaskRepository):
    def __init__(self, tasks: list[Task] | None = None) -> None:
        self._tasks: dict[str, Task] = {}
        if tasks:
            for t in tasks:
                self._tasks[t.id.value] = t

    async def query(
        self, *, status: Optional[TaskStatus] = None, exclude_done: bool = False
    ) -> Sequence[Task]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if exclude_done:
            tasks = [
                t for t in tasks
                if t.status not in (TaskStatus.DONE, TaskStatus.WONT_DO)
            ]
        return tasks

    async def get(self, task_id: TaskId) -> Optional[Task]:
        return self._tasks.get(task_id.value)

    async def create(self, draft: TaskDraft) -> Task:
        raise NotImplementedError

    async def update(self, mutation: TaskMutation) -> Task:
        raise NotImplementedError

    async def increment_mentioned(self, task_id: TaskId) -> int:
        raise NotImplementedError


class InMemoryReviewRepo(ReviewRepository):
    def __init__(self) -> None:
        self._reviews: list[Review] = []

    async def create(self, review: Review) -> Review:
        saved = Review(
            id=ReviewId(f"rev-{len(self._reviews) + 1}"),
            week_of=review.week_of,
            transcript=review.transcript,
            wins=review.wins,
            struggles=review.struggles,
            next_week_focus=review.next_week_focus,
            tasks_completed=review.tasks_completed,
        )
        self._reviews.append(saved)
        return saved


# -- Fixtures --------------------------------------------------------------

now = datetime.now()
last_monday = now - timedelta(days=now.weekday())
week_start = last_monday.strftime("%Y-%m-%d")


def _task(
    tid: str,
    name: str,
    status: TaskStatus = TaskStatus.TASKS,
    mentioned: int = 1,
    energy: Optional[EnergyLevel] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
    priority: Optional[int] = None,
    complete_time_minutes: Optional[int] = None,
) -> Task:
    return Task(
        id=TaskId(tid),
        name=name,
        status=status,
        mentioned=mentioned,
        energy=energy,
        created_at=created_at,
        updated_at=updated_at,
        priority=priority,
        complete_time_minutes=complete_time_minutes,
    )


# -- Tests -----------------------------------------------------------------


def test_completed_summary():
    tasks = [
        _task("1", "Done task", TaskStatus.DONE, updated_at=now - timedelta(days=1)),
        _task("2", "Old done", TaskStatus.DONE, updated_at=now - timedelta(days=14)),
        _task("3", "Open task", TaskStatus.TASKS),
    ]
    repo = InMemoryTaskRepo(tasks)
    reviews = InMemoryReviewRepo()
    svc = ReviewService(repo, reviews)

    data = asyncio.run(svc.gather_review_data(week_start))
    assert data.completed.count >= 1  # at least the recent done task


def test_procrastination_list_by_mentioned():
    tasks = [
        _task("1", "Procrastinated", mentioned=5),
        _task("2", "Normal", mentioned=1),
    ]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())

    data = asyncio.run(svc.gather_review_data(week_start))
    assert len(data.procrastination_list) == 1
    assert data.procrastination_list[0].task.name == "Procrastinated"
    assert "mentioned 5 times" in data.procrastination_list[0].reason


def test_procrastination_list_by_staleness():
    old_date = now - timedelta(days=30)
    tasks = [
        _task("1", "Stale task", created_at=old_date),
        _task("2", "Fresh task", created_at=now),
    ]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())

    data = asyncio.run(svc.gather_review_data(week_start))
    stale_items = [
        p for p in data.procrastination_list if "stale" in p.reason
    ]
    assert len(stale_items) == 1
    assert stale_items[0].task.name == "Stale task"


def test_energy_breakdown():
    tasks = [
        _task("1", "Red", TaskStatus.DONE, energy=EnergyLevel.RED, updated_at=now),
        _task("2", "Green", TaskStatus.DONE, energy=EnergyLevel.GREEN, updated_at=now),
        _task("3", "Green2", TaskStatus.DONE, energy=EnergyLevel.GREEN, updated_at=now),
        _task("4", "None", TaskStatus.DONE, updated_at=now),
    ]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())

    data = asyncio.run(svc.gather_review_data(week_start))
    e = data.energy
    assert e.red >= 1
    assert e.green >= 2
    assert e.drain_ratio > 0


def test_stale_decisions():
    old_date = now - timedelta(days=20)
    tasks = [
        _task("1", "Stale idea", TaskStatus.IDEAS, created_at=old_date),
        _task("2", "Fresh task", TaskStatus.TASKS, created_at=now),
    ]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())

    data = asyncio.run(svc.gather_review_data(week_start))
    assert len(data.stale_decisions) == 1
    assert data.stale_decisions[0].name == "Stale idea"


def test_persist_review():
    tasks = [_task("1", "Done", TaskStatus.DONE, updated_at=now)]
    task_repo = InMemoryTaskRepo(tasks)
    review_repo = InMemoryReviewRepo()
    svc = ReviewService(task_repo, review_repo)

    data = asyncio.run(svc.gather_review_data(week_start))
    review = asyncio.run(svc.persist_review(
        data,
        transcript="Full review conversation...",
        wins="Shipped feature X",
        struggles="Context switching",
        next_week_focus="Deep work mornings",
    ))

    assert review.id.value == "rev-1"
    assert review.wins == "Shipped feature X"
    assert review.tasks_completed == data.completed.count
    assert len(review_repo._reviews) == 1


def test_override_detection():
    tasks = [
        _task("1", "Manual priority", priority=1),
        _task("2", "Manual priority 2", priority=3),
        _task("3", "Auto priority"),
        _task("4", "Auto priority 2"),
        _task("5", "Auto priority 3"),
    ]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())

    data = asyncio.run(svc.gather_review_data(week_start))
    assert data.overrides is not None
    assert data.overrides.manual_count == 2
    assert data.overrides.auto_count == 3
    assert data.overrides.override_rate == 2 / 5
    assert len(data.overrides.manual_tasks) == 2


def test_energy_breakdown_all_unrated():
    e = EnergyBreakdown(unrated=5)
    assert e.total == 5
    assert e.drain_ratio == 0.0


def test_energy_breakdown_all_red():
    e = EnergyBreakdown(red=3)
    assert e.drain_ratio == 1.0


def test_insights_no_completed():
    tasks = [_task("1", "Open", TaskStatus.TASKS)]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())
    data = asyncio.run(svc.gather_review_data(week_start))
    assert any("No tasks completed" in i for i in data.insights)


def test_insights_procrastination():
    tasks = [_task("1", "Avoided task", mentioned=5)]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())
    data = asyncio.run(svc.gather_review_data(week_start))
    assert any("procrastination" in i.lower() for i in data.insights)


def test_insights_stale_decisions():
    old_date = now - timedelta(days=20)
    tasks = [
        _task("1", "Stale 1", created_at=old_date),
        _task("2", "Stale 2", created_at=old_date),
        _task("3", "Stale 3", created_at=old_date),
    ]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())
    data = asyncio.run(svc.gather_review_data(week_start))
    assert any("stale" in i.lower() for i in data.insights)


def test_insights_energy_warning():
    tasks = [
        _task("1", "Red1", TaskStatus.DONE, energy=EnergyLevel.RED, updated_at=now),
        _task("2", "Red2", TaskStatus.DONE, energy=EnergyLevel.RED, updated_at=now),
        _task("3", "Green", TaskStatus.DONE, energy=EnergyLevel.GREEN, updated_at=now),
    ]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())
    data = asyncio.run(svc.gather_review_data(week_start))
    assert any("energy" in i.lower() for i in data.insights)


def test_insights_steady_week():
    """When nothing is flagged, get a steady-week message."""
    data = ReviewData(
        week_start=week_start,
        completed=CompletedSummary(tasks=[], count=5),
        procrastination_list=[],
        energy=EnergyBreakdown(green=5),
        stale_decisions=[],
    )
    assert any("steady" in i.lower() for i in data.insights)


def test_generate_insights_structured():
    """generate_insights returns ReviewInsightsSummary with typed insights."""
    from mirage_core.review import (
        InsightCategory,
        InsightSeverity,
        ReviewInsightsSummary,
        generate_insights,
    )

    tasks = [_task("1", "Open", TaskStatus.TASKS)]
    repo = InMemoryTaskRepo(tasks)
    svc = ReviewService(repo, InMemoryReviewRepo())
    data = asyncio.run(svc.gather_review_data(week_start))

    summary = generate_insights(data)
    assert isinstance(summary, ReviewInsightsSummary)
    assert len(summary.insights) > 0
    # Each insight has required fields
    for insight in summary.insights:
        assert isinstance(insight.category, InsightCategory)
        assert isinstance(insight.severity, InsightSeverity)
        assert len(insight.message) > 0


def test_generate_insights_workload():
    """Workload constraint appears when open tasks have estimates."""
    from mirage_core.review import InsightCategory, generate_insights

    data = ReviewData(
        week_start=week_start,
        completed=CompletedSummary(tasks=[], count=5),
        procrastination_list=[],
        energy=EnergyBreakdown(green=5),
        stale_decisions=[],
        open_tasks=[
            _task("1", "Task A", complete_time_minutes=60),
            _task("2", "Task B", complete_time_minutes=120),
            _task("3", "Task C"),  # no estimate
        ],
    )
    summary = generate_insights(data)
    workload = [i for i in summary.insights if i.category == InsightCategory.WORKLOAD]
    assert len(workload) == 1
    assert workload[0].data["total_hours"] == 3.0
    assert workload[0].data["unestimated_count"] == 1
    assert "3.0h" in workload[0].message


def test_generate_insights_critical_procrastination():
    """Tasks mentioned >= 6 times get CRITICAL severity."""
    from mirage_core.review import InsightCategory, InsightSeverity, generate_insights

    data = ReviewData(
        week_start=week_start,
        completed=CompletedSummary(tasks=[], count=5),
        procrastination_list=[
            ProcrastinationItem(
                task=_task("1", "Chronic avoider", mentioned=7),
                reason="mentioned 7 times",
            ),
        ],
        energy=EnergyBreakdown(green=5),
        stale_decisions=[],
    )
    summary = generate_insights(data)
    proc = [i for i in summary.insights if i.category == InsightCategory.PROCRASTINATION]
    assert len(proc) == 1
    assert proc[0].severity == InsightSeverity.CRITICAL


def test_generate_insights_messages_match_insights():
    """ReviewInsightsSummary.messages matches ReviewData.insights for compat."""
    from mirage_core.review import generate_insights

    data = ReviewData(
        week_start=week_start,
        completed=CompletedSummary(tasks=[], count=0),
        procrastination_list=[],
        energy=EnergyBreakdown(),
        stale_decisions=[],
    )
    summary = generate_insights(data)
    assert data.insights == summary.messages


if __name__ == "__main__":
    test_completed_summary()
    test_procrastination_list_by_mentioned()
    test_procrastination_list_by_staleness()
    test_energy_breakdown()
    test_stale_decisions()
    test_persist_review()
    test_energy_breakdown_all_unrated()
    test_energy_breakdown_all_red()
    test_generate_insights_structured()
    test_generate_insights_workload()
    test_generate_insights_critical_procrastination()
    test_generate_insights_messages_match_insights()
    print("All review tests passed!")
