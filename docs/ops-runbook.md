# Operations Runbook

## Services

| Service | Host | Stack |
|---------|------|-------|
| Slack Bot | fly.io (`mirage-slack`) | Python, Flask |
| Notion MCP | Local (Claude Code) | Node.js |
| Google Calendar MCP | Local (Claude Code) | Node.js |

## Slack Bot (fly.io)

### Check Status

```bash
fly status -a mirage-slack
fly logs -a mirage-slack
```

### Restart

```bash
fly apps restart mirage-slack
```

### Deploy

```bash
cd mcp/slack
fly deploy
```

### Update Secrets

```bash
fly secrets set SLACK_BOT_TOKEN=xoxb-new-token -a mirage-slack
fly secrets list -a mirage-slack
```

### Rollback

```bash
fly releases -a mirage-slack       # List releases
fly deploy --image <previous-image> -a mirage-slack
```

## Notion

### Validate Schema

```bash
NOTION_TOKEN=secret_... python schema/validate.py
```

### Check Integrity

```bash
NOTION_TOKEN=secret_... python schema/kanban_sync.py
```

### Export View Config

```bash
NOTION_TOKEN=secret_... python schema/kanban_sync.py --export-views
```

Output saved to `schema/views_snapshot.json`.

### Common Issues

**"property not found" errors:** Schema drift. Run `schema/validate.py` to identify missing properties, then add them in Notion.

**Status writes failing:** Notion status type requires exact string match. Check `schema/tasks.yaml` for canonical values. Common mistake: using `select` API instead of `status` API.

## Google Calendar

### Verify Connection

Use Claude Code:
```
Check my free time today
```

If calendar is unavailable, the system degrades gracefully — Do Now list skips calendar filtering.

### Common Issues

**"Calendar unavailable" warnings:** Check that the Google Calendar MCP server is running and authenticated. Re-authenticate if OAuth token expired.

## Testing

### Run Full Suite

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

### Run Specific Module

```bash
PYTHONPATH=. python -m pytest tests/test_calendar.py -v
PYTHONPATH=. python -m pytest tests/test_prioritization.py -v
PYTHONPATH=. python -m pytest tests/test_ingestion.py -v
```

## Pre-Deploy Checklist

1. All tests pass: `PYTHONPATH=. python -m pytest tests/ -v`
2. Schema validates: `python schema/validate.py --dry-run`
3. No secrets in code: check `.env`, `.gitignore`
4. Slack bot health: `fly status -a mirage-slack`
5. Notion integrity: `python schema/kanban_sync.py` (if token available)
