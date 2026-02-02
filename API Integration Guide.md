
# API Integration Guide (Notion & Google Calendar)

This guide defines how Mirage integrates with external APIs safely and consistently.

---

## 1. General Rules

- Prefer MCP servers over direct API calls
- Never hardcode IDs in multiple places
- Validate schema assumptions at runtime
- Fail fast on mismatches

---

## 2. Notion API Integration

- Notion is the only persistent store
- Every write must confirm the property exists
- Missing properties are errors
- Canonical schema lives in `schema/tasks.yaml` (single source of truth)
- Run `python schema/validate.py` to check for drift

Required Task properties:
- Name (title)
- Status (status)

Optional Task properties:
- Mentioned (number — procrastination counter)
- Blocked (rich_text — who/what is blocking)
- Energy (select — Red, Yellow, Green)
- Type (select — Identity, Compound, Do It Now, Never Miss 2x, Important Not Urgent, Unblocks)
- Complete Time (number — estimated minutes)
- Priority (number — 1 = highest)

---

## 3. Google Calendar Integration

- Calendar is truth
- Tasks without calendar time are not commitments
- Timezone must be explicit (never hardcoded)

---

## 4. Slack Integration

Slack is an intake surface, not the system.

Allowed:
- Capture tasks
- Trigger explicit commands

Disallowed:
- Implicit coaching
- Silent intent guessing

---

## 5. Rate Limits & Retries

- Use exponential backoff
- Log and surface failures

---

## 6. Security

- Never commit secrets
- Store tokens securely
- Rotate tokens when needed

---

## 7. Migration Safety

When changing schema:
1. Validate
2. Migrate
3. Re-validate
4. Deploy
