# Notion Schema Reference

Database ID: `2ea35d23-b569-80cc-99be-e6d6a17b1548`

Canonical schema: `schema/tasks.yaml` (v1.1)

## Properties

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| Name | title | yes | — | Task description, clear actionable phrasing |
| Status | status | yes | Tasks | Workflow state (see Status below) |
| Mentioned | number | no | 1 | Procrastination counter, flag at 3+ |
| Blocked | rich_text | no | — | Who/what is blocking this task |
| Energy | select | no | — | Red, Yellow, Green |
| Type | select | no | — | Coaching tag (see Type below) |
| Complete Time | number | no | — | Estimated minutes to complete |
| Priority | number | no | — | Manual priority ranking, 1 = highest |

## Status Values

Uses Notion's native status type (not select). Grouped into three categories:

**To-do:**
| Status | Meaning |
|--------|---------|
| Tasks | Single sitting, clear next step — do this week |
| Projects | Multi-step, needs breakdown |
| Ideas | Fuzzy, needs more thinking |
| Not Now | Parked — revisit in weekly review |

**In progress:**
| Status | Meaning |
|--------|---------|
| Blocked | Waiting on someone/something |
| Waiting On | Explicit external dependency |

**Complete:**
| Status | Meaning |
|--------|---------|
| Done | Completed |
| Won't Do | Decided against — kept for record |

### Status Aliases

MCP tools accept these aliases (mapped to canonical names):

| Alias | Maps to |
|-------|---------|
| Action, action | Tasks |
| Project, project | Projects |
| Idea, idea | Ideas |
| blocked | Blocked |
| done | Done |

## Type Values

| Type | Tag | Meaning |
|------|-----|---------|
| Identity | `[IDENTITY]` | Aligns with identity goals |
| Compound | `[COMPOUNDS]` | 1% improvement, builds over time |
| Do It Now | `[DO IT]` | ≤2 min, do immediately |
| Never Miss 2x | `[NEVER MISS 2x]` | Skipped yesterday |
| Important Not Urgent | `[COMPOUNDS]` | Eisenhower Q2 — strategic, not urgent |
| Unblocks | `[KEYSTONE]` | Unlocks other tasks |

Alias: `Compounds` → `Compound`

## Integrity Rules

Defined in `schema/views.yaml` and enforced by `schema/kanban_sync.py`:

1. **Blocked requires reason** — Tasks in Blocked/Waiting On status must have the Blocked field filled
2. **Completed clears priority** — Done/Won't Do tasks should not have an active Priority value

## Validation

```bash
# Parse schema only (no API call)
python schema/validate.py --dry-run

# Validate against live Notion database
NOTION_TOKEN=secret_... python schema/validate.py

# Check integrity rules
NOTION_TOKEN=secret_... python schema/kanban_sync.py
```

## Domain Model Mapping

The `mirage_core.models` module mirrors these properties:

```python
class TaskStatus(str, Enum):
    TASKS = "Tasks"
    PROJECTS = "Projects"
    IDEAS = "Ideas"
    NOT_NOW = "Not Now"
    BLOCKED = "Blocked"
    WAITING_ON = "Waiting On"
    DONE = "Done"
    WONT_DO = "Won't Do"

class TaskType(str, Enum):
    IDENTITY = "Identity"
    COMPOUND = "Compound"
    DO_IT_NOW = "Do It Now"
    NEVER_MISS_2X = "Never Miss 2x"
    IMPORTANT_NOT_URGENT = "Important Not Urgent"
    UNBLOCKS = "Unblocks"

class EnergyLevel(str, Enum):
    RED = "Red"
    YELLOW = "Yellow"
    GREEN = "Green"
```
