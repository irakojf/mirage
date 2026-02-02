"""Centralized configuration with validation and defaults.

All environment variables and database IDs are resolved here.
Adapters should use MirageConfig instead of reading os.environ directly.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from .errors import ConfigError

# Matches 32 hex chars (no dashes) or 8-4-4-4-12 UUID format
_NOTION_ID_RE = re.compile(
    r"^[0-9a-f]{32}$|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _validate_notion_id(value: str, label: str) -> None:
    """Raise ConfigError if *value* is not a valid Notion ID."""
    if not value:
        raise ConfigError(f"{label} is required (set the corresponding env var)")
    if not _NOTION_ID_RE.match(value):
        raise ConfigError(f"{label} is not a valid Notion ID: {value!r}")


@dataclass(frozen=True)
class MirageConfig:
    """Validated configuration for the Mirage system."""

    # Notion
    notion_token: str = ""
    tasks_database_id: str = "2ea35d23-b569-80cc-99be-e6d6a17b1548"
    reviews_database_id: str = "2eb35d23-b569-8040-859f-d5baff2957ab"
    production_calendar_id: str = "28535d23-b569-80d3-b186-d1886bc53f0b"
    identity_page_id: str = "2eb35d23b569808eb1ecc18dc3903100"

    # Calendar
    timezone: str = "America/Los_Angeles"
    work_start: str = "09:00"
    work_end: str = "18:00"
    buffer_minutes: int = 15
    morning_protection_end: str = "10:00"

    # Procrastination
    procrastination_threshold: int = 3

    @classmethod
    def from_env(cls) -> MirageConfig:
        """Load config from environment variables with validation.

        Environment variables override the dataclass defaults so that IDs
        are defined in exactly one place.
        """
        defaults = cls()
        token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY", "")

        return cls(
            notion_token=token,
            tasks_database_id=os.environ.get(
                "MIRAGE_TASKS_DB", defaults.tasks_database_id
            ),
            reviews_database_id=os.environ.get(
                "MIRAGE_REVIEWS_DB", defaults.reviews_database_id
            ),
            production_calendar_id=os.environ.get(
                "MIRAGE_CALENDAR_DB", defaults.production_calendar_id
            ),
            identity_page_id=os.environ.get(
                "MIRAGE_IDENTITY_PAGE", defaults.identity_page_id
            ),
            timezone=os.environ.get("MIRAGE_TIMEZONE", defaults.timezone),
            work_start=os.environ.get("MIRAGE_WORK_START", defaults.work_start),
            work_end=os.environ.get("MIRAGE_WORK_END", defaults.work_end),
            buffer_minutes=int(
                os.environ.get("MIRAGE_BUFFER_MINUTES", str(defaults.buffer_minutes))
            ),
            morning_protection_end=os.environ.get(
                "MIRAGE_MORNING_PROTECTION_END", defaults.morning_protection_end
            ),
            procrastination_threshold=int(
                os.environ.get(
                    "MIRAGE_PROCRASTINATION_THRESHOLD",
                    str(defaults.procrastination_threshold),
                )
            ),
        )

    def validate(self) -> None:
        """Raise ConfigError if required values are missing or malformed."""
        if not self.notion_token:
            raise ConfigError(
                "NOTION_TOKEN or NOTION_API_KEY environment variable is required"
            )
        _validate_notion_id(self.tasks_database_id, "MIRAGE_TASKS_DB")
        _validate_notion_id(self.reviews_database_id, "MIRAGE_REVIEWS_DB")
        _validate_notion_id(self.production_calendar_id, "MIRAGE_CALENDAR_DB")
        _validate_notion_id(self.identity_page_id, "MIRAGE_IDENTITY_PAGE")
