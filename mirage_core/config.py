"""Centralized configuration with validation and defaults.

All environment variables and database IDs are resolved here.
Adapters should use MirageConfig instead of reading os.environ directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from .errors import ConfigError


@dataclass(frozen=True)
class MirageConfig:
    """Validated configuration for the Mirage system."""

    # Notion
    notion_token: str = ""
    tasks_database_id: str = "2ea35d23-b569-80cc-99be-e6d6a17b1548"
    reviews_database_id: str = "2eb35d23-b569-8040-859f-d5baff2957ab"
    production_calendar_id: str = "28535d23-b569-80d3-b186-d1886bc53f0b"
    identity_page_id: str = "2eb35d23b569808eb1ecc18dc3903100"

    # Procrastination
    procrastination_threshold: int = 3

    @classmethod
    def from_env(cls) -> MirageConfig:
        """Load config from environment variables with validation."""
        token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY", "")

        return cls(
            notion_token=token,
            tasks_database_id=os.environ.get(
                "MIRAGE_TASKS_DB", "2ea35d23-b569-80cc-99be-e6d6a17b1548"
            ),
            reviews_database_id=os.environ.get(
                "MIRAGE_REVIEWS_DB", "2eb35d23-b569-8040-859f-d5baff2957ab"
            ),
            production_calendar_id=os.environ.get(
                "MIRAGE_CALENDAR_DB", "28535d23-b569-80d3-b186-d1886bc53f0b"
            ),
            identity_page_id=os.environ.get(
                "MIRAGE_IDENTITY_PAGE", "2eb35d23b569808eb1ecc18dc3903100"
            ),
            procrastination_threshold=int(
                os.environ.get("MIRAGE_PROCRASTINATION_THRESHOLD", "3")
            ),
        )

    def validate(self) -> None:
        """Raise ConfigError if required values are missing."""
        if not self.notion_token:
            raise ConfigError(
                "NOTION_TOKEN or NOTION_API_KEY environment variable is required"
            )
        if not self.tasks_database_id:
            raise ConfigError("Tasks database ID is required")
