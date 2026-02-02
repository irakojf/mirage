# Setup Guide

## Prerequisites

- Python 3.10+
- Notion account with a workspace
- Google Calendar (for calendar features)
- Slack workspace (for mobile capture)
- fly.io account (for Slack bot hosting)

## 1. Notion Setup

### Create Integration

1. Go to https://www.notion.so/my-integrations
2. Create a new integration for your workspace
3. Copy the "Internal Integration Secret" — this is your `NOTION_TOKEN`

### Share Databases

Share these databases with your integration:

| Database | ID | Purpose |
|----------|-----|---------|
| Mirage Tasks | `2ea35d23-b569-80cc-99be-e6d6a17b1548` | Task storage |
| Mirage Reviews | `2eb35d23-b569-8040-859f-d5baff2957ab` | Weekly reviews |

Also share the Identity page: `2eb35d23b569808eb1ecc18dc3903100`

### Validate Schema

```bash
# Check schema parses correctly
python schema/validate.py --dry-run

# Validate against live Notion (requires NOTION_TOKEN)
NOTION_TOKEN=secret_... python schema/validate.py
```

## 2. MCP Servers

Both MCP servers are Python and run over stdio. Configure in your MCP settings (`.claude/settings.json` or project config).

See [MCP Contracts](mcp-contracts.md) for full tool inputs/outputs.

### Google Calendar

```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "python",
      "args": ["mcp/google-calendar/server.py"],
      "env": {
        "NOTION_TOKEN": "secret_..."
      }
    }
  }
}
```

Requires Google OAuth credentials at `~/.config/mirage/credentials.json` (download from Google Cloud Console).

### Notion

```json
{
  "mcpServers": {
    "notion": {
      "command": "python",
      "args": ["mcp/notion/server.py"],
      "env": {
        "NOTION_TOKEN": "secret_..."
      }
    }
  }
}
```

## 3. Slack Bot Setup

See [Slack README](../mcp/slack/README.md) for full setup including scopes, event subscriptions, and message shortcuts.

### Quick Version

1. Go to https://api.slack.com/apps → Create New App → From scratch → Name: `Mirage`
2. Add Bot Token Scopes: `chat:write`, `commands`, `reactions:write`, `channels:history`, `groups:history`, `im:history`, `im:read`, `im:write`, `app_mentions:read`
3. Add Slash Commands: `/mirage`, `/prioritize`, `/plan`, `/review`
4. Enable Events: `app_mention`, `message.im`
5. Enable Interactivity + message shortcut (`capture_with_mirage`)

### Deploy to fly.io

```bash
cd mcp/slack
fly launch --no-deploy
fly secrets set SLACK_BOT_TOKEN=xoxb-...
fly secrets set SLACK_SIGNING_SECRET=...
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly secrets set NOTION_TOKEN=secret_...
fly deploy
```

### Verify

```bash
fly logs  # Check for startup errors
```

Test with `/mirage test task` in Slack.

## 4. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NOTION_TOKEN` | yes | — | Notion integration secret |
| `MIRAGE_TASKS_DB` | no | see `MirageConfig` | Tasks database ID (validated as UUID) |
| `MIRAGE_REVIEWS_DB` | no | see `MirageConfig` | Reviews database ID (validated as UUID) |
| `MIRAGE_CALENDAR_DB` | no | see `MirageConfig` | Production calendar database ID |
| `MIRAGE_IDENTITY_PAGE` | no | see `MirageConfig` | Identity page ID (validated as UUID) |
| `MIRAGE_TIMEZONE` | no | America/Los_Angeles | Timezone |
| `MIRAGE_WORK_START` | no | 09:00 | Workday start |
| `MIRAGE_WORK_END` | no | 18:00 | Workday end |
| `MIRAGE_BUFFER_MINUTES` | no | 15 | Calendar buffer |
| `MIRAGE_MORNING_PROTECTION_END` | no | 10:00 | Morning block cutoff |
| `MIRAGE_PROCRASTINATION_THRESHOLD` | no | 3 | Mentioned count to flag |

Defaults for all Notion IDs live in `mirage_core/config.py::MirageConfig`. Set env vars to override.

## 5. Running Tests

```bash
PYTHONPATH=. python -m pytest tests/ -v
```
