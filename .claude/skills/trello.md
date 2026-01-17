---
name: trello
description: Display tasks in a Trello-style Kanban board view
---

## Instructions

When the user runs /trello, display all open tasks in a visual Kanban board.

### 1. Query Tasks from Notion

Use the Notion MCP `query_tasks` tool to fetch all open tasks:

```
Call: mcp__notion__query_tasks
Arguments: { "exclude_done": true }
```

This returns tasks with:
- id (Notion page ID)
- content (Name property)
- status (Action, Project, Idea, Blocked)
- mentioned (procrastination count)
- estimated_minutes (Time to Complete)
- blocked_by (Blocked By)
- energy (Energy rating)
- tags (Type multi-select)
- created_time

### 2. Auto-assign Missing ETAs

For tasks with null `estimated_minutes`, infer a reasonable estimate and update:

```
Call: mcp__notion__update_task
Arguments: { "page_id": "...", "estimated_minutes": 15 }
```

Use your judgment: quick phone tasks ~2m, emails ~5m, reviews ~10m, multi-step work ~30m.

### 3. Render Kanban Board

**ALWAYS display as a SINGLE VERTICAL Kanban board with all 4 columns side-by-side.**

Use box-drawing characters to create 4 tables: Actions, Projects, Blocked, Ideas.
Each column shows tasks vertically within it. This creates a true Kanban board view.

**Required format:**

```
┌─────────────────────────────────────────┬───────┬──────────┐
│ Actions                                 │ ETA   │ Mentions │
├─────────────────────────────────────────┼───────┼──────────┤
│ □ Task name [DO IT]                     │ 2m    |  5X      │
├─────────────────────────────────────────┼───────┼──────────┤
│ □ Task name [DO IT]                     │ 30m   |  0X      │
└─────────────────────────────────────────┴───────┴──────────┘
```

**Column formatting rules:**
- Each column is ~60 chars wide
- Show task count in header: `ACTIONS (18)`
- Use `□` for open tasks
- Show ETA in parentheses: `(30m)`
- Show `(Nx)` for mentioned > 1
- Use warning for mentioned >= 3 (procrastination flag)
- For blocked items, show waiting info on next line with `↳`
- Empty cells in shorter columns should be blank
- Truncate long task names to fit column width

### 4. Visual Indicators

| Indicator | Meaning |
|-----------|---------|
| `[DO IT]` | Action takes ≤2 min — do it now per Atomic Habits (TOP PRIORITY) |
| `(Nx)` | Task has been mentioned N times (procrastination signal) |
| `@Name` | Who the blocked item is waiting on |

**Mention Count:** Show as `(Nx)` where N is mentioned count, e.g., `(3x)` = mentioned 3 times

**Sorting Priority (within Actions):**
1. `[DO IT]` items (≤2 min) — always at top
2. High mention count (descending) — procrastinated items surface
3. `[KEYSTONE]` tag — unlocks other tasks
4. `[COMPOUNDS]` tag — 1% improvements that build over time
5. `[IDENTITY]` tag — aligns with who you want to become
6. Oldest first (by created_time)

### 5. Highlight Procrastination

If mentioned >= 3, make the task visually prominent and add a note:
> "This task has appeared 3+ times. What's the real blocker?"

### 6. Interactive Commands

After displaying the board, offer:

```
Commands:
  "focus"          → Show only actions for today based on calendar availability
  "next"           → AI recommends what to do next (uses knowledge base)
  "schedule"       → Auto-schedule actions to Google Calendar
  "notion"         → Show Production Calendar from Notion
```

### 7. "next" Command Logic

When user asks "what should I do next?", use this prioritization:

1. **2-minute actions first** — Get quick wins, build momentum
2. **High mentioned count** — Address procrastinated items (they're weighing on you)
3. **Calendar awareness** — Match task duration to available time blocks
4. **Energy matching** — Reference past energy ratings to suggest similar tasks at good times
5. **Knowledge base** — Apply Atomic Habits principles:
   - "What would the person I want to become do?"
   - "Which of these compounds over time?"
   - "What's the keystone habit here?"

## Key Behaviors

- **Visual clarity**: The board should be scannable at a glance
- **Surface procrastination**: Make repeated tasks impossible to ignore
- **Knowledge-informed**: Use Atomic Habits principles for "next" recommendations
