#!/usr/bin/env python3
"""
Google Calendar CLI for Mirage

Provides subcommands:
- list_events: List calendar events for a date range
- get_free_time: Get available free time blocks for a day
- get_week_overview: Busy/free summary for the next 7 days
- create_event: Create a new calendar event

Usage:
    python3.11 mcp/google-calendar/server.py list_events --start-date 2026-02-10
    python3.11 mcp/google-calendar/server.py get_free_time --date 2026-02-10
    python3.11 mcp/google-calendar/server.py get_week_overview
    python3.11 mcp/google-calendar/server.py create_event --title "Meeting" --start "2026-02-10T14:00:00" --end "2026-02-10T15:00:00"

All output is JSON to stdout.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Google Calendar API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Add project root to path for mirage_core imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from mirage_core.config import MirageConfig

# OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Paths
CREDENTIALS_PATH = os.path.expanduser('~/.config/mirage/credentials.json')
TOKEN_PATH = os.path.expanduser('~/.config/mirage/token.json')


def get_timezone() -> str:
    """Return configured timezone for calendar operations."""
    return MirageConfig.from_env().timezone


def get_zoneinfo(timezone: str) -> ZoneInfo:
    """Return ZoneInfo for timezone, falling back to UTC on errors."""
    try:
        return ZoneInfo(timezone)
    except Exception:
        return ZoneInfo("UTC")


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


def get_free_time(service, date_str: str, work_start: str = "09:00", work_end: str = "18:00") -> dict:
    """Calculate free time blocks for a given day."""
    tz = get_zoneinfo(get_timezone())

    # Parse date and work hours
    start_dt = datetime.strptime(
        f"{date_str} {work_start}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=tz)
    end_dt = datetime.strptime(
        f"{date_str} {work_end}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=tz)

    # Get events for the day
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_dt.isoformat(),
        timeMax=end_dt.isoformat(),
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

    return {
        "date": date_str,
        "total_free_minutes": total_free,
        "total_free_hours": round(total_free / 60, 1),
        "free_blocks": free_blocks
    }


def get_week_overview(service, work_start: str = "09:00", work_end: str = "18:00") -> dict:
    """Get busy/free summary for the next 7 days."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_data = []

    for i in range(7):
        day = today + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")

        day_data = get_free_time(service, day_str, work_start, work_end)
        week_data.append({
            "date": day_str,
            "day": day.strftime("%A"),
            "free_hours": day_data["total_free_hours"]
        })

    total_free = sum(d["free_hours"] for d in week_data)

    return {
        "week_start": today.strftime("%Y-%m-%d"),
        "total_free_hours": round(total_free, 1),
        "days": week_data
    }


def create_event(service, title: str, start: str, end: str, description: str | None = None) -> dict:
    """Create a new calendar event."""
    timezone = get_timezone()
    event = {
        'summary': title,
        'start': {'dateTime': start, 'timeZone': timezone},
        'end': {'dateTime': end, 'timeZone': timezone},
    }

    if description:
        event['description'] = description

    created = service.events().insert(calendarId='primary', body=event).execute()

    return {
        "success": True,
        "event_link": created.get('htmlLink'),
        "event_id": created.get('id'),
        "summary": created.get('summary'),
    }


def list_events(service, start_date: str, end_date: str | None = None) -> list:
    """List events for a date range."""
    if not end_date:
        end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")

    tz = get_zoneinfo(get_timezone())

    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=tz)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=tz) + timedelta(days=1)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_dt.isoformat(),
        timeMax=end_dt.isoformat(),
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

    return result


def main():
    parser = argparse.ArgumentParser(description="Google Calendar CLI for Mirage")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list_events
    p_list = subparsers.add_parser("list_events", help="List events for a date range")
    p_list.add_argument("--start-date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Start date YYYY-MM-DD (default: today)")
    p_list.add_argument("--end-date", default=None,
                        help="End date YYYY-MM-DD (default: start + 7 days)")

    # get_free_time
    p_free = subparsers.add_parser("get_free_time", help="Get free time blocks for a day")
    p_free.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Date YYYY-MM-DD (default: today)")
    p_free.add_argument("--work-start", default="09:00", help="Work start HH:MM (default: 09:00)")
    p_free.add_argument("--work-end", default="18:00", help="Work end HH:MM (default: 18:00)")

    # get_week_overview
    p_week = subparsers.add_parser("get_week_overview", help="Busy/free summary for next 7 days")
    p_week.add_argument("--work-start", default="09:00", help="Work start HH:MM (default: 09:00)")
    p_week.add_argument("--work-end", default="18:00", help="Work end HH:MM (default: 18:00)")

    # create_event
    p_create = subparsers.add_parser("create_event", help="Create a calendar event")
    p_create.add_argument("--title", required=True, help="Event title")
    p_create.add_argument("--start", required=True, help="Start time ISO format (YYYY-MM-DDTHH:MM:SS)")
    p_create.add_argument("--end", required=True, help="End time ISO format (YYYY-MM-DDTHH:MM:SS)")
    p_create.add_argument("--description", default=None, help="Event description")

    args = parser.parse_args()

    try:
        service = get_calendar_service()

        if args.command == "list_events":
            result = list_events(service, args.start_date, args.end_date)
        elif args.command == "get_free_time":
            result = get_free_time(service, args.date, args.work_start, args.work_end)
        elif args.command == "get_week_overview":
            result = get_week_overview(service, args.work_start, args.work_end)
        elif args.command == "create_event":
            result = create_event(service, args.title, args.start, args.end, args.description)

        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
