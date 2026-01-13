#!/usr/bin/env python3
"""
Notion MCP Server for Mirage

Provides tools to:
- Fetch Production Calendar from Notion
- List upcoming production items
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


def extract_rich_text(rich_text: list) -> str:
    """Extract plain text from rich text array."""
    return "".join(t.get("plain_text", "") for t in rich_text)


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
