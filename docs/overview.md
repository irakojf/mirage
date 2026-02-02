# System Overview

Mirage is a personal task management agent inspired by James Clear's Atomic Habits. It surfaces what matters, confronts procrastination with curiosity, and grounds priorities in real calendar time.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Surfaces                       │
│  Slack (/mirage, /prioritize…)    Claude Code    │
│         ↓                              ↓         │
├─────────────────────────────────────────────────┤
│                 mirage_core                       │
│  ingestion → prioritization → calendar slotting  │
│  principles    review         services           │
├─────────────────────────────────────────────────┤
│                   Ports                          │
│  TaskRepository  CalendarPort  ReviewRepository  │
│  IdentityRepository                              │
├─────────────────────────────────────────────────┤
│                  Adapters                         │
│  Notion MCP     Google Calendar MCP    Slack Bot  │
└─────────────────────────────────────────────────┘
```

## Data Flow

1. **Capture** — Tasks enter via Slack (`/mirage`, message shortcut, `@mirage`, DM) or Claude Code (`/dump`, `/done`)
2. **Ingest** — `IngestionService` normalizes, deduplicates, and persists to Notion
3. **Prioritize** — `prioritize()` applies Atomic Habits decision filters and scores tasks
4. **Slot** — Calendar functions check whether tasks fit in today's free time
5. **Review** — `ReviewService` generates weekly retrospectives with energy and procrastination analysis

## Key Design Decisions

- **Notion is the single data store** — tasks, reviews, identity all live in Notion
- **Hexagonal architecture** — core logic depends on abstract ports, not concrete APIs
- **Schema-as-code** — `schema/tasks.yaml` is the single source of truth for Notion properties
- **Deterministic prioritization** — rule-based scoring with manual override support; LLM used only for conflict resolution
- **Calendar realism** — Do Now list is filtered by actual available time

## Package Structure

```
mirage_core/           # Pure business logic (no I/O)
  models.py            # Domain models (Task, TaskDraft, enums)
  ports.py             # Abstract interfaces (TaskRepository, CalendarPort)
  services.py          # Orchestration (MirageOrchestrator, TaskCaptureService)
  ingestion.py         # Capture pipeline with dedup
  prioritization.py    # Layered priority scoring
  calendar.py          # Availability, buffering, slotting
  principles.py        # Principles parser and thinking modes
  review.py            # Weekly review data generation
  aliases.py           # Status/type alias resolution
  config.py            # Centralized configuration
  errors.py            # Shared exceptions

schema/                # Database schema definitions
  tasks.yaml           # Canonical Notion task properties
  views.yaml           # Notion board/list view specs
  validate.py          # Schema drift validator
  kanban_sync.py       # Integrity checker

mcp/notion/            # Notion MCP server
mcp/slack/             # Slack bot (fly.io)
knowledge/             # Atomic Habits reference material
tests/                 # Test suite
```

## Core Principles

1. **Identity over outcomes** — "Who do you want to become?" drives prioritization
2. **2-minute rule** — If it takes <2 min, do it now
3. **Never miss twice** — Skipped yesterday? Top priority today
4. **Important Not Urgent** — Eisenhower Q2 strategic work
5. **1% better** — Small compounding actions beat big one-time efforts
6. **Systems > Goals** — Focus on the process, not just the outcome
