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
- `app_mentions:read` - Receive @mirage mentions
- `chat:write` - Send messages
- `im:history` - Read DM history
- `channels:history` - Read channel messages

**Event Subscriptions**:
- Enable Events
- Request URL: `https://mirage-slack.fly.dev/slack/events` (set after deploy)
- Subscribe to bot events:
  - `app_mention`
  - `message.im`

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

**In channels:**
```
@mirage call mom tomorrow
@mirage finish quarterly report by Friday
@mirage blocked on design review from Sarah
```

**In DMs:**
```
buy groceries
research vacation destinations
waiting for client feedback on proposal
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

**"Challenge Failed" error when setting Event URL:**
- Make sure the server is running
- Check `fly logs` for errors
- Verify the URL is correct: `https://mirage-slack.fly.dev/slack/events`

**Bot not responding:**
- Check that bot is invited to the channel
- Verify Event Subscriptions are enabled
- Check secrets are set: `fly secrets list`

**Database errors:**
- Verify Turso credentials
- Check schema is initialized: `turso db shell mirage "SELECT COUNT(*) FROM tasks"`
