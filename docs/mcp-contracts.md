# MCP Server Contracts

Reference for all MCP tool inputs, outputs, and error handling.

## Notion MCP Server (`mcp/notion/server.py`)

Transport: stdio
Env required: `NOTION_TOKEN`

### `get_production_calendar`

Fetch upcoming items from the Production Calendar database.

**Input:**
```json
{
  "days_ahead": 14,         // integer, optional (default: 14)
  "status_filter": "Draft"  // string, optional
}
```

**Output:**
```json
{
  "calendar": "Production Calendar",
  "period": "2026-02-02 to 2026-02-16",
  "items": [
    {
      "id": "page-uuid",
      "title": "Blog post: Atomic Habits recap",
      "date": "2026-02-10",
      "status": "Draft",
      "url": "https://notion.so/..."
    }
  ],
  "count": 1
}
```

### `get_notion_page`

Fetch any Notion page content as markdown.

**Input:**
```json
{
  "page_id": "2eb35d23b569808eb1ecc18dc3903100"  // string, required
}
```

**Output:**
```json
{
  "page_id": "2eb35d23b569808eb1ecc18dc3903100",
  "url": "https://notion.so/...",
  "content": "# Identity\n\n- I am someone who..."
}
```

### `query_tasks`

Query tasks with optional status filter.

**Input:**
```json
{
  "status_filter": "Tasks",  // string, optional — Tasks | Projects | Ideas | Blocked | Not Now | Waiting On | Done | Won't Do
  "exclude_done": true       // boolean, optional (default: false)
}
```

**Output:**
```json
{
  "tasks": [
    {
      "id": "page-uuid",
      "content": "Call mom",
      "status": "Tasks",
      "mentioned": 2,
      "blocked_by": null,
      "energy": "Green",
      "tags": "Do It Now",
      "complete_time": 5,
      "priority": 1,
      "created_time": "2026-01-28T10:00:00+00:00",
      "url": "https://notion.so/..."
    }
  ],
  "count": 1
}
```

**Field notes:**
- `tags` is the Notion `Type` select value (single string, not an array): `Identity`, `Compound`, `Do It Now`, `Never Miss 2x`, `Important Not Urgent`, `Unblocks`
- `energy` is `Red`, `Yellow`, `Green`, or `null`
- `complete_time` is minutes (positive integer) or `null`
- `priority` is rank (1 = highest) or `null`

### `create_task`

Create a task in the Mirage tasks database. The name is auto-normalized (leading bullets stripped, whitespace collapsed).

**Input:**
```json
{
  "content": "Call mom",                // string, required
  "status": "Tasks",                    // string, required — accepts aliases: Action→Tasks, Project→Projects, Idea→Ideas
  "blocked_by": "Sarah",               // string, optional
  "tag": "Do It Now",                  // string, optional — Identity | Compound | Do It Now | Never Miss 2x | Important Not Urgent | Unblocks
  "complete_time": 5                   // integer (minutes), optional
}
```

**Output (success):**
```json
{
  "success": true,
  "id": "page-uuid",
  "content": "Call mom",
  "status": "Tasks",
  "mentioned": 1,
  "blocked_by": null,
  "energy": null,
  "tags": "Do It Now",
  "complete_time": 5,
  "priority": null,
  "created_time": "2026-02-02T10:00:00+00:00",
  "url": "https://notion.so/..."
}
```

### `update_task`

Update any combination of task fields. Only supplied fields are changed.

**Input:**
```json
{
  "page_id": "page-uuid",      // string, required
  "content": "Call mom today",  // string, optional
  "status": "Done",            // string, optional
  "mentioned": 3,              // integer, optional
  "blocked_by": "",            // string, optional (empty string clears)
  "energy": "Green",           // string, optional — Red | Yellow | Green
  "tag": "Identity",           // string, optional
  "complete_time": 10,         // integer (minutes), optional
  "priority": 1                // integer (1 = highest), optional
}
```

**Output (success):** Same shape as `create_task` output with `"success": true`.

### `increment_task_mention`

Bump the Mentioned counter by 1 (procrastination tracking).

**Input:**
```json
{
  "page_id": "page-uuid"  // string, required
}
```

**Output:**
```json
{
  "success": true,
  "id": "page-uuid",
  "content": "Call mom",
  "previous_count": 2,
  "new_count": 3
}
```

### `create_review`

Save a weekly review record.

**Input:**
```json
{
  "week_of": "2026-01-27",                    // string (YYYY-MM-DD), required
  "transcript": "Full review conversation...", // string, required
  "wins": "Shipped new feature",              // string, optional
  "struggles": "Energy was low mid-week",     // string, optional
  "next_week_focus": "Clear blocked items",   // string, optional
  "tasks_completed": 12                       // integer, optional
}
```

**Output:**
```json
{
  "success": true,
  "id": "page-uuid",
  "week_of": "2026-01-27",
  "url": "https://notion.so/..."
}
```

### `update_page_content`

Replace all blocks on a Notion page with new markdown content. Supports headings (`#`, `##`, `###`), bullets (`-`, `*`), numbered lists (`1.`), quotes (`>`), and paragraphs.

**Input:**
```json
{
  "page_id": "page-uuid",                          // string, required
  "content": "# Updated Title\n\n- Item one\n- Item two"  // string (markdown), required
}
```

**Output:**
```json
{
  "success": true,
  "page_id": "page-uuid",
  "blocks_added": 3
}
```

---

## Google Calendar MCP Server (`mcp/google-calendar/server.py`)

Transport: stdio
Auth: Google OAuth2 (credentials at `~/.config/mirage/credentials.json`, token cached at `~/.config/mirage/token.json`)

### `get_free_time`

Get available free blocks for a specific day.

**Input:**
```json
{
  "date": "2026-02-02",    // string (YYYY-MM-DD), optional (default: today)
  "work_start": "09:00",   // string (HH:MM), optional (default: from config)
  "work_end": "18:00"      // string (HH:MM), optional (default: from config)
}
```

**Output:**
```json
{
  "date": "2026-02-02",
  "total_free_minutes": 360,
  "total_free_hours": 6.0,
  "free_blocks": [
    {
      "start": "09:00",
      "end": "10:30",
      "duration_minutes": 90
    },
    {
      "start": "14:00",
      "end": "18:00",
      "duration_minutes": 240
    }
  ]
}
```

### `get_week_overview`

Get busy/free summary for the next 7 days.

**Input:**
```json
{
  "work_start": "09:00",  // string (HH:MM), optional
  "work_end": "18:00"     // string (HH:MM), optional
}
```

**Output:**
```json
{
  "week_start": "2026-02-02",
  "total_free_hours": 32.5,
  "days": [
    {
      "date": "2026-02-02",
      "day": "Monday",
      "free_hours": 6.0
    }
  ]
}
```

### `create_event`

Create a new calendar event.

**Input:**
```json
{
  "title": "Focus: quarterly report",                // string, required
  "start": "2026-02-02T14:00:00",                   // string (ISO datetime), required
  "end": "2026-02-02T15:30:00",                     // string (ISO datetime), required
  "description": "Deep work block for Q1 report"    // string, optional
}
```

**Output:** Plain text with event link:
```
Event created: https://www.google.com/calendar/event?eid=...
```

### `list_events`

List calendar events for a date range.

**Input:**
```json
{
  "start_date": "2026-02-02",  // string (YYYY-MM-DD), optional (default: today)
  "end_date": "2026-02-09"    // string (YYYY-MM-DD), optional (default: start + 7 days)
}
```

**Output:**
```json
[
  {
    "title": "Team standup",
    "start": "2026-02-02T09:00:00-08:00",
    "end": "2026-02-02T09:30:00-08:00"
  }
]
```

---

## Error Format

Both servers return errors as JSON on failure:

```json
{
  "error": true,
  "tool": "create_task",
  "type": "ValidationError",
  "message": "Task name cannot be empty"
}
```

The Google Calendar server falls back to plain text errors: `"Error: <message>"`.

---

## Enum Reference

### TaskStatus
`Tasks` | `Projects` | `Ideas` | `Not Now` | `Blocked` | `Waiting On` | `Done` | `Won't Do`

Aliases accepted on create/update: `Action` → `Tasks`, `Project` → `Projects`, `Idea` → `Ideas`

### TaskType (tag)
`Identity` | `Compound` | `Do It Now` | `Never Miss 2x` | `Important Not Urgent` | `Unblocks`

### EnergyLevel
`Red` | `Yellow` | `Green`
