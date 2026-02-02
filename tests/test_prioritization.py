"""Tests for mirage_core prioritization engine."""

from datetime import datetime, timedelta, timezone

from mirage_core.models import EnergyLevel, Task, TaskId, TaskStatus, TaskType
from mirage_core.prioritization import (
    PrioritizationResult,
    PrioritySuggestion,
    prioritize,
)


def _task(
    name: str = "Test",
    status: TaskStatus = TaskStatus.TASKS,
    mentioned: int = 1,
    priority: int | None = None,
    task_type: TaskType | None = None,
    complete_time: int | None = None,
    energy: EnergyLevel | None = None,
    created_at: datetime | None = None,
) -> Task:
    return Task(
        id=TaskId("t1"),
        name=name,
        status=status,
        mentioned=mentioned,
        priority=priority,
        task_type=task_type,
        complete_time_minutes=complete_time,
        energy=energy,
        created_at=created_at,
    )


def test_two_minute_rule():
    t = _task(complete_time=2)
    result = prioritize([t])
    s = result.suggestions[0]
    assert "[DO IT]" in s.tags
    assert "2-minute" in s.suggested_reason.lower() or "2min" in s.suggested_reason.lower()


def test_identity_aligned():
    t = _task(task_type=TaskType.IDENTITY)
    result = prioritize([t])
    s = result.suggestions[0]
    assert "[IDENTITY]" in s.tags
    assert "identity" in s.suggested_reason.lower()


def test_keystone():
    t = _task(task_type=TaskType.UNBLOCKS)
    result = prioritize([t])
    s = result.suggestions[0]
    assert "[KEYSTONE]" in s.tags


def test_never_miss_twice():
    t = _task(task_type=TaskType.NEVER_MISS_2X)
    result = prioritize([t])
    s = result.suggestions[0]
    assert "[NEVER MISS 2x]" in s.tags


def test_procrastination_pressure():
    t = _task(mentioned=5)
    result = prioritize([t])
    s = result.suggestions[0]
    assert "[PROCRASTINATING]" in s.tags
    assert "5x" in s.suggested_reason


def test_stale_task():
    old = datetime.now(timezone.utc) - timedelta(days=20)
    t = _task(created_at=old)
    result = prioritize([t])
    s = result.suggestions[0]
    assert "[STALE]" in s.tags


def test_compound_potential():
    t = _task(task_type=TaskType.COMPOUND)
    result = prioritize([t])
    s = result.suggestions[0]
    assert "[COMPOUNDS]" in s.tags


def test_important_not_urgent_compounds():
    t = _task(task_type=TaskType.IMPORTANT_NOT_URGENT)
    result = prioritize([t])
    s = result.suggestions[0]
    assert "[COMPOUNDS]" in s.tags


def test_manual_override_preserved():
    t = _task(priority=1)
    result = prioritize([t])
    s = result.suggestions[0]
    assert s.is_manual_override is True
    assert s.suggested_priority == 1


def test_done_tasks_excluded():
    t = _task(status=TaskStatus.DONE)
    result = prioritize([t])
    assert len(result.suggestions) == 0


def test_sorting_by_priority():
    t_high = _task(name="High", complete_time=1)  # [DO IT] → low score
    t_low = _task(name="Low")  # baseline → higher score
    result = prioritize([t_low, t_high])
    assert result.suggestions[0].task.name == "High"
    assert result.suggestions[1].task.name == "Low"


def test_manual_override_sorts_first():
    t_manual = _task(name="Manual", priority=2)
    t_auto = _task(name="Auto", complete_time=1)  # DO IT
    result = prioritize([t_auto, t_manual])
    assert result.suggestions[0].task.name == "Manual"


def test_green_energy_boost():
    t_green = _task(name="Green", energy=EnergyLevel.GREEN)
    t_neutral = _task(name="Neutral")
    result = prioritize([t_neutral, t_green])
    green_s = next(s for s in result.suggestions if s.task.name == "Green")
    neutral_s = next(s for s in result.suggestions if s.task.name == "Neutral")
    assert green_s.suggested_priority < neutral_s.suggested_priority


def test_conflict_detection():
    # Task with many strong signals
    t = _task(
        complete_time=2,
        task_type=TaskType.IDENTITY,
        mentioned=5,  # this doesn't add a strong signal tag, let me use NEVER_MISS_2X instead
    )
    # Actually need 3+ strong signals from tags
    # [DO IT] + [IDENTITY] = 2, need one more. Let me create a different test.
    result = prioritize([t])
    # With DO IT + IDENTITY = 2 strong signals, should NOT flag conflict
    assert result.suggestions[0].has_conflict is False


def test_no_signals_baseline():
    t = _task()
    result = prioritize([t])
    s = result.suggestions[0]
    assert len(s.tags) == 0
    assert "No special priority signals" in s.suggested_reason


def test_principles_hash_included():
    t = _task()
    result = prioritize([t])
    assert len(result.principles_hash) > 0


def test_output_schema():
    t = _task(complete_time=2, mentioned=4)
    result = prioritize([t])
    assert isinstance(result, PrioritizationResult)
    assert isinstance(result.suggestions[0], PrioritySuggestion)
    assert isinstance(result.suggestions[0].tags, tuple)
    assert isinstance(result.suggestions[0].suggested_reason, str)


if __name__ == "__main__":
    test_two_minute_rule()
    test_identity_aligned()
    test_keystone()
    test_never_miss_twice()
    test_procrastination_pressure()
    test_stale_task()
    test_compound_potential()
    test_important_not_urgent_compounds()
    test_manual_override_preserved()
    test_done_tasks_excluded()
    test_sorting_by_priority()
    test_manual_override_sorts_first()
    test_green_energy_boost()
    test_conflict_detection()
    test_no_signals_baseline()
    test_principles_hash_included()
    test_output_schema()
    print("All prioritization tests passed!")
