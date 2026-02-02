# Calendar Policy

Calendar integration grounds priorities in real available time. Tasks without calendar time are aspirations, not commitments.

## Configuration

All calendar settings live in `MirageConfig` (`mirage_core/config.py`):

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| timezone | `MIRAGE_TIMEZONE` | America/Los_Angeles | Timezone for event creation |
| work_start | `MIRAGE_WORK_START` | 09:00 | Workday start (HH:MM) |
| work_end | `MIRAGE_WORK_END` | 18:00 | Workday end (HH:MM) |
| buffer_minutes | `MIRAGE_BUFFER_MINUTES` | 15 | Buffer on each side of free blocks |
| morning_protection_end | `MIRAGE_MORNING_PROTECTION_END` | 10:00 | Morning block cutoff |

## Buffer Policy

`apply_buffer(windows, buffer_minutes)` shrinks each free-time window by `buffer_minutes` on both sides. This prevents scheduling tasks right at the edge of meetings.

Example: A 2-hour block (9:00–11:00) with 15-min buffer becomes 90 minutes (9:15–10:45).

Windows that become too small after buffering are dropped entirely.

## Morning Protection

`protect_morning(windows, protection_end, date)` reserves the first morning window (before `protection_end`) for the top-priority task. The window is split at the cutoff:

- Morning block: start → cutoff (reserved for #1 task)
- Remaining: cutoff → end (available for other tasks)

If the first window ends before the cutoff, the entire window is the morning block. If all windows start after the cutoff, there is no morning block.

## Do Now Calendar Enforcement

`MirageOrchestrator.get_do_now_list(enforce_calendar=True)` filters actionable tasks:

1. Fetches today's free-time from Google Calendar via `CalendarPort`
2. Applies buffer policy
3. Excludes tasks whose `complete_time_minutes` exceeds the largest available slot
4. Tasks without a time estimate are assumed to fit

If the calendar API is unavailable, all actionable tasks are returned (graceful degradation).

## Slotting Algorithm

`find_slot(task, availability)` uses first-fit:
- Tasks with a time estimate get the first window large enough
- Tasks without an estimate get the largest available window

`require_slot()` raises `SlottingError` if no slot fits.

## Conflict Detection

`detect_conflicts(tasks, availability)` simulates first-fit allocation across all tasks. As each task claims a slot, remaining availability shrinks. Tasks that can't be placed are returned as conflicts.

Tasks without time estimates are skipped (not counted as conflicts).

## Error Handling

Calendar API failures are handled gracefully:
- `safe_get_availability()` returns `None` on error
- `safe_get_week_overview()` returns `None` on error
- Callers proceed without calendar enforcement when unavailable
- Errors are logged at WARNING level for debugging
