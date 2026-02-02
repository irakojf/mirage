"""Smoke tests for Slack bot command routing and formatting.

Tests the pure functions in mcp/slack/server.py without requiring
Slack or Notion API connections.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add mcp/slack to path so we can import server helpers
SLACK_DIR = Path(__file__).parent.parent / "mcp" / "slack"
sys.path.insert(0, str(SLACK_DIR))

# Mock external dependencies before importing server module
sys.modules.setdefault("slack_bolt", MagicMock())
sys.modules.setdefault("slack_bolt.adapter.flask", MagicMock())
sys.modules.setdefault("anthropic", MagicMock())
sys.modules.setdefault("notion_db", MagicMock())
sys.modules.setdefault("notion_client", MagicMock())

from mirage_core.config import MirageConfig
from mirage_core.models import Task, TaskId, TaskStatus, TaskType, EnergyLevel
from mirage_core.prioritization import PrioritizationResult, PrioritySuggestion, prioritize


# ---------------------------------------------------------------------------
# Import server helpers (after mocking)
# ---------------------------------------------------------------------------

from task_processor import format_slack_response, detect_intent


# Import server formatting functions
# We need to import these carefully since server.py has side effects
import importlib
_server_spec = importlib.util.spec_from_file_location("server", SLACK_DIR / "server.py")
_server_mod = importlib.util.module_from_spec(_server_spec)

# We can't fully import server.py due to Flask/Slack deps, so test
# the functions via their implementations directly.


# ---------------------------------------------------------------------------
# format_slack_response
# ---------------------------------------------------------------------------

def test_format_new_task():
    task = {
        "content": "Call mom",
        "bucket": "action",
        "estimated_minutes": 5,
        "tags": ["[DO IT]"],
    }
    result = format_slack_response(task, is_new=True)
    assert "Got it!" in result
    assert "Call mom" in result
    assert "5 min" in result
    assert "[DO IT]" in result


def test_format_new_task_no_tags():
    task = {
        "content": "Write report",
        "bucket": "project",
        "estimated_minutes": None,
        "tags": [],
    }
    result = format_slack_response(task, is_new=True)
    assert "Got it!" in result
    assert "Write report" in result
    assert "[DO IT]" not in result


def test_format_duplicate_task():
    task = {
        "content": "Call mom",
        "times_added": 2,
    }
    result = format_slack_response(task, is_new=False)
    assert "Already tracking" in result
    assert "mentioned 2x" in result


def test_format_duplicate_procrastination():
    task = {
        "content": "Call mom",
        "times_added": 4,
    }
    result = format_slack_response(task, is_new=False)
    assert "procrastination" in result.lower()


def test_format_with_status():
    task = {
        "content": "Test task",
        "status": "Tasks",
        "bucket": "action",
        "estimated_minutes": 10,
        "tags": [],
    }
    result = format_slack_response(task, is_new=True)
    assert "Tasks" in result


# ---------------------------------------------------------------------------
# detect_intent
# ---------------------------------------------------------------------------

def test_detect_greeting():
    assert detect_intent("hello") == "greeting"
    assert detect_intent("Hey") == "greeting"
    assert detect_intent("hi") == "greeting"


def test_detect_question():
    assert detect_intent("what should I focus on?") == "question"
    assert detect_intent("help me prioritize") == "question"
    assert detect_intent("which task is most important?") == "question"


def test_detect_task():
    assert detect_intent("call mom tomorrow") == "task"
    assert detect_intent("finish quarterly report") == "task"
    assert detect_intent("buy groceries") == "task"


# ---------------------------------------------------------------------------
# Priority formatting (mirrors server._format_priorities)
# ---------------------------------------------------------------------------

def _task(name: str, **kwargs) -> Task:
    defaults = {"id": TaskId("t1"), "status": TaskStatus.TASKS, "mentioned": 1}
    defaults.update(kwargs)
    return Task(name=name, **defaults)


def test_prioritize_produces_suggestions():
    tasks = [
        _task("Quick task", complete_time_minutes=2),
        _task("Big task", complete_time_minutes=120),
    ]
    result = prioritize(tasks)
    assert len(result.suggestions) == 2
    # Quick task should rank higher (DO IT rule)
    assert result.suggestions[0].task.name == "Quick task"


def test_prioritize_empty_list():
    result = prioritize([])
    assert len(result.suggestions) == 0


# ---------------------------------------------------------------------------
# Day plan building (mirrors server._build_day_plan logic)
# ---------------------------------------------------------------------------

def _minutes_from_hhmm(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def test_day_plan_capacity():
    cfg = MirageConfig()
    work_minutes = _minutes_from_hhmm(cfg.work_end) - _minutes_from_hhmm(cfg.work_start)
    assert work_minutes == 540  # 9 hours


def test_day_plan_buffer():
    cfg = MirageConfig()
    assert cfg.buffer_minutes == 15
