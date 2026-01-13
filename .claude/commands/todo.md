# Show Tasks (Kanban View)

Display all tasks organized as a Kanban board.

## Instructions

1. Query all tasks grouped by status and bucket:
   ```sql
   SELECT * FROM tasks ORDER BY
     CASE status
       WHEN 'in_progress' THEN 1
       WHEN 'pending' THEN 2
       WHEN 'completed' THEN 3
     END,
     CASE bucket
       WHEN 'action' THEN 1
       WHEN 'project' THEN 2
       WHEN 'blocked' THEN 3
       WHEN 'idea' THEN 4
     END,
     created_at DESC;
   ```

2. Display as a Kanban board with columns:
   - **In Progress** — what's actively being worked on
   - **Pending** — ready to start
   - **Blocked** — waiting on something
   - **Completed** (recent only, last 7 days)

3. Within each column, group by bucket (action, project, idea)

4. Highlight special items:
   - `[NEVER MISS TWICE]` — if a task was skipped yesterday
   - `[DO IT]` — 2-minute tasks that should be done now
   - Tasks with `times_added >= 3` — procrastination flag

5. Show task count summary at the bottom

## Display Format

```
## In Progress
**Actions**
- [ ] Task name [KEYSTONE]

## Pending
**Actions**
- [ ] Quick task [DO IT]
- [ ] Another task

**Projects**
- [ ] Multi-step thing (3 subtasks)

## Blocked
- [ ] Waiting on X from @person
```

## Persona

Keep it clean and scannable. The goal is clarity, not overwhelm.
