# QA Playbook

Human test scripts for critical flows. Run before merging behavioral changes, cutting releases, or after schema migrations.

## Prerequisites

```bash
# Automated tests pass
PYTHONPATH=. python -m pytest tests/ -v

# Lint clean
ruff check . && ruff format --check .

# Schema validates (dry run first, then live)
python schema/validate.py --dry-run
NOTION_TOKEN=secret_... python schema/validate.py
```

If any of these fail, fix before proceeding to manual tests.

---

## Flow 1: Task Capture via Slack `/mirage`

**Tests the full path: Slack → Claude API → Notion write → ephemeral response.**

### 1a. New task

1. Open Slack, type: `/mirage buy milk on the way home`
2. Verify ephemeral response appears (only you see it):
   ```
   Got it!

   "Buy milk on the way home"
   Tasks | 5 min
   ```
3. Open Notion tasks database → confirm the task exists with:
   - Name: "Buy milk on the way home" (normalized — no bullets, clean whitespace)
   - Status: Tasks
   - Mentioned: 1
   - Complete Time: a number (Claude estimates)

### 1b. Duplicate detection

1. Type again: `/mirage buy milk`
2. Verify response says "Already tracking" with incremented mention count
3. Open Notion → confirm Mentioned count increased by 1 (no new row created)

### 1c. Blocked task

1. Type: `/mirage waiting on Sarah for the design mockups`
2. Verify response shows status as Blocked (or Waiting On)
3. Open Notion → confirm Blocked By field is populated

### 1d. Empty input

1. Type: `/mirage` (no text)
2. Verify usage hint appears: "Usage: `/mirage <task>`"

---

## Flow 2: Message Shortcut

**Tests: right-click capture → thread context → DM with permalink.**

### 2a. Single message

1. Find any message in a Slack channel
2. Right-click → "Capture with Mirage"
3. Verify:
   - 👀 reaction appears on the message
   - Task is created in Notion
   - You receive a DM from Mirage with the task name + permalink to the original message

### 2b. Thread capture

1. Find a thread with 3+ messages
2. Right-click the parent message → "Capture with Mirage"
3. Verify:
   - Claude reads the full thread and extracts a single action item
   - Task name is a summary, not just the clicked message
   - Notion task is created

---

## Flow 3: @mirage in Threads

1. Go to any thread and type: `@mirage`
2. Verify:
   - 👀 reaction appears
   - Ephemeral message confirms capture
   - Notion task is created with thread context summarized
3. Try `@mirage` outside a thread (top-level message)
4. Verify: ephemeral message says "Tag me in a thread to capture the conversation as a task."

---

## Flow 4: DM Capture

1. Open a DM with Mirage
2. Type: `schedule dentist appointment`
3. Verify:
   - 👀 reaction appears
   - Task created in Notion

---

## Flow 5: `/prioritize`

**Tests: task query → priority scoring → formatted output.**

1. Ensure at least 3–5 tasks exist in Notion with varying properties:
   - One with Priority=1 (manual override)
   - One with Mentioned ≥ 3 (procrastination flag)
   - One with tag=Do It Now
   - One with tag=Identity
2. Type: `/prioritize`
3. Verify:
   - Ranked list appears (up to 5 items)
   - Manual priority task sorts first
   - Tags are shown next to task names
   - Each item has a reason string
4. If no open tasks exist, verify: "No open tasks to prioritize."

---

## Flow 6: `/plan`

**Tests: prioritization + calendar fit + time estimates.**

1. Ensure tasks have `complete_time` values set in Notion
2. Type: `/plan`
3. Verify:
   - Output shows "Day plan (X min capacity)"
   - Tasks are listed with time estimates
   - "Remaining: X min" shown at bottom
   - Tasks without estimates listed under "Unscheduled"
4. With no estimated tasks: verify "No estimated tasks fit into the plan."

---

## Flow 7: `/review`

**Tests: review data gathering → snapshot formatting.**

1. Mark at least 2 tasks as Done in Notion
2. Type: `/review`
3. Verify output includes:
   - "Completed: N" (matches your Done count)
   - Energy breakdown: "green X, yellow Y, red Z, unrated W"
   - Procrastination items (if any tasks have Mentioned ≥ 3)
   - Stale decisions count (if any)

---

## Flow 8: Notion MCP (via Claude Code)

**Tests the MCP tools used by local Claude Code sessions.**

Run these in a Claude Code session or via MCP client:

### 8a. Query

```
mcp__notion__query_tasks(exclude_done=true)
```
- Returns JSON with `tasks` array and `count`
- No Done/Won't Do tasks in results

### 8b. Create

```
mcp__notion__create_task(content="QA test task", status="Tasks", complete_time=5)
```
- Returns JSON with `success: true` and full task payload
- Task visible in Notion

### 8c. Update

```
mcp__notion__update_task(page_id="<id from 8b>", status="Done")
```
- Returns updated payload with `status: "Done"`
- Notion reflects the change

### 8d. Increment mention

```
mcp__notion__increment_task_mention(page_id="<id from 8b>")
```
- Returns `previous_count` and `new_count` (new = previous + 1)

### 8e. Cleanup

Delete the QA test task from Notion manually (or set status to Won't Do).

---

## Flow 9: Google Calendar MCP

### 9a. Free time

```
get_free_time(date="<today's date>")
```
- Returns `free_blocks` with start/end times and durations
- `total_free_minutes` is non-negative
- Times fall within work hours (default 09:00–18:00)

### 9b. Week overview

```
get_week_overview()
```
- Returns 7 days with `free_hours` for each
- No negative hours

### 9c. Calendar unavailable

- Stop the Google Calendar MCP server
- Run `/prioritize` via Slack
- Verify: tasks still appear (graceful degradation, no crash)

---

## Flow 10: Error Handling

### 10a. Invalid status

```
mcp__notion__create_task(content="test", status="InvalidStatus")
```
- Returns error JSON with `type` and `message`

### 10b. Empty task name

```
mcp__notion__create_task(content="", status="Tasks")
```
- Returns error: "Task name cannot be empty"

### 10c. Bad page ID

```
mcp__notion__update_task(page_id="nonexistent-uuid")
```
- Returns error (not a crash or 500)

---

## Failure Triage

| Symptom | Check |
|---------|-------|
| Slash command returns nothing | `fly logs` for errors; verify Request URL |
| "dispatch_failed" | Server down — `fly status`; redeploy if needed |
| Task not in Notion | Check `NOTION_TOKEN` and database sharing |
| Wrong status written | Check `mirage_core/aliases.py` mapping |
| Calendar returns empty | Check Google OAuth token at `~/.config/mirage/token.json` |
| Schema validation fails | Compare `schema/tasks.yaml` with live Notion properties |

## Recording Results

Log results in PR description or release notes:
- Flows tested (by number)
- Failures found and how resolved
- Any skipped flows and why
