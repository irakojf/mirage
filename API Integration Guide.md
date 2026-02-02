
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

Required Task properties:
- Name
- Type
- Status
- Estimated minutes
- Mentioned
- Suggested priority
- Suggested reason

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
