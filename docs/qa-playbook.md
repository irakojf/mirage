# QA Playbook

Purpose: keep quality predictable and regressions rare.

## When to Run QA

- Before merging any behavioral change
- Before cutting a release
- After schema changes or migrations

## Core Checks

1. Run unit tests (`python -m pytest`)
2. Run lint and format checks (`ruff check`, `ruff format --check`)
3. Validate schemas if changed (`python schema/validate.py --dry-run`)

## Regression Checklist

- Capture flow still writes cleanly to Notion
- Prioritization output remains stable
- Calendar-fit logic rejects impossible schedules
- Error handling returns actionable messages

## Failure Triage

- If tests fail, fix first or file a bead
- If lint fails, apply `ruff format` and re-run
- If schema validation fails, update both schema and adapter mappings

## Recording QA

Log results in the PR description or release notes:
- What ran
- What failed
- What changed to fix
