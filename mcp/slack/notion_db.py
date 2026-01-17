"""
Notion database operations for Mirage Slack bot.

Uses Notion API directly (not MCP) since Slack bot runs independently on fly.io.
Mirrors the db.py interface for task operations.
"""

import os
from typing import Optional
from notion_client import Client


# Configuration
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
TASKS_DATABASE_ID = "2ea35d23-b569-80cc-99be-e6d6a17b1548"


def get_notion_client() -> Client:
    """Get authenticated Notion client."""
    if not NOTION_TOKEN:
        raise ValueError("NOTION_TOKEN environment variable not set")
    return Client(auth=NOTION_TOKEN)


def create_task(
    content: str,
    status: str,
    estimated_minutes: Optional[int] = None,
    notes: Optional[str] = None,
    blocked_by: Optional[str] = None,
    tags: Optional[list[str]] = None
) -> dict:
    """
    Create a new task in the Notion database.

    Args:
        content: Task description
        status: Action/Tasks, Project/Projects, Idea/Ideas, or Blocked
        estimated_minutes: Time estimate in minutes (not stored - db doesn't have this)
        notes: Additional notes (not stored - db doesn't have this)
        blocked_by: Who/what is blocking the task
        tags: List of tags (only first one used - Identity, Compound)

    Returns the created task dict.
    """
    notion = get_notion_client()

    # Map bucket names to Notion status names
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
    }
    notion_status = STATUS_MAP.get(status, status)

    # Build properties
    properties = {
        "Name": {
            "title": [{"text": {"content": content}}]
        },
        "Status": {
            "status": {"name": notion_status}
        },
        "Mentioned": {
            "number": 1  # First mention
        }
    }

    if blocked_by:
        properties["Blocked"] = {
            "rich_text": [{"text": {"content": blocked_by}}]
        }

    if tags and len(tags) > 0:
        # Type is single-select, use first tag
        properties["Type"] = {
            "select": {"name": tags[0]}
        }

    page = notion.pages.create(
        parent={"database_id": TASKS_DATABASE_ID},
        properties=properties
    )

    return {
        "id": page["id"],
        "content": content,
        "status": notion_status,
        "estimated_minutes": estimated_minutes,
        "times_added": 1,
        "notes": notes,
        "url": page.get("url")
    }


def get_open_tasks() -> list[dict]:
    """
    Get all open tasks for semantic matching.

    Returns list of task dicts with id, content, status, times_added.
    Excludes Done tasks.
    """
    notion = get_notion_client()

    response = notion.databases.query(
        database_id=TASKS_DATABASE_ID,
        filter={
            "property": "Status",
            "status": {"does_not_equal": "Done"}
        }
    )

    tasks = []
    for page in response.get("results", []):
        props = page.get("properties", {})
        tasks.append({
            "id": page["id"],
            "content": _extract_title(props),
            "status": _extract_status(props, "Status"),
            "times_added": _extract_number(props, "Mentioned") or 1
        })

    return tasks


def increment_task_mentions(page_id: str) -> Optional[dict]:
    """
    Increment the Mentioned count for an existing task.

    Returns the updated task dict, or None if task doesn't exist.
    """
    notion = get_notion_client()

    try:
        # Get current mention count
        page = notion.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})
        current_count = _extract_number(props, "Mentioned") or 0

        # Increment and update
        new_count = current_count + 1
        updated_page = notion.pages.update(
            page_id=page_id,
            properties={
                "Mentioned": {"number": new_count}
            }
        )

        return {
            "id": page_id,
            "content": _extract_title(props),
            "status": _extract_select(props, "Status"),
            "times_added": new_count
        }

    except Exception:
        return None


def find_task_by_id(page_id: str) -> Optional[dict]:
    """
    Fetch a single task by page ID.

    Returns task dict or None if not found.
    """
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
            "tag": _extract_select(props, "Type")
        }

    except Exception:
        return None


# ============================================================================
# Helper functions for extracting Notion properties
# ============================================================================

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
