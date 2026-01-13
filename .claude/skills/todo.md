---
name: todo
description: Display tasks in a Trello-style Kanban board view
---

## Instructions

When the user runs /todo, display all open tasks in a visual board:

### 1. Query Tasks

```sql
SELECT
    id,
    content,
    bucket,
    estimated_minutes,
    times_added,
    first_added_at,
    blocked_on,
    follow_up_date,
    parent_task_id
FROM tasks
WHERE status = 'open'
ORDER BY
    CASE bucket
        WHEN 'action' THEN 1
        WHEN 'project' THEN 2
        WHEN 'idea' THEN 3
        WHEN 'blocked' THEN 4
    END,
    times_added DESC,
    first_added_at ASC;
```

### 2. Query Subtasks (for Projects)

```sql
SELECT id, content, estimated_minutes, parent_task_id
FROM tasks
WHERE status = 'open' AND parent_task_id IS NOT NULL;
```

### 3. Check Google Calendar (if available)

If the Google Calendar MCP server is configured, query today's free time:
- Get total available hours today
- Display at the bottom of the board

### 4. Check Notion Production Calendar (if available)

If Notion MCP server is configured, fetch upcoming items from:
`https://www.notion.so/Production-Calendar-28535d23b569808c9689fa367f5fc9b5`

### 5. Render Kanban Board

Display a terminal-based board with box-drawing characters:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              YOUR TASK BOARD                                     │
├────────────────────┬────────────────────┬────────────────────┬──────────────────┤
│  ACTIONS (7)       │  PROJECTS (3)      │  IDEAS (5)         │  BLOCKED (2)     │
├────────────────────┼────────────────────┼────────────────────┼──────────────────┤
│                    │                    │                    │                  │
│ ┌────────────────┐ │ ┌────────────────┐ │ ┌────────────────┐ │ ┌──────────────┐ │
│ │ Fix auth bug   │ │ │ Q1 Planning    │ │ │ Podcast idea   │ │ │ API migrate  │ │
│ │ ~30 min        │ │ │                │ │ │                │ │ │ @DevOps      │ │
│ │ [3x added]     │ │ │ Next: Create   │ │ │                │ │ │ f/u: Jan 16  │ │
│ └────────────────┘ │ │ blank doc (2m) │ │ └────────────────┘ │ └──────────────┘ │
│                    │ └────────────────┘ │                    │                  │
│ ┌────────────────┐ │                    │ ┌────────────────┐ │ ┌──────────────┐ │
│ │ Email Jake     │ │ ┌────────────────┐ │ │ New pricing    │ │ │ Budget app   │ │
│ │ ~5 min         │ │ │ Website redo   │ │ │ model          │ │ │ @Finance     │ │
│ └────────────────┘ │ │                │ │ └────────────────┘ │ │ f/u: Jan 18  │ │
│                    │ │ Next: Sketch   │ │                    │ └──────────────┘ │
│ ┌────────────────┐ │ │ wireframe (5m) │ │                    │                  │
│ │ Dentist appt   │ │ └────────────────┘ │                    │                  │
│ │ ~2 min [DO IT] │ │                    │                    │                  │
│ └────────────────┘ │                    │                    │                  │
│                    │                    │                    │                  │
└────────────────────┴────────────────────┴────────────────────┴──────────────────┘

Today: 4.5 hrs free on calendar | [3x added] = procrastinated | [DO IT] = under 2 min
```

### 6. Visual Indicators

| Indicator | Meaning |
|-----------|---------|
| `[DO IT]` | Action takes ≤2 min — do it now per Atomic Habits (TOP PRIORITY) |
| `Mentioned Nx` | Task has been mentioned N times across dumps (procrastination signal) |
| `@Name` | Who the blocked item is waiting on |
| `Follow Up: Date` | Follow-up date for blocked items |
| `Next: ...` | First action for a project |

**Tally System for Mentions:**
- Under 10 mentions: Use tally marks (e.g., `Mentioned ||||` = 4 times)
- 10+ mentions: Use number (e.g., `Mentioned 12x`)

**Sorting Priority (within Actions column):**
1. `[DO IT]` items (≤2 min) — always at top
2. `[NEVER MISS TWICE]` — skipped yesterday, do today
3. `[KEYSTONE]` — unlocks other tasks or creates ripple effects
4. High mention count (descending) — procrastinated items surface
5. `[COMPOUNDS]` — 1% improvements that build over time
6. `[IDENTITY]` — aligns with who you want to become
7. Oldest first (by first_added_at) — don't let things rot

**Tag Inference:**
The agent should infer these tags during `/done` processing based on:
- `[KEYSTONE]`: Task mentions enabling other work, or is a blocker for others
- `[COMPOUNDS]`: Learning, health, relationship, or skill-building tasks
- `[IDENTITY]`: Ask during onboarding "Who do you want to become?" and match tasks to that
- `[NEVER MISS TWICE]`: Auto-detected from task history (was scheduled yesterday, not completed)

### 7. Highlight Procrastination

If times_added >= 3, make the task visually prominent and add a note:
> "This task has appeared 3+ times. What's the real blocker?"

### 8. Interactive Commands

After displaying the board, offer:

```
Commands:
  "focus"          → Show only actions for today based on calendar availability
  "expand [name]"  → Show all subtasks for a project
  "next"           → AI recommends what to do next (uses knowledge base)
  "schedule"       → Auto-schedule actions to Google Calendar
  "notion"         → Show Production Calendar from Notion
```

### 9. "next" Command Logic

When user asks "what should I do next?", use this prioritization:

1. **2-minute actions first** — Get quick wins, build momentum
2. **High times_added** — Address procrastinated items (they're weighing on you)
3. **Calendar awareness** — Match task duration to available time blocks
4. **Energy matching** — Reference past energy_ratings to suggest similar tasks at good times
5. **Knowledge base** — Apply Atomic Habits principles:
   - "What would the person I want to become do?"
   - "Which of these compounds over time?"
   - "What's the keystone habit here?"

## Key Behaviors

- **Visual clarity**: The board should be scannable at a glance
- **Surface procrastination**: Make repeated tasks impossible to ignore
- **Actionable projects**: Always show the next step, not just the project name
- **Calendar-aware**: Ground priorities in actual available time
- **Knowledge-informed**: Use Atomic Habits principles for "next" recommendations
