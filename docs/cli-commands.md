# CLI Command Reference

Quick reference for capture, prioritize, plan, and review flows.

## Surfaces

| Surface | Commands | Purpose |
|---------|----------|---------|
| Slack | `/mirage`, `/dump`, `/done` | Fast capture from phone/desktop |
| Claude Code | `/dump`, `/done`, `/prioritize`, `/identity`, `/review` | Full workflow |

## Capture

### `/dump`

Start a brain dump session. Capture everything on your mind conversationally.

Available in both Slack and Claude Code.

### `/done`

End a brain dump session. Processes and categorizes all captured tasks into Notion.

### `/mirage [task]` (Slack only)

Capture a single task:
```
/mirage call mom tomorrow
/mirage blocked on design review from Sarah
```

## Prioritize

### `/prioritize`

Triage tasks: review Projects, check blocked items, and update the Do Now list.

Applies the prioritization engine with these tags:

| Tag | Trigger | Score Impact |
|-----|---------|--------------|
| `[DO IT]` | complete_time <= 2 min | -30 (highest) |
| `[NEVER MISS 2x]` | Type = Never Miss 2x | -25 |
| `[IDENTITY]` | Type = Identity | -20 |
| `[KEYSTONE]` | Type = Unblocks | -20 |
| `[PROCRASTINATING]` | Mentioned >= 3 | -15 |
| `[STALE]` | Created 14+ days ago | -10 |
| `[COMPOUNDS]` | Type = Compound or Important Not Urgent | -10 |

Manual priority overrides sort first. Lower score = higher priority.

## Identity

### `/identity`

Set and update identity goals — who you want to become.

Categories: Love, Relationships, Work, Health, Wealth.

Identity statements are stored in a Notion page and used during prioritization to tag identity-aligned tasks.

## Review

### `/review`

Weekly review — reflect on what happened and plan ahead.

Generates:
- Completed task summary with energy breakdown
- Procrastination watch list (mentioned 3+ or stale 14+ days)
- Stale decisions (Not Now items older than 14 days)
- Override patterns (manual vs auto priority)
- Coaching questions from Atomic Habits principles

## Plan

Planning is calendar-aware. After prioritization, ask for a plan that fits into available free time and respects buffer rules.

```
Plan today from the top 3 priorities.
Fit these tasks into my calendar for tomorrow.
```

## Notion MCP Tools

| Tool | Purpose |
|------|---------|
| `mcp__notion__query_tasks` | Fetch tasks with optional status/done filters |
| `mcp__notion__create_task` | Create a new task |
| `mcp__notion__update_task` | Update task properties |
| `mcp__notion__increment_task_mention` | Increment procrastination counter |
| `mcp__notion__create_review` | Save weekly review with transcript |
| `mcp__notion__get_production_calendar` | Check production/content calendar |
| `mcp__notion__get_notion_page` | Read any Notion page by ID |

## Google Calendar MCP Tools

| Tool | Purpose |
|------|---------|
| `mcp__google-calendar__get_free_time` | Get free time blocks for a date |
| `mcp__google-calendar__get_week_overview` | Get busy/free summary for the week |
| `mcp__google-calendar__create_event` | Create a calendar event |
| `mcp__google-calendar__list_events` | List events for a date range |
