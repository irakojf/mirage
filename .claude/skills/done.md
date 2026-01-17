---
name: done
description: End brain dump session, process and categorize all captured tasks
---

## Instructions

When the user runs /done, process the brain dump:

### 1. Parse into Discrete Tasks

Extract individual tasks from the raw input shared during the dump. Each task should be:
- A single actionable item OR
- A project that needs breakdown OR
- An idea that needs more thinking OR
- Something blocked on external factors

### 2. Deduplicate (Semantic Search)

For each extracted task, fetch ALL open tasks using Notion MCP:

```
Call: mcp__notion__query_tasks
Arguments: { "exclude_done": true }
```

Then use **semantic similarity** (not keyword matching) to find duplicates:
- Compare meaning, not exact words
- "Email Jake about contract" = "Send Jake the contract renewal email" = "Follow up with Jake re: contract"
- "Schedule dentist" = "Book dentist appointment" = "Call dentist"

If a semantic match exists, increment the mention count:

```
Call: mcp__notion__increment_task_mention
Arguments: { "page_id": "<matched_task_id>" }
```

If new, create the task:

```
Call: mcp__notion__create_task
Arguments: {
    "content": "Clean, actionable task description",
    "status": "Action",
    "estimated_minutes": 15,
    "tags": ["Identity", "Compounding"]
}
```

**Renaming Guidelines:**
| Raw Input | Cleaned Task Name |
|-----------|-------------------|
| "need to fix the auth bug" | "Fix authentication bug" |
| "should probably email jake about the contract" | "Email Jake: contract renewal" |
| "oh and dentist" | "Schedule dentist appointment" |
| "that thing with the api" | "Resolve API issue" (ask for clarification) |

### 3. Auto-Label Each Task (Knowledge-Base Informed)

Use your judgment to categorize, **referencing the knowledge base when helpful**:

| Status | Criteria | Examples |
|--------|----------|----------|
| **Action** | Single sitting, clear next step, concrete | "Email Jake", "Fix auth bug", "Schedule dentist" |
| **Project** | Multi-step, needs breakdown, vague scope | "Plan Q1 goals", "Redesign website", "Automate reports" |
| **Idea** | Needs thinking, exploratory, "maybe/might/could" | "Maybe start a podcast", "Think about new pricing" |
| **Blocked** | Waiting on someone/something external | "API migration - waiting on DevOps" |

**Knowledge Base Reference:**
When uncertain about categorization or wanting to improve judgment, consult:
- `knowledge/atomic-habits.pdf` - For principles on habit formation, the 2-minute rule, identity-based decisions
- `knowledge/tim-ferris-podcast.txt` - For prioritization frameworks, "what would this look like if it were easy?"
- `knowledge/principles.md` - Distilled decision rules

### 4. Apply Tags

Use the `tags` parameter when creating tasks:
- `Identity` - Aligns with who the user wants to become
- `Compounding` - 1% improvement that builds over time
- `Keystone` - Unlocks other tasks or creates ripple effects

### 5. Estimate Duration (Actions Only)

For action items, estimate minutes:
- 2 min: Quick messages, simple lookups - flag as `[DO IT]`
- 5 min: Short emails, small fixes
- 15 min: Focused tasks, reviews
- 30 min: Deep work blocks
- 60+ min: Major work sessions

Apply the **2-minute rule** from Atomic Habits: If it takes less than 2 minutes, flag it for immediate execution.

### 6. Handle Blocked Items

For blocked items, include the `blocked_by` parameter:

```
Call: mcp__notion__create_task
Arguments: {
    "content": "API migration",
    "status": "Blocked",
    "blocked_by": "DevOps team"
}
```

### 7. Ask Follow-up Questions

After initial categorization, ask clarifying questions:

> "Quick questions to help me organize better:"

For vague items:
> "You mentioned '[item]' - is this something you need to do, or more of an idea you're exploring?"

For potential duplicates:
> "This sounds similar to '[existing task]'. Same thing or different?"

For blocked items:
> "Who specifically are you waiting on for '[item]'? When should I remind you to follow up?"

For projects:
> "For '[project]' - what's the very first tiny step you'd need to take?"

### 8. Display Summary

```
Processed [N] items from this dump:

ACTIONS (X):
  [NEW] Fix authentication bug (~30 min)
  [NEW] Email Jake: contract renewal (~5 min)
  [3x] Schedule dentist appointment (~2 min) [DO IT]

PROJECTS (Y):
  [NEW] Plan Q1 goals

IDEAS (Z):
  [NEW] Podcast about productivity

BLOCKED (W):
  [NEW] API migration
        Waiting on: DevOps

Run /trello to see your full board.
```

## Key Behaviors

- **Semantic matching**: Match by meaning, not keywords
- **Clean task names**: Transform messy dump text into clear, actionable phrasing
- **Be opinionated**: Make categorization decisions confidently
- **Flag procrastination**: Highlight items with mentioned >= 3
- **Reference knowledge base**: When in doubt, consult atomic-habits.pdf and tim-ferris-podcast.txt
- **Ask targeted questions**: Focus on clarifying ambiguity, not generic prompts
