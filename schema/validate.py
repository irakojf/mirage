#!/usr/bin/env python3
"""
Schema validator for Mirage Notion databases.

Reads the canonical schema from schema/tasks.yaml and validates
that the live Notion database matches. Exits non-zero on drift.

Usage:
    python schema/validate.py              # validate against live Notion
    python schema/validate.py --dry-run    # parse schema only, no API call
"""

import os
import sys
import yaml
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent


def load_schema(path: Path = SCHEMA_DIR / "tasks.yaml") -> dict:
    """Load and return the canonical schema."""
    with open(path) as f:
        return yaml.safe_load(f)


def fetch_notion_schema(database_id: str) -> dict:
    """Fetch the live database schema from Notion API."""
    from notion_client import Client

    token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY")
    if not token:
        print("ERROR: NOTION_TOKEN or NOTION_API_KEY must be set", file=sys.stderr)
        sys.exit(2)

    notion = Client(auth=token)
    db = notion.databases.retrieve(database_id=database_id)
    return db.get("properties", {})


def validate(schema: dict, live_props: dict) -> list[str]:
    """
    Compare canonical schema properties against live Notion properties.

    Returns a list of error strings. Empty list = valid.
    """
    errors = []
    canonical = schema["properties"]

    # Check every canonical property exists in Notion with the right type
    for prop_name, spec in canonical.items():
        if prop_name not in live_props:
            errors.append(f"MISSING property: '{prop_name}' (expected type: {spec['type']})")
            continue

        live_type = live_props[prop_name].get("type", "unknown")
        expected_type = spec["type"]

        if live_type != expected_type:
            errors.append(
                f"TYPE MISMATCH: '{prop_name}' — "
                f"expected '{expected_type}', got '{live_type}'"
            )

        # For select properties, check that canonical options exist
        if expected_type == "select" and "options" in spec:
            live_options = {
                opt["name"]
                for opt in live_props[prop_name].get("select", {}).get("options", [])
            }
            for opt in spec["options"]:
                if opt not in live_options:
                    errors.append(
                        f"MISSING OPTION: '{prop_name}' is missing select option '{opt}' "
                        f"(live options: {sorted(live_options)})"
                    )

        # For status properties, check groups
        if expected_type == "status" and "groups" in spec:
            live_groups = live_props[prop_name].get("status", {}).get("groups", [])
            live_status_names = set()
            for group in live_groups:
                for opt in group.get("options", []):
                    live_status_names.add(opt["name"])

            for group_name, statuses in spec["groups"].items():
                for status_name in statuses:
                    if status_name not in live_status_names:
                        errors.append(
                            f"MISSING STATUS: '{status_name}' not found in "
                            f"live status options {sorted(live_status_names)}"
                        )

    # Warn about extra properties in Notion (not errors, just info)
    for prop_name in live_props:
        if prop_name not in canonical:
            print(f"INFO: Extra Notion property '{prop_name}' not in canonical schema")

    return errors


def validate_enums(schema: dict) -> list[str]:
    """Validate that mirage_core enums match the canonical schema.

    This runs offline (no Notion API) and catches drift between
    schema/tasks.yaml and mirage_core/models.py enums.
    """
    sys.path.insert(0, str(SCHEMA_DIR.parent))
    from mirage_core.models import EnergyLevel, TaskStatus, TaskType

    errors = []
    props = schema["properties"]

    # Check TaskStatus enum vs schema status groups
    schema_statuses = set()
    for group_statuses in props["Status"]["groups"].values():
        schema_statuses.update(group_statuses)
    enum_statuses = {s.value for s in TaskStatus}

    for s in schema_statuses - enum_statuses:
        errors.append(f"Status '{s}' in schema but missing from TaskStatus enum")
    for s in enum_statuses - schema_statuses:
        errors.append(f"Status '{s}' in TaskStatus enum but missing from schema")

    # Check TaskType enum vs schema Type options
    schema_types = set(props["Type"]["options"])
    enum_types = {t.value for t in TaskType}

    for t in schema_types - enum_types:
        errors.append(f"Type '{t}' in schema but missing from TaskType enum")
    for t in enum_types - schema_types:
        errors.append(f"Type '{t}' in TaskType enum but missing from schema")

    # Check EnergyLevel enum vs schema Energy options
    schema_energy = set(props["Energy"]["options"])
    enum_energy = {e.value for e in EnergyLevel}

    for e in schema_energy - enum_energy:
        errors.append(f"Energy '{e}' in schema but missing from EnergyLevel enum")
    for e in enum_energy - schema_energy:
        errors.append(f"Energy '{e}' in EnergyLevel enum but missing from schema")

    return errors


def main():
    dry_run = "--dry-run" in sys.argv
    check_enums = "--check-enums" in sys.argv

    schema = load_schema()
    print(f"Loaded schema v{schema['schema_version']} for '{schema['database']['name']}'")
    print(f"  Properties: {len(schema['properties'])}")

    if check_enums or dry_run:
        # Offline validation: check enums match schema
        enum_errors = validate_enums(schema)
        if enum_errors:
            print(f"\nENUM VALIDATION FAILED — {len(enum_errors)} error(s):")
            for err in enum_errors:
                print(f"  - {err}")
            return 1
        print("\nEnum validation passed — mirage_core enums match tasks.yaml")

    if dry_run:
        print("\n--dry-run: Schema parsed successfully. Skipping Notion API check.")
        for name, spec in schema["properties"].items():
            req = "required" if spec.get("required") else "optional"
            print(f"  {name}: {spec['type']} ({req})")
        return 0

    if check_enums:
        return 0

    db_id = schema["database"]["id"]
    print(f"\nFetching live schema from Notion database {db_id}...")
    live_props = fetch_notion_schema(db_id)
    print(f"  Live properties: {len(live_props)}")

    errors = validate(schema, live_props)

    if errors:
        print(f"\nVALIDATION FAILED — {len(errors)} error(s):\n")
        for err in errors:
            print(f"  - {err}")
        return 1
    else:
        print("\nVALIDATION PASSED — schema matches live Notion database.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
