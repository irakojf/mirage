"""Shared exceptions for Mirage core."""


class MirageCoreError(Exception):
    """Base exception for mirage_core."""


class ValidationError(MirageCoreError):
    """Raised when domain inputs fail validation."""


class DependencyError(MirageCoreError):
    """Raised when external dependencies are missing or misconfigured."""


class ConfigError(MirageCoreError):
    """Raised when configuration is invalid or missing."""
