#!/usr/bin/env python3
"""
Kanban integrity checker and view sync for Mirage Notion database.

Validates that tasks in the live Notion database have valid status/type
combinations and flags integrity issues.

Usage:
    python schema/kanban_sync.py                 # check integrity against live Notion
    python schema/kanban_sync.py --dry-run       # parse specs only, no API call
    python schema/kanban_sync.py --export-views  # export current Notion view config
"""

import json
import os
import sys
import yaml
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent


def load_views_spec(path: Path = SCHEMA_DIR / "views.yaml") -> dict:
    """Load the views specification."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_schema(path: Path = SCHEMA_DIR / "tasks.yaml") -> dict:
    """Load the canonical schema."""
    with open(path) as f:
        return yaml.safe_load(f)


def get_notion_client():
    """Get authenticated Notion client."""
    from notion_client import Client

    token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY")
    if not token:
        print("ERROR: NOTION_TOKEN or NOTION_API_KEY must be set", file=sys.stderr)
        sys.exit(2)
    return Client(auth=token)


def check_integrity(notion, database_id: str, schema: dict, views_spec: dict) -> list[str]:
    """Check all tasks for integrity violations.

    Returns a list of issue strings.
    """
    issues = []
    rules = views_spec.get("integrity_rules", {})

    # Fetch all tasks
    response = notion.databases.query(database_id=database_id)
    tasks = response.get("results", [])

    # Valid statuses and types from schema
    valid_statuses = set()
    for group in schema["properties"]["Status"].get("groups", {}).values():
        valid_statuses.update(group)

    valid_types = set(schema["properties"]["Type"].get("options", []))

    for page in tasks:
        props = page.get("properties", {})
        page_id = page["id"][:8]
        name = _extract_title(props)

        # Check status
        status = _extract_status(props, "Status")
        if status and status not in valid_statuses:
            issues.append(f"[{page_id}] '{name}': invalid status '{status}'")

        # Check type
        task_type = _extract_select(props, "Type")
        if task_type and task_type not in valid_types:
            issues.append(f"[{page_id}] '{name}': invalid type '{task_type}'")

        # Blocked tasks must have a reason
        if rules.get("blocked_requires_reason") and status in ("Blocked", "Waiting On"):
            blocked_text = _extract_text(props, "Blocked")
            if not blocked_text.strip():
                issues.append(
                    f"[{page_id}] '{name}': status is '{status}' but Blocked field is empty"
                )

        # Completed tasks shouldn't have active priority
        if rules.get("completed_clears_priority") and status in ("Done", "Won't Do"):
            priority = _extract_number(props, "Priority")
            if priority is not None:
                issues.append(
                    f"[{page_id}] '{name}': status is '{status}' but Priority is still set ({priority})"
                )

    return issues


def export_views(notion, database_id: str) -> dict:
    """Export the current database views configuration."""
    db = notion.databases.retrieve(database_id=database_id)

    # Extract status groups
    status_prop = db.get("properties", {}).get("Status", {})
    status_groups = status_prop.get("status", {}).get("groups", [])

    # Extract type options
    type_prop = db.get("properties", {}).get("Type", {})
    type_options = type_prop.get("select", {}).get("options", [])

    return {
        "database_id": database_id,
        "status_groups": [
            {
                "name": g.get("name"),
                "color": g.get("color"),
                "options": [o.get("name") for o in g.get("options", [])],
            }
            for g in status_groups
        ],
        "type_options": [
            {"name": o.get("name"), "color": o.get("color")}
            for o in type_options
        ],
    }


def main():
    dry_run = "--dry-run" in sys.argv
    do_export = "--export-views" in sys.argv

    schema = load_schema()
    views_spec = load_views_spec()

    print(f"Schema: v{schema['schema_version']} — {schema['database']['name']}")
    print(f"Views: {len(views_spec.get('views', []))} defined")
    print(f"Integrity rules: {len(views_spec.get('integrity_rules', {}))}")

    if dry_run:
        print("\n--dry-run: Specs parsed successfully.\n")
        for view in views_spec.get("views", []):
            cols = len(view.get("columns", []))
            print(f"  View: {view['name']} ({view['type']}, {cols} columns)")
        return 0

    database_id = schema["database"]["id"]
    notion = get_notion_client()

    if do_export:
        print(f"\nExporting views from {database_id}...")
        snapshot = export_views(notion, database_id)
        output_path = SCHEMA_DIR / "views_snapshot.json"
        with open(output_path, "w") as f:
            json.dump(snapshot, f, indent=2)
        print(f"Exported to {output_path}")
        return 0

    # Default: integrity check
    print(f"\nChecking integrity for {database_id}...")
    issues = check_integrity(notion, database_id, schema, views_spec)

    if issues:
        print(f"\nINTEGRITY ISSUES — {len(issues)} found:\n")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("\nINTEGRITY OK — all tasks pass validation.")
        return 0


# -- helpers (duplicated to keep script standalone) --

def _extract_title(props: dict) -> str:
    for value in props.values():
        if value.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in value.get("title", []))
    return "Untitled"


def _extract_status(props: dict, name: str) -> str:
    if name in props:
        s = props[name].get("status")
        if s:
            return s.get("name", "")
    return ""


def _extract_select(props: dict, name: str) -> str:
    if name in props:
        s = props[name].get("select")
        if s:
            return s.get("name", "")
    return ""


def _extract_number(props: dict, name: str):
    if name in props:
        return props[name].get("number")
    return None


def _extract_text(props: dict, name: str) -> str:
    if name in props:
        return "".join(t.get("plain_text", "") for t in props[name].get("rich_text", []))
    return ""


if __name__ == "__main__":
    sys.exit(main())
