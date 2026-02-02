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

## Examples

- Good: "notion.create_task succeeded", {task_id, duration_ms}
- Bad: "failed to create task" with no task_id or error details
