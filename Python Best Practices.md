
# Python Best Practices for Mirage

This guide defines how Python should be written in Mirage.
The goal is **clarity, safety, and debuggability**, not cleverness.

---

## 1. Code Organization

Business logic lives in `mirage_core/`.
Adapters (Slack, MCP, APIs) contain no decision-making.

---

## 2. Data Modeling

- Use dataclasses or pydantic models
- Never pass raw dicts internally
- Validate early, fail loudly

---

## 3. Error Handling

- Catch API/network errors explicitly
- Re-raise with context
- Never use bare `except`

---

## 4. Side Effects

Functions should be either:
- Pure (return values only)
- Effectful (clearly named, e.g. `write_task_to_notion`)

Never mix both.

---

## 5. Logging

- Use structured logs
- Include IDs (task_id, project_id)
- Never log secrets

---

## 6. Testing Expectations

- Test priority logic
- Test deduplication
- Test calendar-fit logic

Focus on correctness, not coverage.

---

## 7. Code Review Checklist

Before merging:
- Does this reduce cognitive load?
- Does this respect calendar realism?
- Does this make failure modes clearer?
- Would future-you understand this in 6 months?
