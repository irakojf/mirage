#!/usr/bin/env python3
"""
One-time migration: Turso tasks -> Notion

Migrates all open tasks from Turso to the Notion tasks database.
Run locally with both TURSO and NOTION credentials set.

Usage:
    export TURSO_DATABASE_URL=libsql://...
    export TURSO_AUTH_TOKEN=...
    export NOTION_TOKEN=secret_...
    python scripts/migrate_to_notion.py
"""

import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import libsql_experimental as libsql
from notion_client import Client

# Configuration
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
TASKS_DATABASE_ID = "2ea35d23-b569-80cc-99be-e6d6a17b1548"

# Status mapping: Turso bucket -> Notion status
# Turso uses: bucket (action/project/idea/blocked) + status (open/done/archived)
# Notion uses: Status select (Action/Project/Idea/Blocked/Done/Archived)
STATUS_MAP = {
    ("action", "open"): "Action",
    ("project", "open"): "Project",
    ("idea", "open"): "Idea",
    ("blocked", "open"): "Blocked",
    ("action", "done"): "Done",
    ("project", "done"): "Done",
    ("idea", "done"): "Done",
    ("blocked", "done"): "Done",
    ("action", "archived"): "Archived",
    ("project", "archived"): "Archived",
    ("idea", "archived"): "Archived",
    ("blocked", "archived"): "Archived",
}

# Energy mapping
ENERGY_MAP = {
    "red": "red",
    "yellow": "yellow",
    "green": "green",
}


def get_turso_connection():
    """Get connection to Turso database."""
    if not TURSO_DATABASE_URL:
        raise ValueError("TURSO_DATABASE_URL environment variable not set")

    if TURSO_AUTH_TOKEN:
        return libsql.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    else:
        return libsql.connect(TURSO_DATABASE_URL)


def get_notion_client():
    """Get authenticated Notion client."""
    if not NOTION_TOKEN:
        raise ValueError("NOTION_TOKEN environment variable not set")
    return Client(auth=NOTION_TOKEN)


def fetch_turso_tasks(conn, include_done=False):
    """Fetch tasks from Turso."""
    if include_done:
        query = """
            SELECT id, content, bucket, status, estimated_minutes, times_added,
                   first_added_at, blocked_on, energy_rating, notes
            FROM tasks
            ORDER BY first_added_at ASC
        """
    else:
        query = """
            SELECT id, content, bucket, status, estimated_minutes, times_added,
                   first_added_at, blocked_on, energy_rating, notes
            FROM tasks
            WHERE status = 'open'
            ORDER BY first_added_at ASC
        """

    cursor = conn.execute(query)
    tasks = []
    for row in cursor.fetchall():
        tasks.append({
            "id": row[0],
            "content": row[1],
            "bucket": row[2],
            "status": row[3],
            "estimated_minutes": row[4],
            "times_added": row[5],
            "first_added_at": row[6],
            "blocked_on": row[7],
            "energy_rating": row[8],
            "notes": row[9],
        })
    return tasks


def create_notion_task(notion, task):
    """Create a task in Notion database."""
    # Map status
    notion_status = STATUS_MAP.get(
        (task["bucket"], task["status"]),
        "Action"  # Default fallback
    )

    # Build properties
    properties = {
        "Name": {
            "title": [{"text": {"content": task["content"]}}]
        },
        "Status": {
            "select": {"name": notion_status}
        },
        "Mentioned": {
            "number": task["times_added"] or 1
        }
    }

    # Optional: Time to Complete
    if task["estimated_minutes"]:
        properties["Time to Complete"] = {"number": task["estimated_minutes"]}

    # Optional: Blocked By
    if task["blocked_on"]:
        properties["Blocked By"] = {
            "rich_text": [{"text": {"content": task["blocked_on"]}}]
        }

    # Optional: Energy
    if task["energy_rating"] and task["energy_rating"] in ENERGY_MAP:
        properties["Energy"] = {"select": {"name": ENERGY_MAP[task["energy_rating"]]}}

    # Create the page
    page = notion.pages.create(
        parent={"database_id": TASKS_DATABASE_ID},
        properties=properties
    )

    return page["id"]


def migrate_tasks(include_done=False, dry_run=False):
    """
    Migrate tasks from Turso to Notion.

    Args:
        include_done: If True, also migrate done/archived tasks
        dry_run: If True, don't actually create tasks, just show what would happen
    """
    print("=" * 60)
    print("MIRAGE TASK MIGRATION: Turso -> Notion")
    print("=" * 60)
    print()

    # Connect to databases
    print("Connecting to Turso...")
    conn = get_turso_connection()

    print("Connecting to Notion...")
    notion = get_notion_client()

    # Fetch tasks
    print(f"\nFetching tasks from Turso (include_done={include_done})...")
    tasks = fetch_turso_tasks(conn, include_done=include_done)
    print(f"Found {len(tasks)} tasks to migrate")

    if not tasks:
        print("\nNo tasks to migrate!")
        return

    # Migrate each task
    print("\n" + "-" * 60)
    print("MIGRATING TASKS")
    print("-" * 60)

    success_count = 0
    error_count = 0

    for i, task in enumerate(tasks, 1):
        status_key = (task["bucket"], task["status"])
        notion_status = STATUS_MAP.get(status_key, "Action")

        print(f"\n[{i}/{len(tasks)}] {task['content'][:50]}...")
        print(f"         Turso: bucket={task['bucket']}, status={task['status']}")
        print(f"         Notion: Status={notion_status}, Mentioned={task['times_added']}")

        if dry_run:
            print("         [DRY RUN] Would create in Notion")
            success_count += 1
        else:
            try:
                page_id = create_notion_task(notion, task)
                print(f"         [OK] Created: {page_id}")
                success_count += 1
            except Exception as e:
                print(f"         [ERROR] {str(e)}")
                error_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"\nTotal tasks:    {len(tasks)}")
    print(f"Successful:     {success_count}")
    print(f"Errors:         {error_count}")

    if dry_run:
        print("\n[DRY RUN MODE] No tasks were actually created.")
        print("Run without --dry-run to perform the actual migration.")

    conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate Mirage tasks from Turso to Notion")
    parser.add_argument("--include-done", action="store_true", help="Also migrate done/archived tasks")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without creating tasks")

    args = parser.parse_args()

    migrate_tasks(include_done=args.include_done, dry_run=args.dry_run)
