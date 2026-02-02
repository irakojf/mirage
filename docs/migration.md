# Migration Guide

## Schema v1.0 → v1.1

### What Changed

1. **Single source of truth** — Consolidated `schema/tasks.yaml` and `schema/notion_tasks.yaml` into one file: `schema/tasks.yaml` v1.1
2. **Status additions** — Added `Not Now` (to-do group) and `Waiting On` (in-progress group)
3. **Type additions** — Added `Do It Now`, `Never Miss 2x`, `Important Not Urgent`, `Unblocks`
4. **Mentioned default** — Changed from 0 to 1 (first mention counts)
5. **Status type fix** — Status property uses Notion's native `status` type, not `select`

### Migration Steps

#### 1. Add Missing Status Options in Notion

Open your Tasks database in Notion → Properties → Status:

- Add `Not Now` to the **To-do** group
- Add `Waiting On` to the **In progress** group

Existing statuses (Tasks, Projects, Ideas, Blocked, Done, Won't Do) should already exist.

#### 2. Add Missing Type Options

Open Properties → Type (select):

- Add: `Do It Now`, `Never Miss 2x`, `Important Not Urgent`, `Unblocks`

Existing types (Identity, Compound) should already exist.

#### 3. Validate

```bash
# Dry run — check schema parses
python schema/validate.py --dry-run

# Live validation
NOTION_TOKEN=secret_... python schema/validate.py
```

#### 4. Update MCP Servers

If running custom Notion MCP server, ensure it reads status using the `status` API (not `select`):

```python
# Correct
status = props["Status"].get("status", {}).get("name", "")

# Wrong (was a bug in v1.0)
status = props["Status"].get("select", {}).get("name", "")
```

#### 5. Delete Legacy File

```bash
rm schema/notion_tasks.yaml  # if it still exists
```

### Backwards Compatibility

- All v1.0 status and type values remain valid
- The `status_aliases` section in `tasks.yaml` maps old names (Action, Project, Idea) to new canonical names
- Existing tasks are unaffected — no data migration needed
- The Mentioned default change only affects new tasks

### Rollback

If issues arise:
1. Revert `schema/tasks.yaml` to v1.0
2. Remove added status/type options from Notion (or leave them — extra options don't break anything)
3. Re-run `python schema/validate.py` to confirm
