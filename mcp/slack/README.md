# Mirage Slack Bot

Capture tasks directly from Slack by @mentioning Mirage or sending DMs.

## Architecture

```
Slack → fly.io (this server) → Claude Opus → Turso (SQLite cloud)
                                                    ↑
                                     Local Claude Code ─┘
```

## Setup

### 1. Turso Database

```bash
# Install CLI
brew install tursodatabase/tap/turso

# Login
turso auth login

# Create database
turso db create mirage

# Get credentials
turso db show mirage --url        # → TURSO_DATABASE_URL
turso db tokens create mirage     # → TURSO_AUTH_TOKEN

# Initialize schema
turso db shell mirage < ../../data/schema.sql
```

### 2. Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: `Mirage`, select your workspace

**Bot Token Scopes** (OAuth & Permissions):
- `chat:write` - Send messages
- `commands` - Handle slash commands

**Slash Commands**:
1. Go to "Slash Commands" in sidebar
2. Click "Create New Command"
3. Command: `/mirage`
4. Request URL: `https://mirage-slack.fly.dev/slack/commands` (set after deploy)
5. Short Description: `Capture a task privately`
6. Usage Hint: `[task description]`

**Install to Workspace** and save:
- `SLACK_BOT_TOKEN` (starts with `xoxb-`)
- `SLACK_SIGNING_SECRET` (from Basic Information)

### 3. Deploy to fly.io

```bash
cd mcp/slack

# First time setup
fly launch --no-deploy

# Set secrets
fly secrets set SLACK_BOT_TOKEN=xoxb-your-token
fly secrets set SLACK_SIGNING_SECRET=your-signing-secret
fly secrets set ANTHROPIC_API_KEY=sk-ant-your-key
fly secrets set TURSO_DATABASE_URL=libsql://mirage-xxx.turso.io
fly secrets set TURSO_AUTH_TOKEN=your-turso-token

# Deploy
fly deploy

# Check logs
fly logs
```

### 4. Update Slack Event URL

After deploy, go back to your Slack app:
1. Event Subscriptions → Request URL
2. Enter: `https://mirage-slack.fly.dev/slack/events`
3. Slack will verify the endpoint

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_SIGNING_SECRET=...
export ANTHROPIC_API_KEY=sk-ant-...
export TURSO_DATABASE_URL=libsql://...
export TURSO_AUTH_TOKEN=...

# Run server
python server.py

# In another terminal, expose with ngrok
ngrok http 3000

# Update Slack Event URL to ngrok URL
```

## Usage

Use `/mirage` anywhere in Slack - it's completely private (nobody else sees it).

**Capture a task:**
```
/mirage call mom tomorrow
/mirage finish quarterly report by Friday
/mirage blocked on design review from Sarah
```

**From a thread context:**
```
/mirage follow up on design feedback from this thread
/mirage Sarah needs budget approval - waiting on her
```

## Response Format

**New task:**
```
Got it!

"Call mom tomorrow"
action | 5 min
[DO IT]
```

**Duplicate task:**
```
Already tracking this!

"Call mom tomorrow" (mentioned 3x)
Flagged for procrastination review
```

## Troubleshooting

**Slash command not working:**
- Verify the Request URL is correct: `https://mirage-slack.fly.dev/slack/commands`
- Check `fly logs` for errors
- Ensure the app is reinstalled after adding the slash command

**"dispatch_failed" error:**
- Server not running - check `fly status`
- Wrong URL configured - verify `/slack/commands` endpoint

**Database errors:**
- Verify Turso credentials
- Check schema is initialized: `turso db shell mirage "SELECT COUNT(*) FROM tasks"`
