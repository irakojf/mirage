# Slack Command Reference

All Slack commands are completely private — only you see the command and the response.

## Commands

### `/mirage [task description]`

Quick capture a single task.

```
/mirage call mom tomorrow
/mirage finish quarterly report by Friday
/mirage blocked on design review from Sarah
```

**Processing:**
1. Claude analyzes the text for status, time estimate, and type
2. Checks for duplicates against open tasks (semantic matching)
3. If duplicate: increments Mentioned counter, flags if 3+
4. If new: creates task in Notion with inferred properties

**Response format (new task):**
```
Got it!

"Call mom tomorrow"
action | 5 min
[DO IT]
```

**Response format (duplicate):**
```
Already tracking this!

"Call mom tomorrow" (mentioned 3x)
Flagged for procrastination review
```

### `/dump`

Start a brain dump session. Opens a DM where you type freely.

```
/dump
```

After starting:
- Each message gets a checkmark to confirm capture
- No commands needed — just type naturally
- Messages are queued for batch processing

### `/done`

End a brain dump session and process all captured items.

```
/done
```

Processing:
1. All captured messages are batch-processed
2. Each is normalized, deduplicated, and categorized
3. Results are shown as a summary list

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
  Call mom — Tasks (5 min)
  Finish the quarterly report — Tasks (30 min)
  Wait for Sarah's design review — Blocked
  Add dark mode to the app — Ideas
```

## Follow-Up Task Naming

Vague follow-ups are rejected. When capturing a follow-up task, include:

1. **Who** — Full name + context (company, relationship)
2. **What** — Topic of the conversation
3. **Outcome** — What "done" looks like

**Format:** `[Name] ([Context]): [Action] re: [Topic] -> [Outcome]`

| Bad | Good |
|-----|------|
| respond to Samantha | Samantha Wen (Notion): Reply re: partnership -> schedule call |
| follow up with John | John Kim (investor): Send deck re: seed round -> get meeting |

## Deployment

The Slack bot runs on fly.io at `https://mirage-slack.fly.dev`.

Required secrets:
- `SLACK_BOT_TOKEN` — Bot token (xoxb-...)
- `SLACK_SIGNING_SECRET` — Request signing secret
- `ANTHROPIC_API_KEY` — Claude API key
- `NOTION_TOKEN` — Notion integration token

See `mcp/slack/README.md` for full setup instructions.
