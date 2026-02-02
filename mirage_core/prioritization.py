"""Prioritization engine: layered priority rules and suggestion generation.

Applies Atomic Habits decision filters to score and rank tasks.
Produces a suggested priority and a human-readable reason for each task.

Layers (applied in order):
1. Manual override — if priority is set, preserve it
2. Deterministic rules — identity, keystone, 2-minute, never-miss-twice
3. Procrastination pressure — mentioned >= 3 or stale >= 14 days
4. Compound potential tagging
5. Suggested priority score generation
6. Suggested reason text

For ties or conflicting signals, the engine flags them for LLM-assisted
resolution rather than auto-deciding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from .models import EnergyLevel, Task, TaskStatus, TaskType
from .principles import PrinciplesIndex, ThinkingMode, get_principles

PROCRASTINATION_THRESHOLD = 3
STALE_DAYS_THRESHOLD = 14
TWO_MINUTE_THRESHOLD = 2


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PrioritySuggestion:
    """Prioritization output for a single task."""

    task: Task
    suggested_priority: int
    suggested_reason: str
    tags: tuple[str, ...] = ()
    is_manual_override: bool = False
    has_conflict: bool = False


@dataclass(frozen=True)
class PrioritizationResult:
    """Full output from the prioritization engine."""

    suggestions: tuple[PrioritySuggestion, ...]
    principles_hash: str


# ---------------------------------------------------------------------------
# Deterministic rules
# ---------------------------------------------------------------------------

def _is_two_minute(task: Task) -> bool:
    """Task can be done in 2 minutes or less."""
    return (
        task.complete_time_minutes is not None
        and task.complete_time_minutes <= TWO_MINUTE_THRESHOLD
    )


def _is_identity_aligned(task: Task) -> bool:
    """Task is tagged as Identity."""
    return task.task_type == TaskType.IDENTITY


def _is_keystone(task: Task) -> bool:
    """Task is tagged as Unblocks (upstream/keystone habit)."""
    return task.task_type == TaskType.UNBLOCKS


def _is_never_miss_twice(task: Task) -> bool:
    """Task is tagged as Never Miss 2x."""
    return task.task_type == TaskType.NEVER_MISS_2X


def _is_procrastinating(task: Task) -> bool:
    """Task has been mentioned >= threshold times."""
    return task.mentioned >= PROCRASTINATION_THRESHOLD


def _is_stale(task: Task, now: Optional[datetime] = None) -> bool:
    """Task hasn't been touched in >= 14 days."""
    if task.created_at is None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    if task.created_at.tzinfo is None:
        created = task.created_at.replace(tzinfo=timezone.utc)
    else:
        created = task.created_at
    return (now - created) >= timedelta(days=STALE_DAYS_THRESHOLD)


def _has_compound_potential(task: Task) -> bool:
    """Task is tagged as Compound or Important Not Urgent."""
    return task.task_type in (TaskType.COMPOUND, TaskType.IMPORTANT_NOT_URGENT)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _compute_score(task: Task, now: Optional[datetime] = None) -> tuple[int, list[str], list[str]]:
    """Compute a priority score and collect tags + reasons.

    Lower score = higher priority. Returns (score, tags, reasons).
    """
    score = 50  # baseline
    tags: list[str] = []
    reasons: list[str] = []

    # 2-minute rule: highest priority
    if _is_two_minute(task):
        score -= 30
        tags.append("[DO IT]")
        reasons.append(f"Takes {task.complete_time_minutes}min — do it now (2-minute rule)")

    # Never miss twice
    if _is_never_miss_twice(task):
        score -= 25
        tags.append("[NEVER MISS 2x]")
        reasons.append("Skipped recently — never miss twice")

    # Identity alignment
    if _is_identity_aligned(task):
        score -= 20
        tags.append("[IDENTITY]")
        reasons.append("Aligns with identity goals")

    # Keystone / unblocks
    if _is_keystone(task):
        score -= 20
        tags.append("[KEYSTONE]")
        reasons.append("Upstream habit — unlocks other tasks")

    # Procrastination pressure
    if _is_procrastinating(task):
        score -= 15
        tags.append("[PROCRASTINATING]")
        reasons.append(f"Mentioned {task.mentioned}x — friction analysis needed")

    # Stale
    if _is_stale(task, now):
        score -= 10
        tags.append("[STALE]")
        reasons.append("Created 14+ days ago without progress")

    # Compound potential
    if _has_compound_potential(task):
        score -= 10
        tags.append("[COMPOUNDS]")
        reasons.append("Builds over time — 1% better")

    # Explicit priority gets a boost proportional to its value
    if task.priority is not None:
        score -= max(0, 30 - task.priority * 3)

    # Energy: Green tasks get a small boost (easy wins)
    if task.energy == EnergyLevel.GREEN:
        score -= 5
        reasons.append("Low energy — good for a quick win")

    return max(1, score), tags, reasons


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def prioritize(
    tasks: Sequence[Task],
    *,
    now: Optional[datetime] = None,
    principles: Optional[PrinciplesIndex] = None,
) -> PrioritizationResult:
    """Run the full prioritization engine on a set of tasks.

    Returns PrioritizationResult with suggestions sorted by priority (best first).
    """
    if principles is None:
        principles = get_principles()

    suggestions: list[PrioritySuggestion] = []

    for task in tasks:
        # Skip non-actionable statuses
        if task.status in (TaskStatus.DONE, TaskStatus.WONT_DO):
            continue

        # Manual override — preserve existing priority and reason
        if task.priority is not None and task.priority > 0:
            score, tags, reasons = _compute_score(task, now)
            suggestions.append(
                PrioritySuggestion(
                    task=task,
                    suggested_priority=task.priority,
                    suggested_reason=_format_reason(reasons) if reasons else "Manual priority set",
                    tags=tuple(tags),
                    is_manual_override=True,
                    has_conflict=False,
                )
            )
            continue

        # Compute score
        score, tags, reasons = _compute_score(task, now)

        # Detect conflicts: multiple strong competing signals
        strong_signals = sum(1 for t in tags if t in ("[DO IT]", "[NEVER MISS 2x]", "[IDENTITY]", "[KEYSTONE]"))
        has_conflict = strong_signals >= 3

        suggestions.append(
            PrioritySuggestion(
                task=task,
                suggested_priority=score,
                suggested_reason=_format_reason(reasons),
                tags=tuple(tags),
                is_manual_override=False,
                has_conflict=has_conflict,
            )
        )

    # Sort by suggested_priority ascending (lower = more important)
    suggestions.sort(key=lambda s: (not s.is_manual_override, s.suggested_priority))

    return PrioritizationResult(
        suggestions=tuple(suggestions),
        principles_hash=principles.content_hash,
    )


def _format_reason(reasons: list[str]) -> str:
    """Join reason fragments into a 1-2 sentence rationale."""
    if not reasons:
        return "No special priority signals detected"
    if len(reasons) == 1:
        return reasons[0]
    return ". ".join(reasons[:3])
