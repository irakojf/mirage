# Integration Test Plan

Focus: validate end-to-end behavior across adapters.

## Core Scenarios

1. Slack capture → Notion task created with correct fields
2. Prioritize request → stable ordering + reasons returned
3. Calendar availability → task fit evaluation respected
4. Review flow → weekly review saved and parsed

## Fixtures

- Use stable example tasks with known priorities
- Use deterministic timestamps (UTC) to avoid flakiness
- Use sanitized Notion/Calendar responses

## Execution

- Prefer running against mock adapters
- If running live, isolate to a test workspace

## Exit Criteria

- All core scenarios pass
- No new warnings in logs
