"""Weekly review service: data gathering, insights, and persistence.

Coordinates the /review flow by pulling data from task and calendar
repositories, computing summaries, and persisting the review record.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Sequence

from .config import MirageConfig
from .models import (
    Availability,
    EnergyLevel,
    Review,
    ReviewId,
    Task,
    TaskId,
    TaskStatus,
)
from .ports import CalendarPort, ReviewRepository, TaskRepository

logger = logging.getLogger(__name__)

PROCRASTINATION_THRESHOLD = 3
STALE_DAYS_THRESHOLD = 14


# ---------------------------------------------------------------------------
# Data containers for review summaries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompletedSummary:
    """Tasks completed this week."""

    tasks: Sequence[Task]
    count: int


@dataclass(frozen=True)
class ProcrastinationItem:
    """A task flagged for procrastination attention."""

    task: Task
    reason: str  # "mentioned 5 times" or "stale for 21 days"


@dataclass(frozen=True)
class EnergyBreakdown:
    """Distribution of energy ratings across completed tasks."""

    red: int = 0
    yellow: int = 0
    green: int = 0
    unrated: int = 0

    @property
    def total(self) -> int:
        return self.red + self.yellow + self.green + self.unrated

    @property
    def drain_ratio(self) -> float:
        """Fraction of rated tasks that were energy-draining (red)."""
        rated = self.red + self.yellow + self.green
        if rated == 0:
            return 0.0
        return self.red / rated


@dataclass(frozen=True)
class PlannedVsDone:
    """Comparison of planned (calendar) vs actually completed."""

    planned_count: int
    done_count: int
    completion_rate: float  # 0.0 to 1.0


@dataclass(frozen=True)
class OverrideSummary:
    """Summary of manual priority overrides among open tasks."""

    manual_count: int  # tasks with explicit priority set
    auto_count: int  # tasks without explicit priority
    manual_tasks: Sequence[Task] = field(default_factory=tuple)

    @property
    def override_rate(self) -> float:
        """Fraction of tasks with manual priority overrides."""
        total = self.manual_count + self.auto_count
        if total == 0:
            return 0.0
        return self.manual_count / total


# ---------------------------------------------------------------------------
# Review insights — structured, data-backed observations
# ---------------------------------------------------------------------------

ENERGY_DRAIN_THRESHOLD = 0.5
HIGH_OVERRIDE_THRESHOLD = 0.5
STALE_CLUSTER_THRESHOLD = 3


class InsightSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class InsightCategory(str, Enum):
    VELOCITY = "velocity"
    ENERGY = "energy"
    PROCRASTINATION = "procrastination"
    STALENESS = "staleness"
    OVERRIDES = "overrides"
    WORKLOAD = "workload"


@dataclass(frozen=True)
class ReviewInsight:
    """A single data-backed observation from the review."""

    category: InsightCategory
    severity: InsightSeverity
    message: str
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewInsightsSummary:
    """Structured collection of review insights."""

    insights: Sequence[ReviewInsight]

    @property
    def warnings(self) -> list[ReviewInsight]:
        return [i for i in self.insights if i.severity == InsightSeverity.WARNING]

    @property
    def critical(self) -> list[ReviewInsight]:
        return [i for i in self.insights if i.severity == InsightSeverity.CRITICAL]

    @property
    def messages(self) -> list[str]:
        """Plain text list for simple display."""
        return [i.message for i in self.insights]


@dataclass(frozen=True)
class ReviewData:
    """All data gathered for a weekly review."""

    week_start: str
    completed: CompletedSummary
    procrastination_list: Sequence[ProcrastinationItem]
    energy: EnergyBreakdown
    stale_decisions: Sequence[Task]
    overrides: Optional[OverrideSummary] = None
    planned_vs_done: Optional[PlannedVsDone] = None
    open_tasks: Sequence[Task] = field(default_factory=tuple)

    @property
    def insights(self) -> list[str]:
        """Plain text insights for backward compat."""
        return generate_insights(self).messages


def generate_insights(data: ReviewData) -> ReviewInsightsSummary:
    """Derive structured insights from review data.

    Each insight is categorised, severity-rated, and carries the backing
    data so consumers can decide how to render or act on it.
    """
    items: list[ReviewInsight] = []

    # -- Velocity ----------------------------------------------------------
    if data.completed.count == 0:
        items.append(ReviewInsight(
            category=InsightCategory.VELOCITY,
            severity=InsightSeverity.WARNING,
            message="No tasks completed this week. What got in the way?",
            data={"completed": 0},
        ))
    elif data.completed.count >= 10:
        items.append(ReviewInsight(
            category=InsightCategory.VELOCITY,
            severity=InsightSeverity.INFO,
            message=f"Strong week: {data.completed.count} tasks completed.",
            data={"completed": data.completed.count},
        ))

    # -- Energy ------------------------------------------------------------
    if data.energy.total > 0 and data.energy.drain_ratio > ENERGY_DRAIN_THRESHOLD:
        items.append(ReviewInsight(
            category=InsightCategory.ENERGY,
            severity=InsightSeverity.WARNING,
            message=(
                f"Energy warning: {data.energy.red}/{data.energy.total} completed "
                f"tasks were energy-draining. Look for ways to reduce friction."
            ),
            data={"red": data.energy.red, "total": data.energy.total,
                  "drain_ratio": round(data.energy.drain_ratio, 2)},
        ))
    elif data.energy.total > 0 and data.energy.unrated == data.energy.total:
        items.append(ReviewInsight(
            category=InsightCategory.ENERGY,
            severity=InsightSeverity.INFO,
            message=(
                "No tasks have energy ratings. Start tagging Red/Yellow/Green "
                "to reveal patterns."
            ),
            data={"unrated": data.energy.unrated},
        ))

    # -- Procrastination ---------------------------------------------------
    if data.procrastination_list:
        top = data.procrastination_list[0]
        severity = (
            InsightSeverity.CRITICAL
            if top.task.mentioned >= PROCRASTINATION_THRESHOLD * 2
            else InsightSeverity.WARNING
        )
        items.append(ReviewInsight(
            category=InsightCategory.PROCRASTINATION,
            severity=severity,
            message=(
                f'Top procrastination: "{top.task.name}" ({top.reason}). '
                f"What would this look like if it were easy?"
            ),
            data={"task_name": top.task.name, "mentioned": top.task.mentioned,
                  "total_flagged": len(data.procrastination_list)},
        ))

    # -- Staleness ---------------------------------------------------------
    if len(data.stale_decisions) >= STALE_CLUSTER_THRESHOLD:
        items.append(ReviewInsight(
            category=InsightCategory.STALENESS,
            severity=InsightSeverity.WARNING,
            message=(
                f"{len(data.stale_decisions)} stale items (14+ days). "
                f"Decide: do it, delegate it, or drop it."
            ),
            data={"stale_count": len(data.stale_decisions)},
        ))

    # -- Overrides ---------------------------------------------------------
    if data.overrides and data.overrides.override_rate > HIGH_OVERRIDE_THRESHOLD:
        items.append(ReviewInsight(
            category=InsightCategory.OVERRIDES,
            severity=InsightSeverity.WARNING,
            message=(
                f"{data.overrides.manual_count} tasks have manual priority. "
                f"If overriding the system often, revisit your prioritization rules."
            ),
            data={"manual_count": data.overrides.manual_count,
                  "override_rate": round(data.overrides.override_rate, 2)},
        ))

    # -- Workload constraint -----------------------------------------------
    open_with_estimate = [
        t for t in data.open_tasks if t.complete_time_minutes is not None
    ]
    if open_with_estimate:
        total_minutes = sum(t.complete_time_minutes for t in open_with_estimate)  # type: ignore[arg-type]
        total_hours = round(total_minutes / 60, 1)
        unestimated = len(data.open_tasks) - len(open_with_estimate)
        severity = (
            InsightSeverity.WARNING if total_hours > 20
            else InsightSeverity.INFO
        )
        msg = (
            f"Open workload: {total_hours}h estimated across "
            f"{len(open_with_estimate)} tasks."
        )
        if unestimated:
            msg += f" {unestimated} tasks have no estimate."
        items.append(ReviewInsight(
            category=InsightCategory.WORKLOAD,
            severity=severity,
            message=msg,
            data={"total_hours": total_hours,
                  "estimated_count": len(open_with_estimate),
                  "unestimated_count": unestimated},
        ))

    # -- Default -----------------------------------------------------------
    if not items:
        items.append(ReviewInsight(
            category=InsightCategory.VELOCITY,
            severity=InsightSeverity.INFO,
            message="Steady week. Keep the systems running.",
        ))

    return ReviewInsightsSummary(insights=items)


# ---------------------------------------------------------------------------
# Review service
# ---------------------------------------------------------------------------


class ReviewService:
    """Orchestrates the weekly review data gathering and persistence."""

    def __init__(
        self,
        tasks: TaskRepository,
        reviews: ReviewRepository,
        calendar: Optional[CalendarPort] = None,
        config: Optional[MirageConfig] = None,
    ) -> None:
        self._tasks = tasks
        self._reviews = reviews
        self._calendar = calendar
        self._config = config or MirageConfig()

    async def gather_review_data(
        self,
        week_start: Optional[str] = None,
    ) -> ReviewData:
        """Pull all data needed for a weekly review.

        Args:
            week_start: YYYY-MM-DD of the review week's Monday.
                        Defaults to the most recent Monday.
        """
        if week_start is None:
            today = datetime.now()
            monday = today - timedelta(days=today.weekday())
            week_start = monday.strftime("%Y-%m-%d")

        all_tasks = list(await self._tasks.query(exclude_done=False))
        open_tasks = [
            t for t in all_tasks
            if t.status not in (TaskStatus.DONE, TaskStatus.WONT_DO)
        ]

        # 1. Completed this week
        completed = self._get_completed(all_tasks, week_start)

        # 2. Procrastination pressure
        procrastination = self._get_procrastination_list(open_tasks)

        # 3. Energy breakdown of completed tasks
        energy = self._compute_energy(completed.tasks)

        # 4. Stale decisions (open tasks with no updates for 14+ days)
        stale = self._get_stale_decisions(open_tasks)

        # 5. Override patterns
        overrides = self._detect_overrides(open_tasks)

        # 6. Planned vs done (if calendar available)
        planned_vs_done = None

        return ReviewData(
            week_start=week_start,
            completed=completed,
            procrastination_list=procrastination,
            energy=energy,
            stale_decisions=stale,
            overrides=overrides,
            planned_vs_done=planned_vs_done,
            open_tasks=open_tasks,
        )

    async def persist_review(
        self,
        data: ReviewData,
        transcript: str,
        wins: str = "",
        struggles: str = "",
        next_week_focus: str = "",
    ) -> Review:
        """Save the review record to the repository."""
        review = Review(
            id=ReviewId("pending"),
            week_of=datetime.strptime(data.week_start, "%Y-%m-%d"),
            transcript=transcript,
            wins=wins or None,
            struggles=struggles or None,
            next_week_focus=next_week_focus or None,
            tasks_completed=data.completed.count,
        )
        return await self._reviews.create(review)

    # -- Internal helpers --------------------------------------------------

    def _get_completed(
        self, all_tasks: Sequence[Task], week_start: str
    ) -> CompletedSummary:
        """Return tasks that transitioned to Done this week."""
        done = [t for t in all_tasks if t.status == TaskStatus.DONE]
        # Filter by updated_at if available
        start = datetime.strptime(week_start, "%Y-%m-%d")
        end = start + timedelta(days=7)

        this_week = []
        for t in done:
            if t.updated_at is not None:
                if start <= t.updated_at < end:
                    this_week.append(t)
            # If no updated_at, we can't filter by date — include all
            # (the adapter should populate updated_at)

        # If no tasks have updated_at, fall back to all done tasks
        if not this_week and done:
            this_week = done

        return CompletedSummary(tasks=this_week, count=len(this_week))

    def _get_procrastination_list(
        self, open_tasks: Sequence[Task]
    ) -> list[ProcrastinationItem]:
        """Return tasks mentioned >= threshold or stale >= 14 days."""
        items = []
        now = datetime.now()

        for t in open_tasks:
            reasons = []
            if t.mentioned >= PROCRASTINATION_THRESHOLD:
                reasons.append(f"mentioned {t.mentioned} times")
            if t.created_at is not None:
                age_days = (now - t.created_at).days
                if age_days >= STALE_DAYS_THRESHOLD:
                    reasons.append(f"stale for {age_days} days")

            if reasons:
                items.append(ProcrastinationItem(
                    task=t,
                    reason="; ".join(reasons),
                ))

        # Sort by mentioned count descending
        items.sort(key=lambda x: x.task.mentioned, reverse=True)
        return items

    def _compute_energy(self, tasks: Sequence[Task]) -> EnergyBreakdown:
        """Compute energy distribution across tasks."""
        red = yellow = green = unrated = 0
        for t in tasks:
            if t.energy == EnergyLevel.RED:
                red += 1
            elif t.energy == EnergyLevel.YELLOW:
                yellow += 1
            elif t.energy == EnergyLevel.GREEN:
                green += 1
            else:
                unrated += 1
        return EnergyBreakdown(red=red, yellow=yellow, green=green, unrated=unrated)

    def _detect_overrides(self, open_tasks: Sequence[Task]) -> OverrideSummary:
        """Detect tasks with manual priority overrides."""
        manual = [t for t in open_tasks if t.priority is not None]
        auto = [t for t in open_tasks if t.priority is None]
        return OverrideSummary(
            manual_count=len(manual),
            auto_count=len(auto),
            manual_tasks=manual,
        )

    def _get_stale_decisions(self, open_tasks: Sequence[Task]) -> list[Task]:
        """Return tasks that have been open for >= STALE_DAYS_THRESHOLD."""
        now = datetime.now()
        stale = []
        for t in open_tasks:
            if t.created_at is not None:
                age = (now - t.created_at).days
                if age >= STALE_DAYS_THRESHOLD:
                    stale.append(t)
        return sorted(stale, key=lambda t: t.created_at or now)
