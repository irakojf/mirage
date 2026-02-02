"""Shared exceptions and error telemetry for Mirage core."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Telemetry hook: called on every MirageCoreError with (error, context_dict).
# Set via set_error_hook(). Default: log at ERROR level.
_error_hook: Optional[Callable[[Exception, dict[str, Any]], None]] = None


def set_error_hook(hook: Optional[Callable[[Exception, dict[str, Any]], None]]) -> None:
    """Register a global error telemetry hook.

    The hook receives (exception, context_dict) for every MirageCoreError.
    Pass None to reset to default logging behavior.
    """
    global _error_hook
    _error_hook = hook


def _emit(error: Exception, **context: Any) -> None:
    """Emit an error event to the telemetry hook or default logger."""
    ctx = {
        "error_type": type(error).__name__,
        "message": str(error),
        **context,
    }
    if _error_hook is not None:
        try:
            _error_hook(error, ctx)
        except Exception:
            logger.warning("Error hook failed", exc_info=True)
    else:
        logger.error("mirage_core error: %s", ctx)


class MirageCoreError(Exception):
    """Base exception for mirage_core."""

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.context = context
        _emit(self, **context)


class ValidationError(MirageCoreError):
    """Raised when domain inputs fail validation."""


class DependencyError(MirageCoreError):
    """Raised when external dependencies are missing or misconfigured."""


class ConfigError(MirageCoreError):
    """Raised when configuration is invalid or missing."""


class SlottingError(MirageCoreError):
    """Raised when calendar slotting fails or is invalid."""
