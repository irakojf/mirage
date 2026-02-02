---
name: prioritize
description: Triage Projects, check blocked items, and update Do Now list
---

## Instructions

When the user runs /prioritize, help them clean up and prioritize their task list in this order:

### 1. Review Projects

```
Call: mcp__notion__query_tasks
Arguments: { "status_filter": "Tasks" }
```

Evaluate tasks to see if they are actually projects.
- If the task should be a Project, ask the user to confirm.

```
Call: mcp__notion__query_tasks
Arguments: { "status_filter": "Projects" }
```

Display and triage each project:

```
PROJECTS REVIEW

You have [X] projects. For each one, tell me:
- **Keep** (confirm priority 1-4)
- **Ideas** (not ready to work on)
- **Waiting On** (blocked)
- **Tasks** (single clear next step)

---

**1. [Project Name]** *(Priority X, tags)*
**2. [Project Name]** *(Priority X, tags)*
...
```

After triaging, ask for next steps on active projects. Create any next steps as Tasks linked to that project.

**Important Not Urgent check:** For any project tagged `[Important Not Urgent]`, verify it has at least one active task in the Tasks list. If not, ask: "What's the next step for [Project]?" and create it.

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
- **Unblocked → Tasks** (ready to work on)
- **Unblocked → Do Now** (urgent)
- **Won't Do** (no longer relevant)
```

### 3. Review Do Now

```
Call: mcp__notion__query_tasks
Arguments: { "status_filter": "Do Now" }
```

Ask which tasks are already complete:

```
DO NOW - STATUS CHECK

1. [ ] Book Airbnb in SF
2. [ ] Send Modal pricing proposal
3. [ ] Think through Abhi proposal

Which are done? (numbers or "none")
```

### 4. Mark Completed

For each completed task:

```
Call: mcp__notion__update_task
Arguments: { "page_id": "...", "status": "Done" }
```

### 5. Reprioritize All Tasks

```
Call: mcp__notion__query_tasks
Arguments: { "exclude_done": true }
```

Automatically reprioritize ALL tasks in the "Tasks" status.

Rank tasks by:
1. **Active deals & negotiations** — Contracts, proposals, follow-ups with prospects/clients waiting for response
2. **Project-linked tasks** — Tasks that feed into active Projects (especially `[Important Not Urgent]` projects like revenue goals). Keep these clustered together.
3. **[Unblocks] tagged** — Completing this enables other work
4. **Money tasks** — Invoices, payments, payroll
5. **High mention count** — Procrastination signals (mentioned 2+)
6. **Quick wins** — `complete_time` under 15 min
7. **Identity/Compound tags** — Long-term value (see Identity Categories below)
8. **Time-sensitive** — Deadlines, events, travel prep
9. **Relationships** — Follow-ups with friends, family, network (important but not urgent)
10. **Everything else** — By created date (oldest first)

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
Arguments: { "page_id": "...", "priority": 1 }
```

Show the reordered task list:

```
TASKS (reordered by priority):

1. [Task] — [reason]
2. [Task] — [reason]
3. [Task] — [reason]
...
```

### 6. Propose a new Do Now list

**Do Now criteria:** Only items that meet ONE of these:
- **Revenue/deals** — Active negotiations, contracts waiting, prospects to follow up
- **48-hour horizon** — Immovable deadline in next 24-48 hours (meetings, trips, events)
- **Physical constraints** — Travel prep, appointments, things that can't be done later

From the reprioritized tasks, propose items for Do Now status:
- Active deals and negotiations (always #1)
- Time-bound tasks with deadlines in next 48 hours
- Physical reality constraints (packing, appointments)
- High mention counts (procrastination signals — sometimes need forcing function)

**Do Now should be 3-7 items max.** If it's longer, user is overcommitted. Ask what can move back to Tasks.

### 7. Show Final Do Now List

```
DO NOW:

1. Send Modal pricing proposal [client waiting]
2. Run payroll [mentioned 3x]
3. Collect payment from Clint [KEYSTONE]

[X] items. Focused and doable.
```

## Key Behaviors

- **Projects first** — Triage projects and get next steps before touching Do Now
- **Check Waiting On** — Blocked items get unblocked and forgotten
- **Clear done items first** — Don't let completed tasks clutter the list
- **Question priorities** — "Do Now" doesn't mean it should stay there
- **Surface hidden priorities** — High mention counts signal importance
- **Keep Do Now short** — 3-7 items max, focused on revenue + 48hr horizon
- **Cluster project tasks** — Related tasks stay grouped (e.g., all video asset tasks together)
- **Important Not Urgent needs next steps** — Every active Q2 project should have a visible task
- **End with clarity** — User knows exactly what to work on next

## Do Now vs Tasks Decision Tree

```
Is it an active deal/negotiation? → DO NOW
Is there a deadline in 24-48 hours? → DO NOW
Is it physical reality (trip, appointment)? → DO NOW
Does it feed a revenue goal project? → TOP OF TASKS (clustered)
Does it [Unblock] something else? → HIGH IN TASKS
Everything else → TASKS (ordered by priority)
```
