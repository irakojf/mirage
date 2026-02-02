# Logging Guidelines

Goal: logs should explain what happened without leaking secrets.

## Principles

- Use structured logs (`logger.info("message", extra={...})` or dict payloads)
- Include identifiers: task_id, project_id, review_id when available
- Never log secrets or tokens
- Log failures with enough context to reproduce

## Levels

- DEBUG: noisy, local-only troubleshooting
- INFO: state transitions and successful operations
- WARNING: recoverable failures or retries
- ERROR: user-visible failure or data loss risk

## Required Context Fields

- `source`: which adapter or system
- `operation`: the action taken (create_task, update_task, list_events)
- `duration_ms`: elapsed time when possible

## Redaction Policy

**Never log:**
- API tokens or secrets (NOTION_TOKEN, SLACK_BOT_TOKEN, ANTHROPIC_API_KEY)
- Full user messages or task content in production (truncate to 50 chars max)
- Slack user IDs in combination with message content
- Google Calendar event details beyond title

**Safe to log:**
- Notion page IDs (opaque UUIDs)
- Task status transitions
- Operation names and durations
- Error types and messages (but not stack traces at INFO level)
- Counts (task count, mention count)

**Truncation rule:** When logging user-provided text (task names, messages), truncate to 50 characters with `text[:50]` and append `...` to indicate truncation.

## Examples

- Good: `logger.info("notion.create_task succeeded", extra={"task_id": task.id, "duration_ms": 120})`
- Bad: `logger.info(f"created task: {full_task_content}")` — leaks user content
