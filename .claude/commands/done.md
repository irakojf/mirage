# Process Brain Dump

End the current brain dump session and process all captured items into organized tasks.

## Instructions

1. Close the dump session:
   ```sql
   UPDATE dump_sessions SET ended_at = datetime('now') WHERE ended_at IS NULL;
   ```

2. For each item captured during the dump:
   - **Clean the task name**: Transform messy input into clear, actionable phrasing
   - **Assign a bucket**: action, project, idea, or blocked
   - **Check for duplicates**: Query existing tasks by meaning (semantic match, not just keywords)
   - **Apply priority tags** where appropriate:
     - `[DO IT]` — takes ≤2 minutes
     - `[KEYSTONE]` — unlocks other tasks
     - `[COMPOUNDS]` — 1% improvement, builds over time
     - `[IDENTITY]` — aligns with user's identity goals

3. Insert new tasks:
   ```sql
   INSERT INTO tasks (name, bucket, status, priority_tags, created_at, times_added)
   VALUES (?, ?, 'pending', ?, datetime('now'), 1);
   ```

4. For duplicates, increment `times_added`:
   ```sql
   UPDATE tasks SET times_added = times_added + 1 WHERE id = ?;
   ```

5. Flag procrastination: If `times_added >= 3`, surface it:
   > "You've mentioned '[task]' 3+ times now. What's blocking you from doing it?"

6. Show a summary of what was processed:
   - New tasks added (by bucket)
   - Duplicates found
   - Any `[DO IT]` items to handle immediately

## Persona

Be encouraging. Celebrate the dump being complete. Help them see the chaos is now organized.
