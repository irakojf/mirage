# Mirage Slack Bot

Capture tasks directly from Slack by @mentioning Mirage or sending DMs.

## Architecture

```
Slack → fly.io (this server) → Claude Opus → Notion (all data)
                                                    ↑
                                     Local Claude Code ─┘
```

All data (tasks, reviews, identity) lives in Notion, accessible from both Slack and local Claude Code.

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
- `chat:write` - Send messages
- `commands` - Handle slash commands

**Slash Commands**:
1. Go to "Slash Commands" in sidebar
2. Create the following commands (all use URL: `https://mirage-slack.fly.dev/slack/commands`):

| Command | Description | Usage Hint |
|---------|-------------|------------|
| `/mirage` | Capture a task privately | `[task description]` |
| `/dump` | Start a brain dump session | _(none)_ |
| `/done` | End brain dump and process tasks | _(none)_ |

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
export NOTION_TOKEN=secret_...

# Run server
python server.py

# In another terminal, expose with ngrok
ngrok http 3000

# Update Slack Event URL to ngrok URL
```

## Usage

All commands are completely private (nobody else sees them).

### Quick Capture
Use `/mirage` anywhere to capture a single task:
```
/mirage call mom tomorrow
/mirage finish quarterly report by Friday
/mirage blocked on design review from Sarah
```

### Brain Dump Mode
Start a brain dump session to capture multiple thoughts conversationally:

1. Type `/dump` anywhere to start
2. Mirage opens a DM and you just type freely — no commands needed
3. Each message gets a checkmark to confirm capture
4. Type `done` (or `/done`) when finished
5. Mirage processes everything and shows your tasks

**Example session:**
```
You: /dump
Mirage: Brain dump started. Just type whatever's on your mind...

You: call mom
You: need to finish the quarterly report
You: blocked on sarah for the design review
You: maybe we should add dark mode to the app
You: done

Mirage: Brain dump complete!
4 new tasks:
• Call mom — Tasks (5 min)
• Finish the quarterly report — Tasks (30 min)
• Wait for Sarah's design review — Blocked
• Add dark mode to the app — Ideas
```

### From a thread context
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
- Make sure you added all three commands: `/mirage`, `/dump`, `/done`

**"dispatch_failed" error:**
- Server not running - check `fly status`
- Wrong URL configured - verify `/slack/commands` endpoint

**Notion errors:**
- Verify `NOTION_TOKEN` is set correctly
- Ensure the tasks database is shared with your integration
