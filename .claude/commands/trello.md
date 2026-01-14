# Show Tasks (Kanban View)

Display all tasks organized as a Kanban board.

## Instructions

1. Query all tasks grouped by status and bucket:
   ```sql
   SELECT * FROM tasks ORDER BY
     CASE status
       WHEN 'open' THEN 1
       WHEN 'done' THEN 2
       WHEN 'archived' THEN 3
     END,
     CASE bucket
       WHEN 'action' THEN 1
       WHEN 'project' THEN 2
       WHEN 'blocked' THEN 3
       WHEN 'idea' THEN 4
     END,
     first_added_at DESC;
   ```

2. Display as a Kanban board with columns:
   - **Open** — tasks ready to work on (grouped by bucket)
   - **Done** (recent only, last 7 days)
   - **Archived** — old completed tasks (count only)

3. Within each column, group by bucket (action, project, blocked, idea)

4. Highlight special items:
   - `[NEVER MISS TWICE]` — if a task was skipped yesterday
   - `[DO IT]` — 2-minute tasks that should be done now
   - Tasks with `times_added >= 3` — procrastination flag

5. Show task count summary at the bottom

## Display Format

```
## Open Tasks

**Actions**
- [ ] Task name [KEYSTONE]
- [ ] Quick task [DO IT]

**Projects**
- [ ] Multi-step thing

**Blocked**
- [ ] Waiting on X from @person

**Ideas**
- [ ] Something to explore

## Recently Done (7 days)
- [x] Completed task
```

## Persona

Keep it clean and scannable. The goal is clarity, not overwhelm.
