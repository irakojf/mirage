---
name: review
description: Weekly review - reflect on what happened and plan ahead
---

## Instructions

When the user runs /review, conduct a weekly review:

### 1. Gather Data

```sql
-- Tasks completed this week
SELECT id, content, bucket, completed_at, energy_rating
FROM tasks
WHERE status = 'done'
AND completed_at >= date('now', '-7 days')
ORDER BY completed_at;

-- Tasks still open
SELECT id, content, bucket, times_added, first_added_at
FROM tasks
WHERE status = 'open'
ORDER BY times_added DESC;

-- Dump sessions this week
SELECT COUNT(*) as dumps, SUM(LENGTH(raw_input)) as total_input
FROM dump_sessions
WHERE started_at >= date('now', '-7 days');
```

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

Store the energy_rating on each task for future pattern recognition.

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
  [X]% of completed tasks aligned with your identity goals.
  Your "[work]" identity got the most attention.
  Your "[health]" identity got the least.
```

### 5. Stale Task Cleanup

Surface tasks that have been sitting too long:

```
STALE TASKS (open 2+ weeks)

These have been on your list a while:

1. "Automate weekly reports" — first added Nov 15 (8 weeks ago)
   Mentioned 4x. What's really going on here?

2. "Call mom about holiday plans" — first added Dec 1 (6 weeks ago)
   Mentioned 2x.

For each: Archive / Delegate / Recommit / Break down?
```

### 6. Blocked Item Check

Review blocked items:

```
BLOCKED ITEMS

1. "API migration" — waiting on DevOps
   Follow up was: Jan 16 (3 days ago)
   Did this get unblocked? Update status?

2. "Budget approval" — waiting on Finance
   Follow up is: Jan 20 (in 4 days)
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

```sql
INSERT INTO reviews (id, week_start, completed_at, notes, tasks_completed, tasks_added)
VALUES (
    lower(hex(randomblob(8))),
    date('now', '-7 days'),
    datetime('now'),
    '<summary>',
    <completed_count>,
    <added_count>
);
```

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
