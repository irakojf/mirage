"""
Notion database operations for Mirage Slack bot.

Uses Mirage core repositories when available so Slack capture flows share
one canonical persistence layer. Falls back to direct Notion API calls
when mirage_core isn't available in the runtime environment.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

_CORE_AVAILABLE = False
_CORE_IMPORT_ERROR: Optional[Exception] = None

try:
    from mirage_core.adapters.notion_repo import NotionTaskRepository
    from mirage_core.config import MirageConfig
    from mirage_core.models import TaskId
    from mirage_core.services import TaskCaptureService

    _CORE_AVAILABLE = True
except Exception as exc:
    _CORE_IMPORT_ERROR = exc

if not _CORE_AVAILABLE:
    from notion_client import Client


NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
# Fallback default comes from MirageConfig when core is available;
# hardcoded only for the degraded (no mirage_core) path.
_DEFAULT_TASKS_DB = (
    MirageConfig.tasks_database_id if _CORE_AVAILABLE else "2ea35d23-b569-80cc-99be-e6d6a17b1548"
)
TASKS_DATABASE_ID = os.environ.get("MIRAGE_TASKS_DB", _DEFAULT_TASKS_DB)

_TAG_MAP = {
    "[DO IT]": "Do It Now",
    "[KEYSTONE]": "Unblocks",
    "[COMPOUNDS]": "Compound",
    "[IDENTITY]": "Identity",
}
_TAG_MAP_UPPER = {key.upper(): value for key, value in _TAG_MAP.items()}
_CANONICAL_TAGS = {
    "Identity",
    "Compound",
    "Do It Now",
    "Never Miss 2x",
    "Important Not Urgent",
    "Unblocks",
}


# ── Mirage core helpers ─────────────────────────────────────────────────────


def _run(coro):
    return asyncio.run(coro)


def _get_task_repo() -> "NotionTaskRepository":
    config = MirageConfig.from_env()
    config.validate()
    return NotionTaskRepository.from_env(config.tasks_database_id)


def _get_capture_service() -> "TaskCaptureService":
    return TaskCaptureService(_get_task_repo())


def _normalize_tag(tags: Optional[list[str]]) -> Optional[str]:
    if not tags:
        return None
    raw = tags[0].strip()
    if not raw:
        return None
    if raw in _CANONICAL_TAGS:
        return raw
    mapped = _TAG_MAP_UPPER.get(raw.upper())
    return mapped


def _task_to_payload(task, *, mentioned_override: Optional[int] = None) -> dict:
    return {
        "id": task.id.value,
        "content": task.name,
        "status": task.status.value,
        "estimated_minutes": task.complete_time_minutes,
        "times_added": mentioned_override if mentioned_override is not None else task.mentioned,
        "notes": None,
        "url": task.url,
    }


# ── Public API ──────────────────────────────────────────────────────────────


def get_notion_client():
    """Get authenticated Notion client (fallback mode only)."""
    if not NOTION_TOKEN:
        raise ValueError("NOTION_TOKEN environment variable not set")
    return Client(auth=NOTION_TOKEN)


def create_task(
    content: str,
    status: str,
    estimated_minutes: Optional[int] = None,
    notes: Optional[str] = None,
    blocked_by: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """Create a new task in Notion via mirage_core when available."""
    if _CORE_AVAILABLE:
        capture = _get_capture_service()
        tag = _normalize_tag(tags)
        task = _run(
            capture.capture(
                content,
                status,
                blocked_by=blocked_by,
                tag=tag,
                complete_time=estimated_minutes,
            )
        )
        payload = _task_to_payload(task)
        payload["notes"] = notes
        return payload

    notion = get_notion_client()

    STATUS_MAP = {
        "action": "Tasks",
        "Action": "Tasks",
        "project": "Projects",
        "Project": "Projects",
        "idea": "Ideas",
        "Idea": "Ideas",
        "blocked": "Blocked",
        "Blocked": "Blocked",
        "Tasks": "Tasks",
        "Projects": "Projects",
        "Ideas": "Ideas",
        "Not Now": "Not Now",
        "Waiting On": "Waiting On",
        "Won't Do": "Won't Do",
        "Done": "Done",
    }
    notion_status = STATUS_MAP.get(status, status)

    properties = {
        "Name": {"title": [{"text": {"content": content}}]},
        "Status": {"status": {"name": notion_status}},
        "Mentioned": {"number": 1},
    }

    if blocked_by:
        properties["Blocked"] = {"rich_text": [{"text": {"content": blocked_by}}]}

    if tags and len(tags) > 0:
        properties["Type"] = {"select": {"name": tags[0]}}

    if estimated_minutes is not None:
        properties["Complete Time"] = {"number": estimated_minutes}

    page = notion.pages.create(
        parent={"database_id": TASKS_DATABASE_ID},
        properties=properties,
    )

    return {
        "id": page["id"],
        "content": content,
        "status": notion_status,
        "estimated_minutes": estimated_minutes,
        "times_added": 1,
        "notes": notes,
        "url": page.get("url"),
    }


def get_open_tasks() -> list[dict]:
    """Get all open tasks for semantic matching."""
    if _CORE_AVAILABLE:
        repo = _get_task_repo()
        tasks = _run(repo.query(exclude_done=True))
        return [
            {
                "id": task.id.value,
                "content": task.name,
                "status": task.status.value,
                "times_added": task.mentioned,
            }
            for task in tasks
        ]

    notion = get_notion_client()

    response = notion.databases.query(
        database_id=TASKS_DATABASE_ID,
        filter={"property": "Status", "status": {"does_not_equal": "Done"}},
    )

    tasks = []
    for page in response.get("results", []):
        props = page.get("properties", {})
        tasks.append(
            {
                "id": page["id"],
                "content": _extract_title(props),
                "status": _extract_status(props, "Status"),
                "times_added": _extract_number(props, "Mentioned") or 1,
            }
        )

    return tasks


def increment_task_mentions(page_id: str) -> Optional[dict]:
    """Increment the Mentioned count for an existing task."""
    if _CORE_AVAILABLE:
        repo = _get_task_repo()
        capture = TaskCaptureService(repo)
        new_count = _run(capture.increment_mention(page_id))
        task = _run(repo.get(TaskId(page_id)))
        if not task:
            return None
        return {
            "id": page_id,
            "content": task.name,
            "status": task.status.value,
            "times_added": new_count,
        }

    notion = get_notion_client()

    try:
        page = notion.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})
        current_count = _extract_number(props, "Mentioned") or 0

        new_count = current_count + 1
        notion.pages.update(
            page_id=page_id,
            properties={"Mentioned": {"number": new_count}},
        )

        return {
            "id": page_id,
            "content": _extract_title(props),
            "status": _extract_status(props, "Status"),
            "times_added": new_count,
        }

    except Exception:
        return None


def find_task_by_id(page_id: str) -> Optional[dict]:
    """Fetch a single task by page ID."""
    if _CORE_AVAILABLE:
        repo = _get_task_repo()
        task = _run(repo.get(TaskId(page_id)))
        if not task:
            return None
        return {
            "id": task.id.value,
            "content": task.name,
            "status": task.status.value,
            "times_added": task.mentioned,
            "blocked_by": task.blocked_by,
            "energy": task.energy.value if task.energy else None,
            "tag": task.task_type.value if task.task_type else None,
        }

    notion = get_notion_client()

    try:
        page = notion.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})

        return {
            "id": page["id"],
            "content": _extract_title(props),
            "status": _extract_status(props, "Status"),
            "times_added": _extract_number(props, "Mentioned") or 1,
            "blocked_by": _extract_text(props, "Blocked"),
            "energy": _extract_select(props, "Energy"),
            "tag": _extract_select(props, "Type"),
        }

    except Exception:
        return None


# ==========================================================================
# Helper functions for extracting Notion properties (fallback mode only)
# ==========================================================================


def _extract_title(props: dict) -> str:
    """Extract title from properties."""
    for key, value in props.items():
        if value.get("type") == "title":
            title_list = value.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_list)
    return "Untitled"


def _extract_select(props: dict, prop_name: str) -> str:
    """Extract select property value."""
    if prop_name in props:
        select = props[prop_name].get("select")
        if select:
            return select.get("name", "")
    return ""


def _extract_status(props: dict, prop_name: str) -> str:
    """Extract status property value (different from select)."""
    if prop_name in props:
        status = props[prop_name].get("status")
        if status:
            return status.get("name", "")
    return ""


def _extract_number(props: dict, prop_name: str) -> Optional[int]:
    """Extract number property value."""
    if prop_name in props:
        return props[prop_name].get("number")
    return None


def _extract_text(props: dict, prop_name: str) -> str:
    """Extract rich_text property as plain text."""
    if prop_name in props:
        rich_text = props[prop_name].get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in rich_text)
    return ""


def _extract_multi_select(props: dict, prop_name: str) -> list[str]:
    """Extract multi_select property values."""
    if prop_name in props:
        options = props[prop_name].get("multi_select", [])
        return [opt.get("name", "") for opt in options]
    return []
