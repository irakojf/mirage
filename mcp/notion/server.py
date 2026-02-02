#!/usr/bin/env python3
"""
Notion MCP Server for Mirage

Provides tools to:
- Fetch Production Calendar from Notion
- Fetch Notion pages by ID
- Query, create, update tasks in Mirage tasks database
- Track task mentions for procrastination detection
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Any

# MCP SDK imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Notion SDK
from notion_client import Client

# Core imports — status/type resolution from single source of truth
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from mirage_core.adapters.notion_repo import (
    NotionReviewRepository,
    NotionTaskRepository,
)
from mirage_core.aliases import resolve_status, resolve_type
from mirage_core.config import MirageConfig
from mirage_core.models import EnergyLevel, Review, ReviewId, TaskId, TaskMutation
from mirage_core.services import TaskCaptureService, normalize_task_name

# Configuration — load from env with validation
_config = MirageConfig.from_env()
PRODUCTION_CALENDAR_ID = _config.production_calendar_id
TASKS_DATABASE_ID = _config.tasks_database_id
REVIEWS_DATABASE_ID = _config.reviews_database_id

server = Server("notion")


def get_notion_client():
    """Get authenticated Notion client."""
    _config.validate()
    return Client(auth=_config.notion_token)


def get_task_repo() -> NotionTaskRepository:
    """Get task repository backed by Notion."""
    _config.validate()
    return NotionTaskRepository.from_env(TASKS_DATABASE_ID)


def get_review_repo() -> NotionReviewRepository:
    """Get review repository backed by Notion."""
    _config.validate()
    return NotionReviewRepository.from_env(REVIEWS_DATABASE_ID)


def _task_to_payload(task) -> dict:
    return {
        "id": task.id.value,
        "content": task.name,
        "status": task.status.value,
        "mentioned": task.mentioned,
        "blocked_by": task.blocked_by,
        "energy": task.energy.value if task.energy else None,
        "tags": task.task_type.value if task.task_type else None,
        "complete_time": task.complete_time_minutes,
        "priority": task.priority,
        "created_time": task.created_at.isoformat() if task.created_at else "",
        "url": task.url,
    }


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Notion tools."""
    return [
        Tool(
            name="get_production_calendar",
            description="Fetch items from the Production Calendar in Notion",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 14)"
                    },
                    "status_filter": {
                        "type": "string",
                        "description": "Filter by status (optional)"
                    }
                }
            }
        ),
        Tool(
            name="get_notion_page",
            description="Fetch content from any Notion page by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "Notion page ID (from URL)"
                    }
                },
                "required": ["page_id"]
            }
        ),
        # Task management tools
        Tool(
            name="query_tasks",
            description="Query tasks from the Mirage tasks database with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "description": "Filter by status: Tasks, Projects, Ideas, Blocked, Not Now, Waiting On, Done, Won't Do (optional)"
                    },
                    "exclude_done": {
                        "type": "boolean",
                        "description": "Exclude Done and Archived tasks (default: false)"
                    }
                }
            }
        ),
        Tool(
            name="create_task",
            description="Create a new task in the Mirage tasks database",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Task description"
                    },
                    "status": {
                        "type": "string",
                        "description": "Status: Action/Tasks, Project/Projects, Idea/Ideas, Blocked, Not Now, Waiting On, Won't Do, Done"
                    },
                    "blocked_by": {
                        "type": "string",
                        "description": "Who/what is blocking (optional)"
                    },
                    "tag": {
                        "type": "string",
                        "description": "Tag: Identity, Compound, Do It Now, Never Miss 2x, Important Not Urgent, Unblocks (optional)"
                    },
                    "complete_time": {
                        "type": "integer",
                        "description": "Estimated time to complete in minutes (optional)"
                    }
                },
                "required": ["content", "status"]
            }
        ),
        Tool(
            name="update_task",
            description="Update an existing task in the Mirage tasks database",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "Notion page ID of the task"
                    },
                    "content": {
                        "type": "string",
                        "description": "New task name/description (optional)"
                    },
                    "status": {
                        "type": "string",
                        "description": "New status: Tasks, Projects, Ideas, Blocked, Not Now, Waiting On, Won't Do, Done (optional)"
                    },
                    "mentioned": {
                        "type": "integer",
                        "description": "New mention count (optional)"
                    },
                    "blocked_by": {
                        "type": "string",
                        "description": "New blocked by value (optional)"
                    },
                    "energy": {
                        "type": "string",
                        "description": "Energy rating: Red, Yellow, Green (optional)"
                    },
                    "tag": {
                        "type": "string",
                        "description": "Tag: Identity, Compound, Do It Now, Never Miss 2x, Important Not Urgent, Unblocks (optional)"
                    },
                    "complete_time": {
                        "type": "integer",
                        "description": "Estimated time to complete in minutes (optional)"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority ranking (1 = highest priority) (optional)"
                    }
                },
                "required": ["page_id"]
            }
        ),
        Tool(
            name="increment_task_mention",
            description="Increment the Mentioned count for a task (for procrastination tracking)",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "Notion page ID of the task"
                    }
                },
                "required": ["page_id"]
            }
        ),
        # Review tools
        Tool(
            name="create_review",
            description="Create a weekly review record in the Mirage reviews database",
            inputSchema={
                "type": "object",
                "properties": {
                    "week_of": {
                        "type": "string",
                        "description": "Week date in YYYY-MM-DD format (e.g., start of the week)"
                    },
                    "wins": {
                        "type": "string",
                        "description": "Summary of wins/accomplishments this week"
                    },
                    "struggles": {
                        "type": "string",
                        "description": "Challenges or struggles faced"
                    },
                    "next_week_focus": {
                        "type": "string",
                        "description": "Primary focus for next week"
                    },
                    "tasks_completed": {
                        "type": "integer",
                        "description": "Number of tasks completed this week"
                    },
                    "transcript": {
                        "type": "string",
                        "description": "Full transcript of the review conversation"
                    }
                },
                "required": ["week_of", "transcript"]
            }
        ),
        Tool(
            name="update_page_content",
            description="Update the content of a Notion page by replacing all blocks with new content",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "Notion page ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "Markdown content to set as page content (supports headings, paragraphs, lists)"
                    }
                },
                "required": ["page_id", "content"]
            }
        )
    ]


def _error_response(tool_name: str, error: Exception) -> list[TextContent]:
    """Build a consistent error response for any tool failure."""
    error_type = type(error).__name__
    payload = json.dumps({
        "error": True,
        "tool": tool_name,
        "type": error_type,
        "message": str(error),
    })
    return [TextContent(type="text", text=payload)]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        notion = get_notion_client()

        if name == "get_production_calendar":
            return await get_production_calendar(notion, arguments)
        elif name == "get_notion_page":
            return await get_notion_page(notion, arguments)
        elif name == "query_tasks":
            return await query_tasks(notion, arguments)
        elif name == "create_task":
            return await create_task(notion, arguments)
        elif name == "update_task":
            return await update_task(notion, arguments)
        elif name == "increment_task_mention":
            return await increment_task_mention(notion, arguments)
        elif name == "create_review":
            return await create_review(notion, arguments)
        elif name == "update_page_content":
            return await update_page_content(notion, arguments)
        else:
            return _error_response(name, ValueError(f"Unknown tool: {name}"))
    except Exception as e:
        return _error_response(name, e)


async def get_production_calendar(notion: Client, args: dict) -> list[TextContent]:
    """Fetch items from Production Calendar database."""
    days_ahead = args.get("days_ahead", 14)
    status_filter = args.get("status_filter")

    # Build filter
    today = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    filter_obj = {
        "and": [
            {
                "property": "Date",
                "date": {
                    "on_or_after": today
                }
            },
            {
                "property": "Date",
                "date": {
                    "on_or_before": future
                }
            }
        ]
    }

    if status_filter:
        filter_obj["and"].append({
            "property": "Status",
            "select": {
                "equals": status_filter
            }
        })

    try:
        # Query the database
        response = notion.databases.query(
            database_id=PRODUCTION_CALENDAR_ID,
            filter=filter_obj,
            sorts=[
                {
                    "property": "Date",
                    "direction": "ascending"
                }
            ]
        )

        items = []
        for page in response.get("results", []):
            props = page.get("properties", {})

            # Extract common properties (adjust based on actual schema)
            item = {
                "id": page["id"],
                "title": extract_title(props),
                "date": extract_date(props),
                "status": extract_select(props, "Status"),
                "url": page.get("url")
            }
            items.append(item)

        result = {
            "calendar": "Production Calendar",
            "period": f"{today} to {future}",
            "items": items,
            "count": len(items)
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        # If database query fails, try fetching as a page
        return _error_response("get_production_calendar", e)


async def get_notion_page(notion: Client, args: dict) -> list[TextContent]:
    """Fetch a Notion page by ID."""
    page_id = args["page_id"]

    page = notion.pages.retrieve(page_id=page_id)

    # Get page blocks (content)
    blocks = notion.blocks.children.list(block_id=page_id)

    content = []
    for block in blocks.get("results", []):
        block_type = block.get("type")
        if block_type == "paragraph":
            text = extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
            if text:
                content.append(text)
        elif block_type == "heading_1":
            text = extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
            content.append(f"# {text}")
        elif block_type == "heading_2":
            text = extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
            content.append(f"## {text}")
        elif block_type == "heading_3":
            text = extract_rich_text(block.get("heading_3", {}).get("rich_text", []))
            content.append(f"### {text}")
        elif block_type == "bulleted_list_item":
            text = extract_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
            content.append(f"- {text}")
        elif block_type == "numbered_list_item":
            text = extract_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
            content.append(f"1. {text}")
        elif block_type == "to_do":
            text = extract_rich_text(block.get("to_do", {}).get("rich_text", []))
            checked = block.get("to_do", {}).get("checked", False)
            checkbox = "[x]" if checked else "[ ]"
            content.append(f"{checkbox} {text}")

    result = {
        "page_id": page_id,
        "url": page.get("url"),
        "content": "\n".join(content)
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ============================================================================
# Task Management Tools
# ============================================================================

async def query_tasks(notion: Client, args: dict) -> list[TextContent]:
    """Query tasks from the Mirage tasks database."""
    status_filter = args.get("status_filter")
    exclude_done = args.get("exclude_done", False)

    try:
        repo = get_task_repo()
        status = resolve_status(status_filter) if status_filter else None
        tasks = await repo.query(status=status, exclude_done=exclude_done)

        result = {
            "tasks": [_task_to_payload(task) for task in tasks],
            "count": len(tasks),
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return _error_response("query_tasks", e)


async def create_task(notion: Client, args: dict) -> list[TextContent]:
    """Create a new task in the Mirage tasks database."""
    content = args["content"]
    status = args["status"]
    blocked_by = args.get("blocked_by")
    tag = args.get("tag")
    complete_time = args.get("complete_time")

    try:
        repo = get_task_repo()
        capture = TaskCaptureService(repo)
        task = await capture.capture(
            content,
            status,
            blocked_by=blocked_by,
            tag=tag,
            complete_time=complete_time,
        )

        payload = _task_to_payload(task)
        payload["success"] = True
        return [TextContent(type="text", text=json.dumps(payload, indent=2))]

    except Exception as e:
        return _error_response("create_task", e)


async def update_task(notion: Client, args: dict) -> list[TextContent]:
    """Update an existing task in the Mirage tasks database."""
    page_id = args["page_id"]

    energy = None
    if "energy" in args and args["energy"]:
        try:
            energy = EnergyLevel(args["energy"].capitalize())
        except ValueError as exc:
            return [TextContent(type="text", text=f"Invalid energy value: {exc}")]

    try:
        mutation = TaskMutation(
            task_id=TaskId(page_id),
            name=normalize_task_name(args["content"]) if "content" in args else None,
            status=resolve_status(args["status"]) if "status" in args else None,
            mentioned=args.get("mentioned"),
            blocked_by=args.get("blocked_by"),
            energy=energy,
            task_type=resolve_type(args["tag"]) if "tag" in args else None,
            complete_time_minutes=args.get("complete_time"),
            priority=args.get("priority"),
        )

        repo = get_task_repo()
        task = await repo.update(mutation)
        payload = _task_to_payload(task)
        payload["success"] = True
        return [TextContent(type="text", text=json.dumps(payload, indent=2))]

    except Exception as e:
        return _error_response("update_task", e)


async def increment_task_mention(notion: Client, args: dict) -> list[TextContent]:
    """Increment the Mentioned count for a task."""
    page_id = args["page_id"]

    try:
        repo = get_task_repo()
        task = await repo.get(TaskId(page_id))
        current_count = task.mentioned if task else 0
        new_count = await repo.increment_mentioned(TaskId(page_id))

        result = {
            "success": True,
            "id": page_id,
            "content": task.name if task else "",
            "previous_count": current_count,
            "new_count": new_count
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return _error_response("increment_task_mention", e)


async def create_review(notion: Client, args: dict) -> list[TextContent]:
    """Create a weekly review record in the Mirage reviews database."""
    week_of_raw = args["week_of"]
    transcript = args["transcript"]
    wins = args.get("wins", "")
    struggles = args.get("struggles", "")
    next_week_focus = args.get("next_week_focus", "")
    tasks_completed = args.get("tasks_completed")

    try:
        try:
            week_of = datetime.fromisoformat(week_of_raw)
        except ValueError:
            week_of = datetime.strptime(week_of_raw, "%Y-%m-%d")

        review = Review(
            id=ReviewId("pending"),
            week_of=week_of,
            transcript=transcript,
            wins=wins or None,
            struggles=struggles or None,
            next_week_focus=next_week_focus or None,
            tasks_completed=tasks_completed,
        )

        repo = get_review_repo()
        saved = await repo.create(review)

        result = {
            "success": True,
            "id": saved.id.value,
            "week_of": week_of_raw,
            "url": saved.url,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return _error_response("create_review", e)


async def update_page_content(notion: Client, args: dict) -> list[TextContent]:
    """Update a Notion page's content by replacing all blocks."""
    page_id = args["page_id"]
    content = args["content"]

    try:
        # First, delete all existing blocks
        existing_blocks = notion.blocks.children.list(block_id=page_id)
        for block in existing_blocks.get("results", []):
            notion.blocks.delete(block_id=block["id"])

        # Parse markdown content into Notion blocks
        blocks = parse_markdown_to_blocks(content)

        # Add new blocks
        if blocks:
            notion.blocks.children.append(block_id=page_id, children=blocks)

        result = {
            "success": True,
            "page_id": page_id,
            "blocks_added": len(blocks)
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return _error_response("update_page_content", e)


def parse_markdown_to_blocks(content: str) -> list[dict]:
    """Parse markdown content into Notion blocks."""
    blocks = []
    lines = content.split("\n")

    for line in lines:
        line = line.rstrip()

        # Skip empty lines
        if not line:
            continue

        # Headings
        if line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                }
            })
        elif line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        elif line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        # Bulleted list
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        # Numbered list (simple pattern)
        elif len(line) > 2 and line[0].isdigit() and line[1] == "." and line[2] == " ":
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        # Quote blocks
        elif line.startswith("> "):
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        # Regular paragraph
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                }
            })

    return blocks


# Helper functions for extracting Notion properties
def extract_title(props: dict) -> str:
    """Extract title from properties."""
    for key, value in props.items():
        if value.get("type") == "title":
            title_list = value.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_list)
    return "Untitled"


def extract_date(props: dict) -> str:
    """Extract date from properties."""
    for key, value in props.items():
        if value.get("type") == "date" and value.get("date"):
            return value["date"].get("start", "")
    return ""


def extract_select(props: dict, prop_name: str) -> str:
    """Extract select property value."""
    if prop_name in props:
        select = props[prop_name].get("select")
        if select:
            return select.get("name", "")
    return ""


def extract_status(props: dict, prop_name: str) -> str:
    """Extract status property value (different from select)."""
    if prop_name in props:
        status = props[prop_name].get("status")
        if status:
            return status.get("name", "")
    return ""


def extract_number(props: dict, prop_name: str) -> int | None:
    """Extract number property value."""
    if prop_name in props:
        return props[prop_name].get("number")
    return None


def extract_text(props: dict, prop_name: str) -> str:
    """Extract rich_text property as plain text."""
    if prop_name in props:
        rich_text = props[prop_name].get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in rich_text)
    return ""


def extract_multi_select(props: dict, prop_name: str) -> list[str]:
    """Extract multi_select property values."""
    if prop_name in props:
        options = props[prop_name].get("multi_select", [])
        return [opt.get("name", "") for opt in options]
    return []


def extract_rich_text(rich_text: list) -> str:
    """Extract plain text from rich text array."""
    return "".join(t.get("plain_text", "") for t in rich_text)


async def main():
    """Run the MCP server."""
    # Fail fast if required config is missing
    try:
        _config.validate()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
