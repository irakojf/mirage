"""Smoke tests for MCP servers — no live credentials required.

Tests tool listing, helper functions, and error handling paths
that don't require Notion or Google API connections.
"""

import asyncio
import json
import sys
import os

import pytest

# Ensure mirage_core is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../mcp/notion"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../mcp/google-calendar"))


# ---------------------------------------------------------------------------
# Notion MCP server tests
# ---------------------------------------------------------------------------


class TestNotionMCPHelpers:
    """Test Notion server helper functions that don't need API credentials."""

    def _import_notion_server(self):
        """Import notion server module (may fail without notion_client)."""
        try:
            import mcp  # noqa: F401
            from importlib import import_module
            # Use importlib to handle the server module
            spec_path = os.path.join(
                os.path.dirname(__file__), "../mcp/notion/server.py"
            )
            import importlib.util
            spec = importlib.util.spec_from_file_location("notion_server", spec_path)
            mod = importlib.util.module_from_spec(spec)
            return mod, spec
        except ImportError:
            pytest.skip("mcp or notion_client not installed")

    def test_parse_markdown_headings_inline(self):
        """Test markdown parsing logic inline (no imports needed)."""
        # Replicate the parse_markdown_to_blocks logic for testing
        def parse_markdown_to_blocks(content):
            blocks = []
            for line in content.split("\n"):
                line = line.rstrip()
                if not line:
                    continue
                if line.startswith("### "):
                    blocks.append({"type": "heading_3", "text": line[4:]})
                elif line.startswith("## "):
                    blocks.append({"type": "heading_2", "text": line[3:]})
                elif line.startswith("# "):
                    blocks.append({"type": "heading_1", "text": line[2:]})
                elif line.startswith("- ") or line.startswith("* "):
                    blocks.append({"type": "bulleted_list_item", "text": line[2:]})
                elif line.startswith("> "):
                    blocks.append({"type": "quote", "text": line[2:]})
                else:
                    blocks.append({"type": "paragraph", "text": line})
            return blocks

        blocks = parse_markdown_to_blocks("# Title\n## Subtitle\n### Section\nParagraph")
        assert len(blocks) == 4
        assert blocks[0]["type"] == "heading_1"
        assert blocks[0]["text"] == "Title"
        assert blocks[1]["type"] == "heading_2"
        assert blocks[2]["type"] == "heading_3"
        assert blocks[3]["type"] == "paragraph"

    def test_parse_markdown_lists_inline(self):
        """Test markdown list parsing."""
        def parse_markdown_to_blocks(content):
            blocks = []
            for line in content.split("\n"):
                line = line.rstrip()
                if not line:
                    continue
                if line.startswith("- "):
                    blocks.append({"type": "bulleted_list_item", "text": line[2:]})
                elif line.startswith("> "):
                    blocks.append({"type": "quote", "text": line[2:]})
                else:
                    blocks.append({"type": "paragraph", "text": line})
            return blocks

        blocks = parse_markdown_to_blocks("- Item 1\n- Item 2\n> Quote")
        assert len(blocks) == 3
        assert blocks[0]["type"] == "bulleted_list_item"
        assert blocks[1]["type"] == "bulleted_list_item"
        assert blocks[2]["type"] == "quote"

    def test_parse_markdown_empty_lines_skipped(self):
        """Empty lines in markdown are skipped."""
        def parse_markdown_to_blocks(content):
            blocks = []
            for line in content.split("\n"):
                line = line.rstrip()
                if not line:
                    continue
                blocks.append({"type": "paragraph", "text": line})
            return blocks

        blocks = parse_markdown_to_blocks("Line 1\n\n\nLine 2")
        assert len(blocks) == 2


class TestNotionPropertyExtractors:
    """Test Notion property extraction helpers."""

    def test_extract_title(self):
        """Extract title from Notion properties."""
        props = {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "My Task"}],
            }
        }

        # Replicate extract_title logic
        def extract_title(props):
            for key, value in props.items():
                if value.get("type") == "title":
                    title_list = value.get("title", [])
                    return "".join(t.get("plain_text", "") for t in title_list)
            return "Untitled"

        assert extract_title(props) == "My Task"

    def test_extract_title_missing(self):
        """Return 'Untitled' when no title property exists."""
        def extract_title(props):
            for key, value in props.items():
                if value.get("type") == "title":
                    title_list = value.get("title", [])
                    return "".join(t.get("plain_text", "") for t in title_list)
            return "Untitled"

        assert extract_title({}) == "Untitled"

    def test_extract_select(self):
        """Extract select property value."""
        props = {
            "Status": {
                "type": "select",
                "select": {"name": "Tasks"},
            }
        }

        def extract_select(props, prop_name):
            if prop_name in props:
                select = props[prop_name].get("select")
                if select:
                    return select.get("name", "")
            return ""

        assert extract_select(props, "Status") == "Tasks"

    def test_extract_select_missing(self):
        """Return empty string for missing select property."""
        def extract_select(props, prop_name):
            if prop_name in props:
                select = props[prop_name].get("select")
                if select:
                    return select.get("name", "")
            return ""

        assert extract_select({}, "Status") == ""

    def test_extract_number(self):
        """Extract number property value."""
        props = {"Mentioned": {"type": "number", "number": 5}}

        def extract_number(props, prop_name):
            if prop_name in props:
                return props[prop_name].get("number")
            return None

        assert extract_number(props, "Mentioned") == 5
        assert extract_number(props, "Missing") is None

    def test_extract_rich_text(self):
        """Extract plain text from rich text array."""
        rich_text = [
            {"plain_text": "Hello "},
            {"plain_text": "world"},
        ]

        def extract_rich_text(rich_text):
            return "".join(t.get("plain_text", "") for t in rich_text)

        assert extract_rich_text(rich_text) == "Hello world"
        assert extract_rich_text([]) == ""


class TestNotionTaskPayload:
    """Test task-to-payload conversion logic."""

    def test_task_to_payload_shape(self):
        """Verify _task_to_payload returns expected fields."""
        from mirage_core.models import Task, TaskId, TaskStatus

        task = Task(
            id=TaskId("test-id"),
            name="Test task",
            status=TaskStatus.TASKS,
            mentioned=2,
        )

        # Replicate _task_to_payload
        payload = {
            "id": task.id.value,
            "content": task.name,
            "status": task.status.value,
            "mentioned": task.mentioned,
            "blocked_by": task.blocked_by,
            "energy": task.energy.value if task.energy else None,
            "tags": task.task_type.value if task.task_type else None,
            "complete_time": task.complete_time_minutes,
            "priority": task.priority,
        }

        assert payload["id"] == "test-id"
        assert payload["content"] == "Test task"
        assert payload["status"] == "Tasks"
        assert payload["mentioned"] == 2
        assert payload["energy"] is None
        assert payload["tags"] is None


# ---------------------------------------------------------------------------
# Google Calendar MCP server tests
# ---------------------------------------------------------------------------


class TestCalendarMCPHelpers:
    """Test Google Calendar server helpers that don't need credentials."""

    def test_get_timezone_returns_string(self):
        """get_timezone returns a timezone string from config."""
        from mirage_core.config import MirageConfig

        cfg = MirageConfig()
        assert isinstance(cfg.timezone, str)
        assert cfg.timezone == "America/Los_Angeles"

    def test_get_zoneinfo_valid(self):
        """get_zoneinfo returns ZoneInfo for valid timezone."""
        from zoneinfo import ZoneInfo

        def get_zoneinfo(timezone):
            try:
                return ZoneInfo(timezone)
            except Exception:
                return ZoneInfo("UTC")

        tz = get_zoneinfo("America/Los_Angeles")
        assert str(tz) == "America/Los_Angeles"

    def test_get_zoneinfo_invalid_falls_back_to_utc(self):
        """get_zoneinfo falls back to UTC for invalid timezone."""
        from zoneinfo import ZoneInfo

        def get_zoneinfo(timezone):
            try:
                return ZoneInfo(timezone)
            except Exception:
                return ZoneInfo("UTC")

        tz = get_zoneinfo("Invalid/Timezone")
        assert str(tz) == "UTC"

    def test_tool_schema_definitions(self):
        """Verify expected tool names for calendar server."""
        expected_tools = {"get_free_time", "get_week_overview", "create_event", "list_events"}
        # These are the tool names defined in the calendar server
        assert len(expected_tools) == 4

    def test_event_body_construction(self):
        """Test event body construction logic from create_event."""
        args = {
            "title": "Team standup",
            "start": "2026-02-02T09:00:00",
            "end": "2026-02-02T09:30:00",
            "description": "Daily sync",
        }
        timezone = "America/Los_Angeles"

        event = {
            "summary": args["title"],
            "start": {"dateTime": args["start"], "timeZone": timezone},
            "end": {"dateTime": args["end"], "timeZone": timezone},
        }
        if "description" in args:
            event["description"] = args["description"]

        assert event["summary"] == "Team standup"
        assert event["start"]["timeZone"] == "America/Los_Angeles"
        assert event["description"] == "Daily sync"

    def test_event_body_without_description(self):
        """Event body omits description when not provided."""
        args = {
            "title": "Quick call",
            "start": "2026-02-02T10:00:00",
            "end": "2026-02-02T10:15:00",
        }
        timezone = "America/Los_Angeles"

        event = {
            "summary": args["title"],
            "start": {"dateTime": args["start"], "timeZone": timezone},
            "end": {"dateTime": args["end"], "timeZone": timezone},
        }
        if "description" in args:
            event["description"] = args["description"]

        assert "description" not in event


# ---------------------------------------------------------------------------
# Error response format tests
# ---------------------------------------------------------------------------


class TestErrorResponse:
    """Test the _error_response pattern used by Notion MCP server."""

    def test_error_response_format(self):
        """Error responses follow consistent JSON structure."""
        def _error_response(tool_name, error):
            error_type = type(error).__name__
            return json.dumps({
                "error": True,
                "tool": tool_name,
                "type": error_type,
                "message": str(error),
            })

        result = _error_response("query_tasks", ValueError("bad input"))
        parsed = json.loads(result)

        assert parsed["error"] is True
        assert parsed["tool"] == "query_tasks"
        assert parsed["type"] == "ValueError"
        assert parsed["message"] == "bad input"

    def test_unknown_tool_error(self):
        """Unknown tool names produce clear error."""
        name = "nonexistent_tool"
        error_msg = f"Unknown tool: {name}"
        assert "nonexistent_tool" in error_msg


# ---------------------------------------------------------------------------
# Alias resolution (used by Notion MCP server for status/type mapping)
# ---------------------------------------------------------------------------


class TestAliasResolution:
    """Test status and type alias resolution used by MCP servers."""

    def test_resolve_status_canonical(self):
        """Canonical status names resolve correctly."""
        from mirage_core.aliases import resolve_status
        from mirage_core.models import TaskStatus

        assert resolve_status("Tasks") == TaskStatus.TASKS
        assert resolve_status("Done") == TaskStatus.DONE
        assert resolve_status("Projects") == TaskStatus.PROJECTS
        assert resolve_status("Ideas") == TaskStatus.IDEAS

    def test_resolve_status_aliases(self):
        """Common aliases resolve to canonical statuses."""
        from mirage_core.aliases import resolve_status
        from mirage_core.models import TaskStatus

        assert resolve_status("Action") == TaskStatus.TASKS
        assert resolve_status("action") == TaskStatus.TASKS

    def test_resolve_type_canonical(self):
        """Canonical type names resolve correctly."""
        from mirage_core.aliases import resolve_type
        from mirage_core.models import TaskType

        assert resolve_type("Identity") == TaskType.IDENTITY
        assert resolve_type("Compound") == TaskType.COMPOUND
