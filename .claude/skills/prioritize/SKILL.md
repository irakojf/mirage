---
name: prioritize
description: Triage Projects, check blocked items, and update Do Now list
---

## Instructions

When the user runs /prioritize, help them clean up and prioritize their task list in this order:

### 1. Review Projects

```
Call: mcp__notion__query_tasks
Arguments: { "kind_filter": "Project", "exclude_done": true }
```

Display and triage each project:

```
PROJECTS REVIEW

You have [X] projects. For each one, tell me:
- **Keep** (confirm priority tier)
- **Idea** (not ready to work on — change kind to Idea)
- **Waiting On** (blocked — change status to Waiting On)
- **Task** (single clear next step — change kind to Task)

---

**1. [Project Name]** *(P2, tags)*
**2. [Project Name]** *(P3, tags)*
...
```

After triaging, ask for next steps on active projects. Create any next steps as Tasks (kind: Task) linked to that project.

**Important Not Urgent check:** For any project tagged `[Important Not Urgent]`, verify it has at least one active task in the Backlog. If not, ask: "What's the next step for [Project]?" and create it.

### 2. Review Waiting On

```
Call: mcp__notion__query_tasks
Arguments: { "status_filter": "Waiting On" }
```

Check if blocked items are still blocked:

```
WAITING ON REVIEW

You have [X] blocked items:

**1. [Task Name]** — Blocked by: [blocker]
**2. [Task Name]** — Blocked by: [blocker]

For each:
- **Still blocked** (no change)
- **Unblocked → Backlog** (ready to work on)
- **Unblocked → Do Now** (urgent)
- **Won't Do** (no longer relevant)
```

### 3. Review In Progress

```
Call: mcp__notion__query_tasks
Arguments: { "status_filter": "In Progress" }
```

Check status of in-progress items:

```
IN PROGRESS - STATUS CHECK

1. [ ] [Task name]
2. [ ] [Task name]

Which are done? Still in progress? Need to move back to Backlog?
```

### 4. Review Do Now

```
Call: mcp__notion__query_tasks
Arguments: { "status_filter": "Do Now" }
```

Ask which tasks are already complete:

```
DO NOW - STATUS CHECK

1. [ ] [Task name]
2. [ ] [Task name]

Which are done? (numbers or "none")
```

### 5. Mark Completed

For each completed task:

```
Call: mcp__notion__update_task
Arguments: { "page_id": "...", "status": "Done" }
```

### 6. Reprioritize Backlog

```
Call: mcp__notion__query_tasks
Arguments: { "status_filter": "Backlog" }
```

Reprioritize ALL items in Backlog status using **priority tiers**.

#### Priority Tiers

| Tier | Meaning | What belongs here |
|------|---------|-------------------|
| **P1** | Do this week | Deadlines, money tasks, deals, time-sensitive |
| **P2** | This sprint | Revenue-linked, active project work, call preps |
| **P3** | Active projects & systems | Ongoing projects, strategic work, outbound |
| **P4** | Someday backlog | Do when capacity opens, relationships, misc |
| **P5** | Ideas / parking lot | All Ideas, Substack topics, experiments |

Within each tier, the user can **drag cards freely** in Notion to reorder. The tier is the bucket; position within the bucket is manual.

Assign tiers by:
1. **Active deals & negotiations** → P1
2. **Deadlines in next 7 days** → P1
3. **Money tasks** (invoices, payments) → P1
4. **Project-linked tasks** feeding active Projects (especially `[Important Not Urgent]`) → P2
5. **[Unblocks] tagged** → P2
6. **Quick wins** (`complete_time` under 15 min) → P1 or P2
7. **High mention count** (procrastination signals, mentioned 2+) → bump up one tier
8. **Identity/Compound tags** → P3
9. **Relationships** → P4
10. **Ideas** (kind: Idea) → P5
11. **Everything else** → P4

**Identity Categories** (from Notion Identity page):
| Category | Identity Statement | Example Tasks |
|----------|-------------------|---------------|
| Health (Mental) | Maintains mental calm and clarity | Meditation, journaling, therapy |
| Health (Physical) | Moves fast, feels strong, avoids injury, physical age 10yrs younger | Workouts, meal prep, sleep |
| Work | Builds with patience, masters craft, applies tech creatively, leads calmly in turbulence | Deep work, shipping, creative problem-solving |
| Love | Shows up reliably, dedicates intentional time, clear on priorities | Partner time, date nights |
| Wealth | Creates wealth through revenue and creative selling | Revenue tasks, deals, $30k/mo goal |
| Relationships | Reliable, cultivates deep trust with a few | Family, close friend catch-ups |
| Life / Experience | Lives fully, says yes to once-in-a-lifetime moments | Travel, adventures, spontaneous yeses |
| Social / Connection | Genuinely open, hosts, brings people together | Hosting, intros, community events |

```
Call: mcp__notion__update_task
Arguments: { "page_id": "...", "priority": 2 }
```

Show the tiered list:

```
BACKLOG (by priority tier):

P1 — Do this week:
- [Task] — [reason]
- [Task] — [reason]

P2 — This sprint:
- [Task] — [reason]
- [Task] — [reason]

P3 — Active projects & systems:
- [Task] — [reason]

P4 — Someday:
- [Task] — [reason]

P5 — Ideas:
- [Task] — [reason]
```

### 7. Propose a new Do Now list

**Do Now criteria:** Only items that meet ONE of these:
- **Revenue/deals** — Active negotiations, contracts waiting, prospects to follow up
- **48-hour horizon** — Immovable deadline in next 24-48 hours (meetings, trips, events)
- **Physical constraints** — Travel prep, appointments, things that can't be done later

From the reprioritized backlog, propose items for Do Now status:
- Active deals and negotiations (always #1)
- Time-bound tasks with deadlines in next 48 hours
- Physical reality constraints (packing, appointments)
- High mention counts (procrastination signals — sometimes need forcing function)

**Do Now should be 3-7 items max.** If it's longer, user is overcommitted. Ask what can move back to Backlog.

### 8. Show Final Do Now List

```
DO NOW:

1. [Task] [reason]
2. [Task] [reason]
3. [Task] [reason]

[X] items. Focused and doable.
```

## Priority Tiers (P1–P5)

- **P1** = do this week (deadlines, money, deals)
- **P2** = this sprint (revenue-linked work, project tasks, call preps)
- **P3** = active projects & systems (ongoing strategic work)
- **P4** = someday backlog (do when capacity opens)
- **P5** = ideas / parking lot (all Ideas)
- Lower number = higher priority tier
- Within each tier, the user drags cards in Notion to set order manually
- Do Now and In Progress items don't need tiers (status IS the priority signal)
- `/prioritize` reassigns tiers, not individual ranks

## Key Behaviors

- **Projects first** — Triage projects and get next steps before touching Do Now
- **Check Waiting On** — Blocked items get unblocked and forgotten
- **Check In Progress** — Make sure active work is still active
- **Clear done items first** — Don't let completed tasks clutter the list
- **Question priorities** — "Do Now" doesn't mean it should stay there
- **Surface hidden priorities** — High mention counts signal importance
- **Keep Do Now short** — 3-7 items max, focused on revenue + 48hr horizon
- **Cluster project tasks** — Related tasks stay grouped (e.g., all video asset tasks together)
- **Important Not Urgent needs next steps** — Every active project should have a visible task
- **End with clarity** — User knows exactly what to work on next

## Do Now vs Backlog Decision Tree

```
Is it an active deal/negotiation? → DO NOW
Is there a deadline in 24-48 hours? → DO NOW
Is it physical reality (trip, appointment)? → DO NOW
Does it feed a revenue goal project? → TOP OF BACKLOG (clustered)
Does it [Unblock] something else? → HIGH IN BACKLOG
Everything else → BACKLOG (ordered by tier, drag within tier)
```
