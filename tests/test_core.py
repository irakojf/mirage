"""Unit tests for mirage_core business logic."""

import pytest

from mirage_core import (
    PROCRASTINATION_THRESHOLD,
    TaskId,
    TaskStatus,
    TaskType,
    Task,
    TaskMutation,
    ValidationError,
    resolve_status,
    resolve_type,
    normalize_task_name,
    sort_by_priority,
    filter_actionable,
    flag_procrastinating,
)
from mirage_core.config import MirageConfig


def _task(name, **kwargs):
    defaults = dict(id=TaskId("test"), status=TaskStatus.TASKS, mentioned=1)
    defaults.update(kwargs)
    return Task(name=name, **defaults)


class TestResolveStatus:
    def test_canonical(self):
        assert resolve_status("Tasks") == TaskStatus.TASKS

    def test_alias(self):
        assert resolve_status("Action") == TaskStatus.TASKS

    def test_lowercase(self):
        assert resolve_status("project") == TaskStatus.PROJECTS

    def test_all_statuses(self):
        for s in TaskStatus:
            assert resolve_status(s.value) == s

    def test_unknown(self):
        with pytest.raises(ValueError):
            resolve_status("Nonexistent")


class TestResolveType:
    def test_canonical(self):
        assert resolve_type("Identity") == TaskType.IDENTITY

    def test_alias(self):
        assert resolve_type("Compounds") == TaskType.COMPOUND

    def test_unknown(self):
        with pytest.raises(ValueError):
            resolve_type("Nonexistent")


class TestTaskValidation:
    def test_empty_name(self):
        with pytest.raises(ValidationError):
            Task(id=TaskId("x"), name="  ", status=TaskStatus.TASKS)

    def test_negative_mentioned(self):
        with pytest.raises(ValidationError):
            Task(id=TaskId("x"), name="ok", status=TaskStatus.TASKS, mentioned=-1)

    def test_zero_complete_time(self):
        with pytest.raises(ValidationError):
            Task(id=TaskId("x"), name="ok", status=TaskStatus.TASKS, complete_time_minutes=0)

    def test_zero_priority(self):
        with pytest.raises(ValidationError):
            Task(id=TaskId("x"), name="ok", status=TaskStatus.TASKS, priority=0)

    def test_valid(self):
        t = _task("Buy groceries", priority=1, complete_time_minutes=30)
        assert t.name == "Buy groceries"


class TestTaskId:
    def test_empty(self):
        with pytest.raises(ValidationError):
            TaskId("")

    def test_whitespace(self):
        with pytest.raises(ValidationError):
            TaskId("   ")


class TestNormalize:
    def test_strip(self):
        assert normalize_task_name("  hello  ") == "hello"

    def test_bullet(self):
        assert normalize_task_name("- buy milk") == "buy milk"

    def test_collapse(self):
        assert normalize_task_name("buy   some   milk") == "buy some milk"


class TestSortByPriority:
    def test_explicit_first(self):
        t1 = _task("low", priority=5)
        t2 = _task("high", priority=1)
        t3 = _task("none")
        result = sort_by_priority([t1, t3, t2])
        assert result[0].name == "high"
        assert result[1].name == "low"
        assert result[2].name == "none"

    def test_mentioned_tiebreaker(self):
        t1 = _task("less", mentioned=1)
        t2 = _task("more", mentioned=5)
        result = sort_by_priority([t1, t2])
        assert result[0].name == "more"


class TestFilterActionable:
    def test_only_tasks(self):
        tasks = [
            _task("a", status=TaskStatus.TASKS),
            _task("b", status=TaskStatus.PROJECTS),
            _task("c", status=TaskStatus.BLOCKED),
        ]
        assert len(filter_actionable(tasks)) == 1


class TestFlagProcrastinating:
    def test_threshold(self):
        tasks = [
            _task("ok", mentioned=2),
            _task("proc", mentioned=PROCRASTINATION_THRESHOLD),
            _task("very", mentioned=10),
        ]
        assert len(flag_procrastinating(tasks)) == 2


class TestConfig:
    def test_defaults(self):
        cfg = MirageConfig()
        assert cfg.tasks_database_id == "2ea35d23-b569-80cc-99be-e6d6a17b1548"

    def test_validate_missing_token(self):
        cfg = MirageConfig(notion_token="")
        with pytest.raises(Exception):
            cfg.validate()

    def test_validate_ok(self):
        cfg = MirageConfig(notion_token="secret_abc")
        cfg.validate()
