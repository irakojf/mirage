# Integration Test Plan

Manual checklist for validating Notion and Calendar integration end-to-end.

## Prerequisites

- `NOTION_TOKEN` set with access to test databases
- Google Calendar MCP server running
- Slack bot deployed (for Slack tests)

## 1. Notion Task CRUD

### Create
- [ ] `/mirage buy groceries` creates task in Notion with Status=Tasks
- [ ] Task name is normalized (no bullets, collapsed whitespace)
- [ ] Mentioned defaults to 1
- [ ] Blocked field populated when `blocked_by` provided
- [ ] Type field set when tag provided (Identity, Compound, etc.)
- [ ] Complete Time written when estimated_minutes provided
- [ ] Energy field set when provided (Red, Yellow, Green)
- [ ] AI tag `[DO IT]` maps to Type=Do It Now via `from_ai_output`
- [ ] AI tag `[KEYSTONE]` maps to Type=Unblocks via `from_ai_output`
- [ ] AI bucket `action` without estimate defaults to 5 min
- [ ] AI bucket `project` drops any estimate (stored as None)

### Read
- [ ] `query_tasks` returns all open tasks
- [ ] `query_tasks(exclude_done=True)` excludes Done and Won't Do
- [ ] `query_tasks(status_filter="Blocked")` returns only Blocked tasks
- [ ] Status aliases work: "Action" → Tasks, "Project" → Projects
- [ ] All properties round-trip: what you write is what you read

### Update
- [ ] `update_task` changes Status correctly
- [ ] `update_task` changes Priority correctly
- [ ] `update_task` changes Energy correctly
- [ ] Status uses `status` API (not `select`) for writes

### Increment Mention
- [ ] `increment_task_mention` increases Mentioned by 1
- [ ] Duplicate task detection increments instead of creating
- [ ] AI-flagged duplicate with stale ID falls through to IngestionService dedup

## 2. Notion Schema Validation

- [ ] `python schema/validate.py --dry-run` passes
- [ ] `python schema/validate.py --check-enums` passes (enum alignment)
- [ ] `python schema/validate.py` passes against live Notion
- [ ] `python schema/kanban_sync.py --dry-run` parses views spec
- [ ] `python schema/kanban_sync.py` integrity check passes

## 3. Calendar Integration

### Free Time
- [ ] `get_free_time` returns windows for today
- [ ] Windows have correct start/end times
- [ ] Work hours respected (default 09:00–18:00)

### Week Overview
- [ ] `get_week_overview` returns 5–7 days
- [ ] Free hours are reasonable (not negative, not >24/day)

### Calendar-Aware Do Now
- [ ] `/prioritize` shows tasks that fit in available time
- [ ] Tasks with `complete_time > available_slot` are filtered out
- [ ] Tasks without time estimate still appear
- [ ] When calendar is unavailable, all tasks shown (graceful degradation)

## 4. Prioritization

- [ ] 2-minute tasks get `[DO IT]` tag
- [ ] Identity tasks get `[IDENTITY]` tag
- [ ] Tasks mentioned 3+ times get `[PROCRASTINATING]` tag
- [ ] Manual priority (Priority field set) sorts first
- [ ] Done/Won't Do tasks excluded from results
- [ ] Suggested reasons are human-readable

## 5. Weekly Review

- [ ] `ReviewService.gather_review_data()` returns data
- [ ] Completed count matches recent Done tasks
- [ ] Procrastination list includes mentioned 3+ items
- [ ] Energy breakdown matches task energy fields
- [ ] Stale decisions include items older than 14 days
- [ ] `persist_review` saves to Notion reviews database
- [ ] Review insights generated (non-empty list)

### Structured Insights (`generate_insights`)
- [ ] Returns `ReviewInsightsSummary` with typed `ReviewInsight` objects
- [ ] Each insight has `category`, `severity`, `message`, and `data`
- [ ] Workload insight shows total estimated hours across open tasks
- [ ] Workload insight counts unestimated tasks separately
- [ ] Procrastination insight escalates to CRITICAL at 6+ mentions
- [ ] Energy drain warning fires when >50% of completed tasks are Red
- [ ] Staleness warning fires when 3+ items are older than 14 days
- [ ] Override warning fires when >50% of tasks have manual priority
- [ ] Zero-completion week produces a WARNING-severity velocity insight
- [ ] `ReviewData.insights` (plain text) matches `generate_insights().messages`

## 6. Slack Commands

- [ ] `/mirage <text>` captures task and shows confirmation
- [ ] `/mirage` routes through `CaptureRequest.from_ai_output` → `IngestionService`
- [ ] `/prioritize` shows ranked task list
- [ ] `/plan` shows day plan with time estimates
- [ ] `/review` shows weekly snapshot
- [ ] Duplicate detection works (shows "Already tracking")
- [ ] Message shortcut "Capture with Mirage" works in threads
- [ ] Error responses are JSON with `error`, `tool`, `type`, `message` keys

## 7. Error Handling

- [ ] Invalid status string returns clear error
- [ ] Missing required fields return clear error
- [ ] Notion API timeout handled gracefully
- [ ] Calendar API unavailable → system continues without calendar
- [ ] Error hook receives (exception, context_dict) when set

## Execution

- **Automated tests**: `PYTHONPATH=. python -m pytest tests/ -v`
- **Live tests**: Run checklist manually against real Notion workspace
- **Isolation**: Use a test database if available; avoid modifying production tasks

## 8. Ingestion Pipeline (core → Notion round-trip)

- [ ] `CaptureRequest.from_ai_output()` accepts minimal dict `{"content": "...", "bucket": "action"}`
- [ ] `from_ai_output` with unknown tags produces `tag=None` (no error)
- [ ] `IngestionService.ingest()` creates task in Notion
- [ ] `IngestionService.ingest()` detects exact-match duplicate and increments mentioned
- [ ] `IngestionService.ingest_batch()` processes multiple requests sequentially
- [ ] Normalized name matches after round-trip (write → read → compare)

## 9. Telemetry / Error Hooks

- [ ] `capture_error(exc, ctx)` invokes registered handler
- [ ] Errors include context dict with `tool`, `type`, `message`
- [ ] No handler registered → error logged, no crash

## Exit Criteria

- All automated tests pass (currently 186)
- All manual checklist items verified
- No new warnings in logs
- Schema validation passes against live Notion
