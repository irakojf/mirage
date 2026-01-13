#!/usr/bin/env python3
"""
Google Calendar MCP Server for Mirage

Provides tools to:
- Get free time blocks for a given day
- Get week overview of busy/free time
- Create calendar events
- List existing events
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

# Google Calendar API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Paths
CREDENTIALS_PATH = os.path.expanduser('~/.config/mirage/credentials.json')
TOKEN_PATH = os.path.expanduser('~/.config/mirage/token.json')

server = Server("google-calendar")


def get_calendar_service():
    """Authenticate and return Google Calendar service."""
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Google credentials not found at {CREDENTIALS_PATH}\n"
                    "Please download from Google Cloud Console and save there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future use
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available calendar tools."""
    return [
        Tool(
            name="get_free_time",
            description="Get available free time blocks for a specific date",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (defaults to today)"
                    },
                    "work_start": {
                        "type": "string",
                        "description": "Work day start time in HH:MM format (default: 09:00)"
                    },
                    "work_end": {
                        "type": "string",
                        "description": "Work day end time in HH:MM format (default: 18:00)"
                    }
                }
            }
        ),
        Tool(
            name="get_week_overview",
            description="Get busy/free time summary for the current week",
            inputSchema={
                "type": "object",
                "properties": {
                    "work_start": {
                        "type": "string",
                        "description": "Work day start time in HH:MM format (default: 09:00)"
                    },
                    "work_end": {
                        "type": "string",
                        "description": "Work day end time in HH:MM format (default: 18:00)"
                    }
                }
            }
        ),
        Tool(
            name="create_event",
            description="Create a new calendar event",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title"
                    },
                    "start": {
                        "type": "string",
                        "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)"
                    },
                    "end": {
                        "type": "string",
                        "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    }
                },
                "required": ["title", "start", "end"]
            }
        ),
        Tool(
            name="list_events",
            description="List calendar events for a date range",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (defaults to today)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (defaults to 7 days from start)"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        service = get_calendar_service()

        if name == "get_free_time":
            return await get_free_time(service, arguments)
        elif name == "get_week_overview":
            return await get_week_overview(service, arguments)
        elif name == "create_event":
            return await create_event(service, arguments)
        elif name == "list_events":
            return await list_events(service, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def get_free_time(service, args: dict) -> list[TextContent]:
    """Calculate free time blocks for a given day."""
    date_str = args.get("date", datetime.now().strftime("%Y-%m-%d"))
    work_start = args.get("work_start", "09:00")
    work_end = args.get("work_end", "18:00")

    # Parse date and work hours
    date = datetime.strptime(date_str, "%Y-%m-%d")
    start_dt = datetime.strptime(f"{date_str} {work_start}", "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(f"{date_str} {work_end}", "%Y-%m-%d %H:%M")

    # Get events for the day
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_dt.isoformat() + 'Z',
        timeMax=end_dt.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    # Calculate free blocks
    free_blocks = []
    current_time = start_dt

    for event in events:
        event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')).replace('Z', ''))
        event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')).replace('Z', ''))

        if current_time < event_start:
            free_blocks.append({
                "start": current_time.strftime("%H:%M"),
                "end": event_start.strftime("%H:%M"),
                "duration_minutes": int((event_start - current_time).total_seconds() / 60)
            })
        current_time = max(current_time, event_end)

    # Add remaining time if any
    if current_time < end_dt:
        free_blocks.append({
            "start": current_time.strftime("%H:%M"),
            "end": end_dt.strftime("%H:%M"),
            "duration_minutes": int((end_dt - current_time).total_seconds() / 60)
        })

    total_free = sum(block["duration_minutes"] for block in free_blocks)

    result = {
        "date": date_str,
        "total_free_minutes": total_free,
        "total_free_hours": round(total_free / 60, 1),
        "free_blocks": free_blocks
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_week_overview(service, args: dict) -> list[TextContent]:
    """Get busy/free summary for the week."""
    work_start = args.get("work_start", "09:00")
    work_end = args.get("work_end", "18:00")

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_data = []

    for i in range(7):
        day = today + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")

        free_result = await get_free_time(service, {
            "date": day_str,
            "work_start": work_start,
            "work_end": work_end
        })

        day_data = json.loads(free_result[0].text)
        week_data.append({
            "date": day_str,
            "day": day.strftime("%A"),
            "free_hours": day_data["total_free_hours"]
        })

    total_free = sum(d["free_hours"] for d in week_data)

    result = {
        "week_start": today.strftime("%Y-%m-%d"),
        "total_free_hours": round(total_free, 1),
        "days": week_data
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def create_event(service, args: dict) -> list[TextContent]:
    """Create a new calendar event."""
    event = {
        'summary': args['title'],
        'start': {'dateTime': args['start'], 'timeZone': 'America/Los_Angeles'},
        'end': {'dateTime': args['end'], 'timeZone': 'America/Los_Angeles'},
    }

    if 'description' in args:
        event['description'] = args['description']

    created = service.events().insert(calendarId='primary', body=event).execute()

    return [TextContent(type="text", text=f"Event created: {created.get('htmlLink')}")]


async def list_events(service, args: dict) -> list[TextContent]:
    """List events for a date range."""
    start_date = args.get("start_date", datetime.now().strftime("%Y-%m-%d"))
    end_date = args.get("end_date", (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d"))

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_dt.isoformat() + 'Z',
        timeMax=end_dt.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    result = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        result.append({
            "title": event.get('summary', 'No title'),
            "start": start,
            "end": event['end'].get('dateTime', event['end'].get('date'))
        })

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
