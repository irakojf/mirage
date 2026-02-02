---
name: done
description: End brain dump session, process and categorize all captured tasks
---

## Instructions

When the user runs /done, process the brain dump:

### 1. Fetch ALL Existing Tasks

Before processing, fetch all open tasks for deduplication:

```
Call: mcp__notion__query_tasks
Arguments: { "exclude_done": true }
```

### 2. Parse & Clean Tasks

Extract individual tasks from raw input. Transform messy input into clear, actionable phrasing:

| Raw Input | Cleaned |
|-----------|---------|
| "need to fix the auth bug" | "Fix authentication bug" |
| "should probably email jake" | "Email Jake: contract renewal" |
| "oh and dentist" | "Schedule dentist appointment" |

**Relationship context required:** For any task involving a person, add context in parentheses:
- Company/work: `Brandon Fan (Shade):`, `Tiffany Kim (Truemed):`
- Personal: `Matt Yeung (cousin):`, `Aaron (friend):`
- Professional network: `Nicho Mann (investor):`, `Hector (advisor):`

If context is missing, ask: "Who is [name]? (company/relationship)"

### 3. Deduplicate (Semantic Matching)

Compare each task against existing tasks by **meaning, not keywords**:

- "Email Jake about contract" = "Send Jake the contract renewal email"
- "Schedule dentist" = "Book dentist appointment"

**If duplicate found:**
```
Call: mcp__notion__increment_task_mention
Arguments: { "page_id": "<matched_task_id>" }
```

**If new → create with all fields** (see steps 4-6 for field values)

### 4. Assign Status

| Status | Criteria |
|--------|----------|
| **Tasks** | Single sitting, clear next step |
| **Projects** | Multi-step, needs breakdown |
| **Ideas** | Needs thinking, exploratory |
| **Blocked** | Waiting on someone/something |

### 4b. Check Project Linking

For each new task, ask: "Does this relate to an active Project?"

```
Call: mcp__notion__query_tasks
Arguments: { "status_filter": "Projects" }
```

If task feeds into a Project (e.g., video pricing task → "$30k/mo revenue" project), note the connection. These tasks should cluster together when prioritized.

### 5. Assign Type Tag

| Type | Criteria |
|------|----------|
| **Identity** | Aligns with who user wants to become (see categories below) |
| **Compound** | 1% improvement that builds over time |
| **Unblocks** | Completing this unlocks other tasks |

**Identity Categories** (from Notion Identity page):

| Category | Statement | Example Tasks |
|----------|-----------|---------------|
| **Health (Mental)** | Maintains mental calm and clarity | Meditation, journaling, therapy |
| **Health (Physical)** | Moves fast, feels strong, avoids injury, physical age 10 years younger | Workouts, meal prep, sleep habits |
| **Work** | Builds with patience, leads with level head. Masters craft, applies technology creatively, shows up authentically. Leads calmly in turbulent times. | Deep work, strategic planning, shipping, creative problem-solving |
| **Love** | Shows up reliably, dedicates intentional time to partner, clear on priorities | Date nights, quality time, communication |
| **Wealth** | Creates wealth through revenue and creative selling, money becomes an afterthought — a tool for shaping the world | Sales calls, invoicing, deal closing, $30k/mo goal tasks |
| **Relationships** | Reliable, sets aside time for people who matter, cultivates deep trust with a few — loyal, kind, creative, building a better world | Catch-up calls, family time, close friend meetups |
| **Life / Experience** | Lives fully, says yes to once-in-a-lifetime moments, treats life as adventure to be seized, not optimized | Travel planning, new experiences, spontaneous yeses |
| **Social / Connection** | Genuinely open and interested in others, hosts, brings people together, creates spaces for connection | Hosting events, introductions, community building |

When tagging a task with `Identity`, note which category in the task description if relevant.

Leave type blank if task doesn't clearly fit.

### 6. Estimate Time (Tasks only)

| Time | Criteria |
|------|----------|
| 2 min | Quick message, simple lookup → **flag `[DO IT NOW]`** |
| 5 min | Short email, small fix |
| 15 min | Focused task, review |
| 30 min | Deep work block |
| 60+ min | Major work session |

### 7. Create Tasks

```
Call: mcp__notion__create_task
Arguments: {
    "content": "Clean, actionable task description",
    "status": "Tasks",
    "tag": "Compound",
    "complete_time": 15
}
```

For blocked items, include `"blocked_by": "Person/team name"`.

### 7b. Do Now Promotion

After creating a task, check if it belongs in Do Now:

**Auto-suggest Do Now if:**
- Active deal/negotiation (contract, proposal, prospect follow-up)
- Deadline within 48 hours (meeting prep, travel, event)
- Physical constraint (appointment, trip)

Ask: "This looks like [deal/time-sensitive/physical]. Should it go in Do Now?"

### 8. Clean Up Database

Scan entire task database for cleanup:

**Consolidate duplicates:**
- Batch similar tasks (e.g., 5 "send video to X" → 1 batch task)
- Merge tasks for same person/company
- Keep most detailed version, mark others as Done

**Remove stale tasks:**
- Outdated one-off tasks
- Vague tasks with no recent activity

### 9. Reprioritize All Tasks

```
Call: mcp__notion__query_tasks
Arguments: { "exclude_done": true }
```

Rank all "Tasks" status items by:
1. **Active deals & negotiations** — Contracts, proposals, follow-ups with prospects/clients
2. **Project-linked tasks** — Tasks feeding into active Projects (cluster together)
3. **[Unblocks] tagged** — Enables other work
4. **Money tasks** — Invoices, payments
5. **High mention count** — Procrastination signals (2+)
6. **Quick wins** — Under 15 min
7. **Identity/Compound tags** — Long-term value
8. **Time-sensitive** — Deadlines, events
9. **Relationships** — Friends, family, network follow-ups
10. **Everything else** — By created date (oldest first)

### 10. Display Summary

```
PROCESSED [N] ITEMS

NEW TASKS:
  ✓ Fix authentication bug (~30 min)
  ✓ Email Jake: contract renewal (~5 min) [DO IT NOW]
  ✓ Purchase flights to Italy (~15 min) [Compound]

NEW PROJECTS:
  ✓ Plan Hightouch manifesto shoot

NEW IDEAS:
  ✓ Explore podcast strategy

DUPLICATES FOUND:
  ↑ "Schedule dentist" (now mentioned 3x) ⚠️ PROCRASTINATION FLAG

BLOCKED:
  ⏸ API migration — waiting on DevOps

CLEANUP:
  🔀 Consolidated 5 video sends → 1 batch task
  🗑️ Removed 4 stale tasks

Net reduction: 71 → 62 active tasks
```

### Procrastination Flag

If any task reaches `mentioned >= 3`, call it out:

> "⚠️ '[task]' has been mentioned [N] times. What's really blocking this?"

## Task Naming Standards

**Follow-ups with people MUST include:**
1. **Who** — Full name + context: `Brandon Fan (Shade):`, `Matt (cousin):`
2. **What** — Topic of conversation: `re: MSA + invoice`
3. **Outcome** — What "done" looks like: `→ finalize contract`

**Format:** `[Name] ([Context]): [Action] re: [Topic] → [Outcome]`

**Examples:**
| Bad | Good |
|-----|------|
| Follow up with Brandon | Brandon Fan (Shade): Send MSA + invoice → finalize contract |
| Text Matt | Matt Yeung (cousin): Schedule 45-min catch-up call |
| Email Aaron about trip | Aaron (friend): Message on Instagram re: Milan trip → book restaurant reservations |

If user provides vague follow-up, ask for context before creating.
