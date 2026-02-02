"""Notion-backed repositories for Mirage core."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional, Sequence

from notion_client import Client

from ..errors import DependencyError, ValidationError
from ..models import (
    EnergyLevel,
    Review,
    ReviewId,
    Task,
    TaskDraft,
    TaskId,
    TaskMutation,
    TaskStatus,
    TaskType,
)
from ..ports import TaskRepository
from ..ports import ReviewRepository


class NotionTaskRepository(TaskRepository):
    """Task repository backed by the Mirage Notion database."""

    def __init__(self, client: Client, database_id: str) -> None:
        self._client = client
        self._database_id = database_id

    @classmethod
    def from_env(cls, database_id: str) -> "NotionTaskRepository":
        token = _get_notion_token()
        return cls(Client(auth=token), database_id)

    async def query(
        self,
        *,
        status: Optional[TaskStatus] = None,
        exclude_done: bool = False,
    ) -> Sequence[Task]:
        filter_obj = None
        if status is not None:
            filter_obj = {
                "property": "Status",
                "status": {"equals": status.value},
            }
        elif exclude_done:
            filter_obj = {
                "and": [
                    {"property": "Status", "status": {"does_not_equal": "Done"}},
                    {"property": "Status", "status": {"does_not_equal": "Won't Do"}},
                ]
            }

        def _run_query() -> dict:
            query_args = {"database_id": self._database_id}
            if filter_obj:
                query_args["filter"] = filter_obj
            return self._client.databases.query(**query_args)

        response = await asyncio.to_thread(_run_query)
        return [_task_from_page(page) for page in response.get("results", [])]

    async def get(self, task_id: TaskId) -> Optional[Task]:
        def _run_get() -> dict:
            return self._client.pages.retrieve(page_id=task_id.value)

        try:
            page = await asyncio.to_thread(_run_get)
        except Exception:
            return None

        return _task_from_page(page)

    async def create(self, task: TaskDraft) -> Task:
        properties = _properties_from_task_draft(task)

        def _run_create() -> dict:
            return self._client.pages.create(
                parent={"database_id": self._database_id},
                properties=properties,
            )

        page = await asyncio.to_thread(_run_create)
        return _task_from_page(page)

    async def update(self, mutation: TaskMutation) -> Task:
        properties = _properties_from_mutation(mutation)
        if not properties:
            raise ValidationError("TaskMutation has no fields to update")

        def _run_update() -> dict:
            return self._client.pages.update(
                page_id=mutation.task_id.value,
                properties=properties,
            )

        page = await asyncio.to_thread(_run_update)
        return _task_from_page(page)

    async def increment_mentioned(self, task_id: TaskId) -> int:
        def _run_get() -> dict:
            return self._client.pages.retrieve(page_id=task_id.value)

        page = await asyncio.to_thread(_run_get)
        props = page.get("properties", {})
        current_count = _extract_number(props, "Mentioned") or 0
        new_count = current_count + 1

        def _run_update() -> dict:
            return self._client.pages.update(
                page_id=task_id.value,
                properties={"Mentioned": {"number": new_count}},
            )

        await asyncio.to_thread(_run_update)
        return new_count


class NotionReviewRepository(ReviewRepository):
    """Review repository backed by the Mirage Notion database."""

    def __init__(self, client: Client, database_id: str) -> None:
        self._client = client
        self._database_id = database_id

    @classmethod
    def from_env(cls, database_id: str) -> "NotionReviewRepository":
        token = _get_notion_token()
        return cls(Client(auth=token), database_id)

    async def create(self, review: Review) -> Review:
        properties = _properties_from_review(review)

        def _run_create() -> dict:
            return self._client.pages.create(
                parent={"database_id": self._database_id},
                properties=properties,
            )

        page = await asyncio.to_thread(_run_create)
        return Review(
            id=ReviewId(page.get("id", "")),
            week_of=review.week_of,
            transcript=review.transcript,
            wins=review.wins,
            struggles=review.struggles,
            next_week_focus=review.next_week_focus,
            tasks_completed=review.tasks_completed,
            url=page.get("url"),
        )


def _get_notion_token() -> str:
    token = _get_env("NOTION_TOKEN") or _get_env("NOTION_API_KEY")
    if not token:
        raise DependencyError("NOTION_TOKEN or NOTION_API_KEY must be set")
    return token


def _get_env(key: str) -> Optional[str]:
    import os

    value = os.environ.get(key)
    return value if value and value.strip() else None


def _task_from_page(page: dict) -> Task:
    props = page.get("properties", {})
    status_name = _extract_status(props, "Status")
    try:
        status = TaskStatus(status_name)
    except ValueError as exc:
        raise ValidationError(f"Unknown status '{status_name}'") from exc

    energy_name = _extract_select(props, "Energy")
    energy = None
    if energy_name:
        try:
            energy = EnergyLevel(energy_name)
        except ValueError as exc:
            raise ValidationError(f"Unknown energy '{energy_name}'") from exc

    type_name = _extract_select(props, "Type")
    task_type = None
    if type_name:
        try:
            task_type = TaskType(type_name)
        except ValueError:
            task_type = None

    return Task(
        id=TaskId(page.get("id", "")),
        name=_extract_title(props),
        status=status,
        mentioned=_extract_number(props, "Mentioned") or 1,
        blocked_by=_extract_text(props, "Blocked") or None,
        energy=energy,
        task_type=task_type,
        complete_time_minutes=_extract_number(props, "Complete Time"),
        priority=_extract_number(props, "Priority"),
        created_at=_parse_time(page.get("created_time")),
        updated_at=_parse_time(page.get("last_edited_time")),
        url=page.get("url"),
    )


def _properties_from_task_draft(task: TaskDraft) -> dict:
    properties = {
        "Name": {"title": [{"text": {"content": task.name}}]},
        "Status": {"status": {"name": task.status.value}},
        "Mentioned": {"number": task.mentioned},
    }

    if task.blocked_by:
        properties["Blocked"] = {"rich_text": [{"text": {"content": task.blocked_by}}]}

    if task.energy:
        properties["Energy"] = {"select": {"name": task.energy.value}}

    if task.task_type:
        properties["Type"] = {"select": {"name": task.task_type.value}}

    if task.complete_time_minutes is not None:
        properties["Complete Time"] = {"number": task.complete_time_minutes}

    if task.priority is not None:
        properties["Priority"] = {"number": task.priority}

    return properties


def _properties_from_mutation(mutation: TaskMutation) -> dict:
    properties: dict[str, dict] = {}

    if mutation.name is not None:
        properties["Name"] = {"title": [{"text": {"content": mutation.name}}]}

    if mutation.status is not None:
        properties["Status"] = {"status": {"name": mutation.status.value}}

    if mutation.mentioned is not None:
        properties["Mentioned"] = {"number": mutation.mentioned}

    if mutation.blocked_by is not None:
        properties["Blocked"] = {
            "rich_text": [{"text": {"content": mutation.blocked_by}}]
        }

    if mutation.energy is not None:
        properties["Energy"] = {"select": {"name": mutation.energy.value}}

    if mutation.task_type is not None:
        properties["Type"] = {"select": {"name": mutation.task_type.value}}

    if mutation.complete_time_minutes is not None:
        properties["Complete Time"] = {"number": mutation.complete_time_minutes}

    if mutation.priority is not None:
        properties["Priority"] = {"number": mutation.priority}

    return properties


def _properties_from_review(review: Review) -> dict:
    week_of = review.week_of.strftime("%Y-%m-%d")
    transcript = _truncate_text(review.transcript, 2000)

    properties = {
        "Name": {"title": [{"text": {"content": f"Week of {week_of}"}}]},
        "Transcript": {"rich_text": [{"text": {"content": transcript}}]},
    }

    if review.wins:
        properties["Wins"] = {"rich_text": [{"text": {"content": review.wins}}]}

    if review.struggles:
        properties["Struggles"] = {"rich_text": [{"text": {"content": review.struggles}}]}

    if review.next_week_focus:
        properties["Next Week Focus"] = {
            "rich_text": [{"text": {"content": review.next_week_focus}}]
        }

    if review.tasks_completed is not None:
        properties["Tasks Completed"] = {"number": review.tasks_completed}

    return properties


def _extract_title(props: dict) -> str:
    for value in props.values():
        if value.get("type") == "title":
            title_list = value.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_list)
    return "Untitled"


def _extract_select(props: dict, prop_name: str) -> str:
    if prop_name in props:
        select = props[prop_name].get("select")
        if select:
            return select.get("name", "")
    return ""


def _extract_status(props: dict, prop_name: str) -> str:
    if prop_name in props:
        status = props[prop_name].get("status")
        if status:
            return status.get("name", "")
    return ""


def _extract_number(props: dict, prop_name: str) -> Optional[int]:
    if prop_name in props:
        return props[prop_name].get("number")
    return None


def _extract_text(props: dict, prop_name: str) -> str:
    if prop_name in props:
        rich_text = props[prop_name].get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in rich_text)
    return ""


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _truncate_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[:max_len]
