#!/usr/bin/env python3
"""
Reorder Backlog tasks in Notion so priority 1 tickets appear first.

This script queries tasks with "Backlog" status and reorders them by updating
their priority values in Notion.

Usage:
    python reorder_backlog.py                    # Uses NOTION_TOKEN env var
    python reorder_backlog.py --token secret_xxx # Provide token directly
    python reorder_backlog.py --dry-run          # Preview without making changes
"""

import os
import sys
import json
import argparse
from notion_client import Client

# Configuration
TASKS_DATABASE_ID = "2ea35d23-b569-80cc-99be-e6d6a17b1548"

def get_notion_client(token=None):
    """Get authenticated Notion client."""
    notion_token = token or os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
    if not notion_token:
        print("Error: Notion API token not found.")
        print("\nTo fix this, either:")
        print("  1. Set NOTION_TOKEN environment variable:")
        print("     export NOTION_TOKEN='secret_xxxx'")
        print("\n  2. Or provide token via command line:")
        print("     python reorder_backlog.py --token secret_xxxx")
        sys.exit(1)
    return Client(auth=notion_token)


def extract_title(props: dict) -> str:
    """Extract title from properties."""
    for key, value in props.items():
        if value.get("type") == "title":
            title_list = value.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_list)
    return "Untitled"


def extract_status(props: dict, prop_name: str) -> str:
    """Extract status property value."""
    if prop_name in props:
        status = props[prop_name].get("status")
        if status:
            return status.get("name", "")
    return ""


def extract_number(props: dict, prop_name: str):
    """Extract number property value."""
    if prop_name in props:
        return props[prop_name].get("number")
    return None


def query_backlog_tasks(notion: Client, status_filter: str = "Backlog"):
    """Query all tasks, optionally filtering by status."""
    # Query all tasks to see what statuses exist
    response = notion.databases.query(database_id=TASKS_DATABASE_ID)

    all_tasks = []
    filtered_tasks = []

    for page in response.get("results", []):
        props = page.get("properties", {})
        task = {
            "id": page["id"],
            "content": extract_title(props),
            "status": extract_status(props, "Status"),
            "priority": extract_number(props, "Priority"),
            "url": page.get("url")
        }
        all_tasks.append(task)

        # Check for matching status (case-insensitive)
        if task["status"].lower() == status_filter.lower():
            filtered_tasks.append(task)

    return all_tasks, filtered_tasks


def reorder_backlog_by_priority(notion: Client, tasks: list, dry_run: bool = False):
    """
    Reorder backlog tasks so priority 1 appears first.

    Notion doesn't have a direct "order" API, but we can achieve visual ordering
    by updating tasks in a specific sequence. The most reliable way is to ensure
    the Priority field is set correctly and the view is sorted by Priority.

    We'll assign priority values:
    - Priority 1 tasks get priority 1
    - Other tasks get priority 2, 3, 4, etc. based on their current order
    """
    # Separate priority 1 and others
    priority_1 = [t for t in tasks if t["priority"] == 1]
    others = [t for t in tasks if t["priority"] != 1]

    print(f"\nFound {len(priority_1)} priority 1 tasks")
    print(f"Found {len(others)} other priority tasks")

    # Sort others by their current priority (if any), keeping relative order
    others.sort(key=lambda t: (t["priority"] is None, t["priority"] or 999))

    # Assign sequential priorities: priority 1 tasks keep 1, others get 2, 3, 4, etc.
    updates = []

    # Priority 1 tasks stay at 1
    for task in priority_1:
        if task["priority"] != 1:
            updates.append({"id": task["id"], "content": task["content"], "new_priority": 1})

    # Other tasks get sequential priorities starting from 2
    next_priority = 2
    for task in others:
        if task["priority"] != next_priority:
            updates.append({"id": task["id"], "content": task["content"], "new_priority": next_priority})
        next_priority += 1

    print(f"\n{'[DRY RUN] Would update' if dry_run else 'Will update'} {len(updates)} tasks")

    # Perform updates
    for update in updates:
        print(f"  {'[DRY RUN] ' if dry_run else ''}Updating '{update['content']}' -> Priority {update['new_priority']}")
        if not dry_run:
            notion.pages.update(
                page_id=update["id"],
                properties={
                    "Priority": {"number": update["new_priority"]}
                }
            )

    return updates


def main():
    parser = argparse.ArgumentParser(description="Reorder Backlog tasks by priority in Notion")
    parser.add_argument("--token", help="Notion API token (or set NOTION_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without making them")
    parser.add_argument("--status", default="Backlog", help="Status to filter by (default: Backlog)")
    args = parser.parse_args()

    notion = get_notion_client(args.token)

    print("Querying tasks from Notion...")
    all_tasks, filtered_tasks = query_backlog_tasks(notion, args.status)

    print(f"\nTotal tasks found: {len(all_tasks)}")

    # Show all unique statuses
    statuses = set(t["status"] for t in all_tasks)
    print(f"Statuses in database: {statuses}")

    if filtered_tasks:
        print(f"\n{args.status} tasks found: {len(filtered_tasks)}")
        for t in filtered_tasks:
            print(f"  [P{t['priority'] or '-'}] {t['content']}")

        print(f"\nReordering {args.status} tasks...")
        updates = reorder_backlog_by_priority(notion, filtered_tasks, args.dry_run)
        if args.dry_run:
            print(f"\n[DRY RUN] Would have updated {len(updates)} tasks.")
        else:
            print(f"\nDone! Updated {len(updates)} tasks.")
            print("\nNote: Make sure your Notion view is sorted by 'Priority' (ascending) to see the reordering.")
    else:
        print(f"\nNo tasks with '{args.status}' status found.")
        print("\nShowing all tasks with their statuses and priorities:")
        for t in all_tasks:
            print(f"  [{t['status']}] [P{t['priority'] or '-'}] {t['content']}")


if __name__ == "__main__":
    main()
