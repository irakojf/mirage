---
name: done
description: End brain dump session, process and categorize all captured tasks
---

## Instructions

When the user runs /done, process the brain dump:

### 1. Close the Session

```sql
UPDATE dump_sessions
SET ended_at = datetime('now'), raw_input = '<full transcript>'
WHERE id = '<session_id>';
```

### 2. Parse into Discrete Tasks

Extract individual tasks from the raw input. Each task should be:
- A single actionable item OR
- A project that needs breakdown OR
- An idea that needs more thinking OR
- Something blocked on external factors

### 3. Deduplicate (Semantic Search)

For each extracted task, fetch ALL open tasks:

```sql
SELECT id, content, times_added, first_added_at
FROM tasks
WHERE status = 'open';
```

Then use **semantic similarity** (not keyword matching) to find duplicates:
- Compare meaning, not exact words
- "Email Jake about contract" = "Send Jake the contract renewal email" = "Follow up with Jake re: contract"
- "Schedule dentist" = "Book dentist appointment" = "Call dentist"

If a semantic match exists:
- Increment `times_added`
- Update `last_added_at`
- **Rename/normalize** the task content to the clearest, most actionable phrasing
- Add a task_mention record linking to this session

If new:
- Create new task record with unique id
- **Clean up the phrasing**: Transform raw dump language into clear, action-oriented task names

**Renaming Guidelines:**
| Raw Input | Cleaned Task Name |
|-----------|-------------------|
| "need to fix the auth bug" | "Fix authentication bug" |
| "should probably email jake about the contract" | "Email Jake: contract renewal" |
| "oh and dentist" | "Schedule dentist appointment" |
| "that thing with the api" | "Resolve API issue" (ask for clarification) |

### 4. Auto-Label Each Task (Knowledge-Base Informed)

Use your judgment to categorize, **referencing the knowledge base when helpful**:

| Bucket | Criteria | Examples |
|--------|----------|----------|
| **action** | Single sitting, clear next step, concrete | "Email Jake", "Fix auth bug", "Schedule dentist" |
| **project** | Multi-step, needs breakdown, vague scope | "Plan Q1 goals", "Redesign website", "Automate reports" |
| **idea** | Needs thinking, exploratory, "maybe/might/could" | "Maybe start a podcast", "Think about new pricing" |
| **blocked** | Waiting on someone/something external | "API migration - waiting on DevOps" |

**Knowledge Base Reference:**
When uncertain about categorization or wanting to improve judgment, consult:
- `knowledge/atomic-habits.pdf` - For principles on habit formation, the 2-minute rule, identity-based decisions
- `knowledge/tim-ferris-podcast.txt` - For prioritization frameworks, "what would this look like if it were easy?"
- `knowledge/principles.md` - Distilled decision rules (create this as you learn patterns)

**When to reference knowledge base:**
- Distinguishing action vs project (Is this really one step, or am I fooling myself?)
- Deciding if something is truly blocked vs just uncomfortable
- Determining if an "idea" is actually a project in disguise
- Improving task phrasing to be more actionable

### 5. Estimate Duration (Actions Only)

For action items, estimate minutes:
- 2 min: Quick messages, simple lookups
- 5 min: Short emails, small fixes
- 15 min: Focused tasks, reviews
- 30 min: Deep work blocks
- 60+ min: Major work sessions

Apply the **2-minute rule** from Atomic Habits: If it takes less than 2 minutes, flag it for immediate execution.

### 6. Break Down Projects

For each project, auto-generate the first "2-minute starting action":

Example:
- Project: "Plan Q1 goals with team"
- First action: "Create blank Q1 planning doc" (~2 min)

Reference the knowledge base for the "what would this look like if it were easy?" framework when breaking down intimidating projects.

Insert the first action as a subtask:
```sql
INSERT INTO tasks (id, content, bucket, estimated_minutes, parent_task_id)
VALUES ('<id>', '<first action>', 'action', 2, '<project_id>');
```

### 7. Set Follow-up Dates (Blocked Items)

For blocked items, set a reasonable follow_up_date (default: 3 days from now).

### 8. Ask Follow-up Questions

After initial categorization, ask clarifying questions:

> "Quick questions to help me organize better:"

For vague items:
> "You mentioned '[item]' - is this something you need to do, or more of an idea you're exploring?"

For potential duplicates:
> "This sounds similar to '[existing task]' from [date]. Same thing or different?"

For blocked items:
> "Who specifically are you waiting on for '[item]'? When should I remind you to follow up?"

For projects:
> "For '[project]' - what's the very first tiny step you'd need to take?"

### 9. Display Summary

```
Processed [N] items from this dump:

ACTIONS (X):
  [NEW] Fix authentication bug (~30 min)
  [NEW] Email Jake: contract renewal (~5 min)
  [3x since Dec 1] Schedule dentist appointment (~2 min)

PROJECTS (Y):
  [NEW] Plan Q1 goals
        Next action: "Create blank Q1 doc" (~2 min)
  [2x since Nov 15] Automate weekly reports
        Next action: "List current manual steps" (~5 min)

IDEAS (Z):
  [NEW] Podcast about productivity

BLOCKED (W):
  [NEW] API migration
        Waiting on: DevOps
        Follow up: Jan 16

Run /todo to see your full board.
```

## Key Behaviors

- **Semantic matching**: Match by meaning, not keywords
- **Clean task names**: Transform messy dump text into clear, actionable phrasing
- **Be opinionated**: Make categorization decisions confidently
- **Flag procrastination**: Highlight items with times_added >= 3
- **Always generate first actions**: Every project gets a 2-minute starting step
- **Reference knowledge base**: When in doubt, consult atomic-habits.pdf and tim-ferris-podcast.txt
- **Ask targeted questions**: Focus on clarifying ambiguity, not generic prompts
