"""Lightweight error telemetry for Mirage.

Provides a hook-based system for capturing failures with context.
Default handler logs structured error data; additional handlers
can be registered for external services (Sentry, etc.) later.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

ErrorHandler = Callable[["ErrorEvent"], None]

_handlers: list[ErrorHandler] = []


@dataclass(frozen=True)
class ErrorEvent:
    """Structured error event with context."""

    error: Exception
    source: str  # e.g. "notion_repo", "slack_server", "calendar"
    operation: str  # e.g. "create_task", "query_tasks"
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def error_type(self) -> str:
        return type(self.error).__name__

    @property
    def message(self) -> str:
        return str(self.error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "source": self.source,
            "operation": self.operation,
            "context": self.context,
            "timestamp": self.timestamp,
        }


def register_handler(handler: ErrorHandler) -> None:
    """Register an error handler to receive all error events."""
    _handlers.append(handler)


def clear_handlers() -> None:
    """Remove all registered error handlers."""
    _handlers.clear()


def capture_error(
    error: Exception,
    *,
    source: str,
    operation: str,
    context: Optional[dict[str, Any]] = None,
) -> ErrorEvent:
    """Capture an error event and dispatch to all registered handlers.

    Always logs via the default logger. Additional handlers receive
    the structured ErrorEvent for custom processing.
    """
    event = ErrorEvent(
        error=error,
        source=source,
        operation=operation,
        context=context or {},
    )

    # Always log
    logger.error(
        "%s.%s failed: %s: %s",
        event.source,
        event.operation,
        event.error_type,
        event.message,
        extra={"telemetry": event.to_dict()},
    )

    # Dispatch to registered handlers
    for handler in _handlers:
        try:
            handler(event)
        except Exception:
            # Never let a telemetry handler crash the application
            logger.debug("Telemetry handler failed", exc_info=True)

    return event
