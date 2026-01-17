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

# Configuration
NOTION_TOKEN = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
PRODUCTION_CALENDAR_ID = "28535d23-b569-80d3-b186-d1886bc53f0b"  # Shapeshift Production Calendar database
TASKS_DATABASE_ID = "2ea35d23-b569-80cc-99be-e6d6a17b1548"  # Mirage Tasks database
REVIEWS_DATABASE_ID = "2eb35d23-b569-8040-859f-d5baff2957ab"  # Mirage Reviews database

server = Server("notion")


def get_notion_client():
    """Get authenticated Notion client."""
    if not NOTION_TOKEN:
        raise ValueError(
            "Notion API token not found.\n"
            "Set NOTION_TOKEN environment variable or add to ~/.config/mirage/notion-token"
        )
    return Client(auth=NOTION_TOKEN)


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
                        "description": "Filter by status: Action, Project, Idea, Blocked, Done, Archived (optional)"
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
                        "description": "Status: Action/Tasks, Project/Projects, Idea/Ideas, Blocked"
                    },
                    "blocked_by": {
                        "type": "string",
                        "description": "Who/what is blocking (optional)"
                    },
                    "tag": {
                        "type": "string",
                        "description": "Tag: Identity or Compound (optional)"
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
                    "status": {
                        "type": "string",
                        "description": "New status: Tasks, Projects, Ideas, Blocked, Done (optional)"
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
                        "description": "Tag: Identity or Compound (optional)"
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
        )
    ]


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
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


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
        return [TextContent(type="text", text=f"Could not query database: {str(e)}\nMake sure the integration has access to this page.")]


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

    # Build filter - Status is a "status" type property
    filter_obj = None
    if status_filter:
        filter_obj = {
            "property": "Status",
            "status": {"equals": status_filter}
        }
    elif exclude_done:
        filter_obj = {
            "property": "Status",
            "status": {"does_not_equal": "Done"}
        }

    try:
        query_args = {"database_id": TASKS_DATABASE_ID}
        if filter_obj:
            query_args["filter"] = filter_obj

        response = notion.databases.query(**query_args)

        tasks = []
        for page in response.get("results", []):
            props = page.get("properties", {})
            task = {
                "id": page["id"],
                "content": extract_title(props),
                "status": extract_status(props, "Status"),
                "mentioned": extract_number(props, "Mentioned"),
                "blocked_by": extract_text(props, "Blocked"),
                "energy": extract_select(props, "Energy"),
                "tags": extract_select(props, "Type"),  # Type is single-select
                "created_time": page.get("created_time", ""),
                "url": page.get("url")
            }
            tasks.append(task)

        result = {
            "tasks": tasks,
            "count": len(tasks)
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error querying tasks: {str(e)}")]


async def create_task(notion: Client, args: dict) -> list[TextContent]:
    """Create a new task in the Mirage tasks database."""
    content = args["content"]
    status = args["status"]
    blocked_by = args.get("blocked_by")
    tag = args.get("tag")  # Single tag: Identity, Compound

    # Map bucket names to Notion status names
    STATUS_MAP = {
        "Action": "Tasks",
        "Project": "Projects",
        "Idea": "Ideas",
        "Blocked": "Blocked",
        "Done": "Done",
        # Also accept Notion names directly
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

    if tag:
        properties["Type"] = {
            "select": {"name": tag}
        }

    try:
        page = notion.pages.create(
            parent={"database_id": TASKS_DATABASE_ID},
            properties=properties
        )

        result = {
            "success": True,
            "id": page["id"],
            "content": content,
            "status": notion_status,
            "url": page.get("url")
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error creating task: {str(e)}")]


async def update_task(notion: Client, args: dict) -> list[TextContent]:
    """Update an existing task in the Mirage tasks database."""
    page_id = args["page_id"]

    # Status mapping
    STATUS_MAP = {
        "Action": "Tasks",
        "Project": "Projects",
        "Idea": "Ideas",
        "Blocked": "Blocked",
        "Done": "Done",
        "Tasks": "Tasks",
        "Projects": "Projects",
        "Ideas": "Ideas",
    }

    # Build properties to update
    properties = {}

    if "status" in args:
        notion_status = STATUS_MAP.get(args["status"], args["status"])
        properties["Status"] = {"status": {"name": notion_status}}

    if "mentioned" in args:
        properties["Mentioned"] = {"number": args["mentioned"]}

    if "blocked_by" in args:
        properties["Blocked"] = {
            "rich_text": [{"text": {"content": args["blocked_by"]}}]
        }

    if "energy" in args:
        # Capitalize first letter for Notion
        energy = args["energy"].capitalize()
        properties["Energy"] = {"select": {"name": energy}}

    if "tag" in args:
        properties["Type"] = {"select": {"name": args["tag"]}}

    if not properties:
        return [TextContent(type="text", text="No properties to update")]

    try:
        page = notion.pages.update(page_id=page_id, properties=properties)

        props = page.get("properties", {})
        result = {
            "success": True,
            "id": page["id"],
            "content": extract_title(props),
            "status": extract_status(props, "Status"),
            "url": page.get("url")
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error updating task: {str(e)}")]


async def increment_task_mention(notion: Client, args: dict) -> list[TextContent]:
    """Increment the Mentioned count for a task."""
    page_id = args["page_id"]

    try:
        # First, get current mention count
        page = notion.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})
        current_count = extract_number(props, "Mentioned") or 0

        # Increment and update
        new_count = current_count + 1
        updated_page = notion.pages.update(
            page_id=page_id,
            properties={
                "Mentioned": {"number": new_count}
            }
        )

        result = {
            "success": True,
            "id": page_id,
            "content": extract_title(props),
            "previous_count": current_count,
            "new_count": new_count
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error incrementing mention: {str(e)}")]


async def create_review(notion: Client, args: dict) -> list[TextContent]:
    """Create a weekly review record in the Mirage reviews database."""
    week_of = args["week_of"]
    transcript = args["transcript"]
    wins = args.get("wins", "")
    struggles = args.get("struggles", "")
    next_week_focus = args.get("next_week_focus", "")
    tasks_completed = args.get("tasks_completed")

    # Build properties
    properties = {
        "Name": {
            "title": [{"text": {"content": f"Week of {week_of}"}}]
        },
        "Transcript": {
            "rich_text": [{"text": {"content": transcript[:2000]}}]  # Notion limit
        }
    }

    # Optional properties - add if provided
    if wins:
        properties["Wins"] = {
            "rich_text": [{"text": {"content": wins}}]
        }

    if struggles:
        properties["Struggles"] = {
            "rich_text": [{"text": {"content": struggles}}]
        }

    if next_week_focus:
        properties["Next Week Focus"] = {
            "rich_text": [{"text": {"content": next_week_focus}}]
        }

    if tasks_completed is not None:
        properties["Tasks Completed"] = {"number": tasks_completed}

    try:
        page = notion.pages.create(
            parent={"database_id": REVIEWS_DATABASE_ID},
            properties=properties
        )

        result = {
            "success": True,
            "id": page["id"],
            "week_of": week_of,
            "url": page.get("url")
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error creating review: {str(e)}")]


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
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
