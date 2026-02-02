# Mirage Slack Bot

Capture tasks directly from Slack — completely private (only you see responses).

## Architecture

```
Slack → fly.io (this server) → Claude Opus → Notion (all data)
                                                    ↑
                                     Local Claude Code ─┘
```

All data (tasks, reviews, identity) lives in Notion, accessible from both Slack and local Claude Code.

## Commands

| Command | Description |
|---------|-------------|
| `/mirage <task>` | Capture a single task |
| `/prioritize` | Rank open tasks using core priority rules |
| `/plan` | Draft a day plan from priorities + time estimates |
| `/review` | Weekly review snapshot (completed, energy, procrastination) |
| Message shortcut | Right-click any message → "Capture with Mirage" |
| `@mirage` (in thread) | Capture a thread conversation as a task |
| DM | Send any message in a DM to capture it as a task |

All slash command responses are ephemeral (only you see them).

## Setup

### 1. Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Create a new integration for your workspace
3. Copy the "Internal Integration Secret" → `NOTION_TOKEN`
4. Share your tasks database with the integration

### 2. Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: `Mirage`, select your workspace

**Bot Token Scopes** (OAuth & Permissions):
- `chat:write` — Send messages and ephemeral responses
- `commands` — Handle slash commands
- `reactions:write` — Add reaction indicators (👀 while processing)
- `channels:history` — Read thread messages in public channels
- `groups:history` — Read thread messages in private channels
- `im:history` — Read DM messages
- `im:read` — Access DM channel info
- `im:write` — Open DMs with users
- `app_mentions:read` — Respond to @mirage mentions

**Slash Commands** (all use URL `https://mirage-slack.fly.dev/slack/commands`):

| Command | Description | Usage Hint |
|---------|-------------|------------|
| `/mirage` | Capture a task privately | `[task description]` |
| `/prioritize` | Rank tasks by priority | _(none)_ |
| `/plan` | Draft a day plan | _(none)_ |
| `/review` | Weekly review snapshot | _(none)_ |

**Interactivity & Shortcuts**:
1. Enable Interactivity, set Request URL to `https://mirage-slack.fly.dev/slack/interactive`
2. Create a **Message Shortcut**:
   - Name: `Capture with Mirage`
   - Callback ID: `capture_with_mirage`

**Event Subscriptions**:
1. Enable Events, set Request URL to `https://mirage-slack.fly.dev/slack/events`
2. Subscribe to bot events:
   - `app_mention` — @mirage mentions in threads
   - `message.im` — DM messages

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
fly secrets set NOTION_TOKEN=secret_your-notion-token

# Deploy
fly deploy

# Check logs
fly logs
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_SIGNING_SECRET=...
export ANTHROPIC_API_KEY=sk-ant-...
export NOTION_TOKEN=secret_...

# Run server
python server.py

# In another terminal, expose with ngrok
ngrok http 3000

# Update Slack URLs to ngrok URL
```

## Usage

### Quick Capture

```
/mirage call mom tomorrow
/mirage finish quarterly report by Friday
/mirage blocked on design review from Sarah
```

### Prioritize

```
/prioritize
```

Returns a ranked list of your top tasks with tags and reasoning.

### Day Plan

```
/plan
```

Builds a schedule from your prioritized tasks that fit within configured work hours, using time estimates.

### Weekly Review

```
/review
```

Shows completed count, procrastination patterns, energy breakdown, and stale decisions.

### Message Shortcut

Right-click any message → "Capture with Mirage". Works on single messages and threads:
- Single message: captures as a task
- Thread: reads the full conversation and extracts the core action item

Adds a 👀 reaction while processing, then DMs you the captured task with a permalink back to the original message.

### @mirage in Threads

Tag `@mirage` in any thread to capture the conversation as a task. Must be used inside a thread (not top-level).

### DM Capture

Send any message directly to Mirage in a DM and it gets captured as a task. No slash command needed.

## Response Format

**New task:**
```
Got it!

"Call mom tomorrow"
Tasks | 5 min
[DO IT]
```

**Duplicate task:**
```
Already tracking this!

"Call mom tomorrow" (mentioned 3x)
Flagged for procrastination review
```

**Prioritize:**
```
Top priorities:
1) Send invoice to client [KEYSTONE] — Unblocks payment
2) Review PR #42 [DO IT] — 2 min, do immediately
3) Plan Q2 roadmap [COMPOUNDS] — Strategic, builds over time
```

## Troubleshooting

**Slash command not working:**
- Verify the Request URL: `https://mirage-slack.fly.dev/slack/commands`
- Check `fly logs` for errors
- Ensure the app is reinstalled after adding commands
- All four commands must be registered: `/mirage`, `/prioritize`, `/plan`, `/review`

**"dispatch_failed" error:**
- Server not running — check `fly status`
- Wrong URL configured — verify the `/slack/commands` endpoint

**Message shortcut not appearing:**
- Verify Interactivity is enabled with correct Request URL
- Check that the shortcut callback ID is exactly `capture_with_mirage`

**@mirage not responding:**
- Ensure `app_mention` event subscription is active
- Must be used inside a thread, not as a top-level message

**DMs not captured:**
- Ensure `message.im` event subscription is active
- Check that `im:history` scope is granted

**Notion errors:**
- Verify `NOTION_TOKEN` is set correctly
- Ensure the tasks database is shared with your integration
