---
name: review
description: Weekly review - reflect on what happened and plan ahead
---

## Instructions

When the user runs /review, conduct a weekly review:

### 1. Gather Data

Query tasks from Notion and calendar events from Google Calendar:

```
# Tasks completed this week
Call: mcp__notion__query_tasks
Arguments: { "status_filter": "Done" }

# Tasks still open
Call: mcp__notion__query_tasks
Arguments: { "exclude_done": true }

# Calendar events for this week (Sunday to Saturday)
Bash: python3.11 mcp/google-calendar/server.py list_events --start-date <sunday of this week> --end-date <saturday of this week>
```

Filter completed tasks by `created_time` for "this week" logic.

### 1b. Display Calendar Summary

Show what actually happened this week by organizing calendar events by day:

```
THIS WEEK'S CALENDAR (Jan 12-18)

Sunday 1/12
- Production Day (7:15am - 6:50pm)
- Company lunch
- Weekly Data Insights Brainstorm

Monday 1/13
- Lower Body Strength workout
- Standup
- Sauna
...
```

Group events by:
- **Production/Shoots** — major work blocks
- **Meetings** — calls, 1:1s, client meetings
- **Workouts** — fitness activities
- **Personal** — meals, wind down, etc.

This provides context for the review — what the week actually looked like beyond just tasks.

### 2. Celebrate Wins

Start positive:

```
WEEKLY REVIEW

WINS THIS WEEK
You completed [X] tasks:

  [done] Fix authentication bug
  [done] Email Jake: contract renewal
  [done] Schedule dentist appointment
  ...
```

### 3. Energy Audit

For each completed task, ask about energy:

```
ENERGY CHECK

Let's tag how these tasks felt. For each one, tell me:
  Red    = Energy drain, dreaded it, felt heavy
  Yellow = Neutral, just got it done
  Green  = Energizing, felt good, want more of these

1. Fix authentication bug — red / yellow / green?
2. Email Jake: contract renewal — red / yellow / green?
3. Schedule dentist appointment — red / yellow / green?
...
```

Store the energy rating on each task:

```
Call: mcp__notion__update_task
Arguments: { "page_id": "...", "energy": "green" }
```

### 4. Pattern Recognition

Analyze patterns and surface insights:

```
PATTERNS I NOTICED

Procrastination:
  "Schedule dentist" appeared 5 times over 3 weeks before you did it.
  What made it hard? What finally got you to do it?

Energy drains:
  Most of your "red" tasks this week were [category].
  Consider: delegating, batching, or eliminating these.

Energy gains:
  Your "green" tasks were mostly [category].
  How can you do more of these?

Identity alignment:
  [X]% of completed tasks had the Identity tag.
```

### 5. Stale Task Cleanup

Surface tasks that have been sitting too long (check `created_time`):

```
STALE TASKS (open 2+ weeks)

These have been on your list a while:

1. "Automate weekly reports" — first added Nov 15 (8 weeks ago)
   Mentioned 4x. What's really going on here?

2. "Call mom about holiday plans" — first added Dec 1 (6 weeks ago)
   Mentioned 2x.

For each: Archive / Delegate / Recommit / Break down?
```

To archive stale tasks:

```
Call: mcp__notion__update_task
Arguments: { "page_id": "...", "status": "Archived" }
```

### 6. Blocked Item Check

Review blocked items:

```
BLOCKED ITEMS

1. "API migration" — waiting on DevOps
   Did this get unblocked? Update status?

2. "Budget approval" — waiting on Finance
   Status check needed?
```

### 7. Next Week Planning

```
NEXT WEEK

Based on your energy patterns and identity goals, I suggest focusing on:

Top Priority:
  "[KEYSTONE] Ship the MVP" — unlocks 3 other tasks

Identity Focus:
  Your "[health]" identity needs attention. One small action?

Quick Wins Available:
  3 tasks under 5 minutes you could batch tomorrow morning

What's your #1 priority for next week?
>
```

### 8. Save Review Record

At the end of the review, save it to Notion with the full conversation transcript:

```
Call: mcp__notion__create_review
Arguments: {
    "week_of": "2025-01-13",  // Start of the week being reviewed
    "wins": "Completed 12 tasks including...",
    "struggles": "Procrastinated on dentist appointment...",
    "next_week_focus": "Ship the MVP",
    "tasks_completed": 12,
    "transcript": "<full conversation from /review to end>"
}
```

**Important:** Capture the ENTIRE conversation that happened during the review - all questions asked, user responses, insights surfaced. This transcript is valuable for future pattern recognition.

### 9. Knowledge Base Integration

Reference `knowledge/atomic-habits.pdf` and `knowledge/tim-ferris-podcast.txt` for:
- Reframing procrastinated tasks ("What would this look like if it were easy?")
- Identity-based motivation ("You said you're someone who [identity]. Does keeping this task align?")
- Habit insights ("This keeps appearing. Should it become a routine instead of a task?")

## Key Behaviors

- **Start with wins**: Always celebrate what got done first
- **Energy is data**: Track red/yellow/green to inform future prioritization
- **Surface procrastination**: Don't let stale tasks hide — confront them
- **Connect to identity**: Show how task completion aligns with who they want to become
- **Be a coach, not a judge**: Curious questions, not guilt trips
- **End with focus**: One clear priority for next week
