"""Schema smoke tests: validate alignment between tasks.yaml and models.

These tests run offline (no Notion API, no notion_client) and verify:
1. Enum values match canonical schema
2. All statuses, types, and energy levels are consistent
3. Schema property structure is well-formed
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mirage_core.models import (
    EnergyLevel,
    Task,
    TaskDraft,
    TaskId,
    TaskMutation,
    TaskStatus,
    TaskType,
)

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "tasks.yaml"


def _load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Enum alignment with schema
# ---------------------------------------------------------------------------

def test_task_status_matches_schema():
    schema = _load_schema()
    schema_statuses = set()
    for group in schema["properties"]["Status"]["groups"].values():
        schema_statuses.update(group)
    enum_statuses = {s.value for s in TaskStatus}
    assert schema_statuses == enum_statuses, (
        f"Drift: in schema but not enum={schema_statuses - enum_statuses}, "
        f"in enum but not schema={enum_statuses - schema_statuses}"
    )


def test_task_type_matches_schema():
    schema = _load_schema()
    schema_types = set(schema["properties"]["Type"]["options"])
    enum_types = {t.value for t in TaskType}
    assert schema_types == enum_types, (
        f"Drift: in schema but not enum={schema_types - enum_types}, "
        f"in enum but not schema={enum_types - schema_types}"
    )


def test_energy_level_matches_schema():
    schema = _load_schema()
    schema_energy = set(schema["properties"]["Energy"]["options"])
    enum_energy = {e.value for e in EnergyLevel}
    assert schema_energy == enum_energy


# ---------------------------------------------------------------------------
# Schema structure
# ---------------------------------------------------------------------------

def test_schema_has_required_keys():
    schema = _load_schema()
    assert "schema_version" in schema
    assert "database" in schema
    assert "properties" in schema
    assert "id" in schema["database"]
    assert "name" in schema["database"]


def test_schema_property_types():
    schema = _load_schema()
    valid_types = {"title", "status", "number", "rich_text", "select"}
    for name, spec in schema["properties"].items():
        assert "type" in spec, f"Property '{name}' missing 'type'"
        assert spec["type"] in valid_types, (
            f"Property '{name}' has unknown type '{spec['type']}'"
        )


def test_schema_has_name_and_status():
    schema = _load_schema()
    assert "Name" in schema["properties"]
    assert schema["properties"]["Name"]["type"] == "title"
    assert "Status" in schema["properties"]
    assert schema["properties"]["Status"]["type"] == "status"


def test_schema_status_groups_cover_all():
    """Every status in schema groups should be reachable."""
    schema = _load_schema()
    groups = schema["properties"]["Status"]["groups"]
    all_statuses = []
    for group_statuses in groups.values():
        all_statuses.extend(group_statuses)
    # No duplicates
    assert len(all_statuses) == len(set(all_statuses))
    # At least one in each lifecycle group
    assert "To-do" in groups
    assert "In progress" in groups
    assert "Complete" in groups


# ---------------------------------------------------------------------------
# Model roundtrip (in-memory, no Notion)
# ---------------------------------------------------------------------------

def test_task_draft_all_fields():
    """TaskDraft can represent all schema properties."""
    draft = TaskDraft(
        name="Full task",
        status=TaskStatus.BLOCKED,
        mentioned=3,
        blocked_by="Sarah",
        energy=EnergyLevel.RED,
        task_type=TaskType.IDENTITY,
        complete_time_minutes=30,
        priority=2,
    )
    assert draft.name == "Full task"
    assert draft.status == TaskStatus.BLOCKED
    assert draft.mentioned == 3
    assert draft.blocked_by == "Sarah"
    assert draft.energy == EnergyLevel.RED
    assert draft.task_type == TaskType.IDENTITY
    assert draft.complete_time_minutes == 30
    assert draft.priority == 2


def test_task_all_fields():
    """Task can represent all schema properties plus metadata."""
    task = Task(
        id=TaskId("abc123"),
        name="Full task",
        status=TaskStatus.WAITING_ON,
        mentioned=5,
        blocked_by="Design team",
        energy=EnergyLevel.YELLOW,
        task_type=TaskType.UNBLOCKS,
        complete_time_minutes=60,
        priority=1,
    )
    assert task.id.value == "abc123"
    assert task.status == TaskStatus.WAITING_ON
    assert task.energy == EnergyLevel.YELLOW
    assert task.task_type == TaskType.UNBLOCKS


def test_mutation_all_fields():
    """TaskMutation can update every mutable property."""
    mutation = TaskMutation(
        task_id=TaskId("abc"),
        name="Updated",
        status=TaskStatus.DONE,
        mentioned=5,
        blocked_by="resolved",
        energy=EnergyLevel.GREEN,
        task_type=TaskType.COMPOUND,
        complete_time_minutes=15,
        priority=1,
    )
    assert mutation.name == "Updated"
    assert mutation.status == TaskStatus.DONE
    assert mutation.energy == EnergyLevel.GREEN


def test_every_status_constructs():
    """Every TaskStatus value creates a valid Task."""
    for status in TaskStatus:
        task = Task(
            id=TaskId("t1"), name=f"Test {status.value}", status=status
        )
        assert task.status == status


def test_every_type_constructs():
    """Every TaskType value creates a valid TaskDraft."""
    for task_type in TaskType:
        draft = TaskDraft(
            name=f"Test {task_type.value}",
            status=TaskStatus.TASKS,
            task_type=task_type,
        )
        assert draft.task_type == task_type


def test_every_energy_constructs():
    """Every EnergyLevel value creates a valid Task."""
    for energy in EnergyLevel:
        task = Task(
            id=TaskId("t1"),
            name=f"Test {energy.value}",
            status=TaskStatus.TASKS,
            energy=energy,
        )
        assert task.energy == energy


# ---------------------------------------------------------------------------
# Status aliases
# ---------------------------------------------------------------------------

def test_schema_aliases_map_to_valid_statuses():
    schema = _load_schema()
    aliases = schema.get("status_aliases", {})
    schema_statuses = set()
    for group in schema["properties"]["Status"]["groups"].values():
        schema_statuses.update(group)

    for alias, target in aliases.items():
        assert target in schema_statuses, (
            f"Alias '{alias}' maps to '{target}' which is not a valid status"
        )


def test_aliases_match_core():
    """status_aliases in schema align with mirage_core.aliases."""
    from mirage_core.aliases import STATUS_ALIASES

    schema = _load_schema()
    schema_aliases = schema.get("status_aliases", {})

    for alias, target in schema_aliases.items():
        if alias in STATUS_ALIASES:
            assert STATUS_ALIASES[alias].value == target, (
                f"Alias '{alias}': schema says '{target}', "
                f"core says '{STATUS_ALIASES[alias].value}'"
            )
