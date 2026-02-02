"""Core business logic for Mirage.

Adapters (Slack, MCP, APIs) should call into this package instead of
implementing decision-making directly.
"""

from .aliases import (
    STATUS_ALIASES,
    TYPE_ALIASES,
    resolve_status,
    resolve_type,
)
from .config import MirageConfig
from .errors import ConfigError, DependencyError, MirageCoreError, ValidationError
from .models import (
    Availability,
    AvailabilityWindow,
    EnergyLevel,
    IdentityId,
    IdentityProfile,
    IdentityStatement,
    Project,
    ProjectId,
    Review,
    ReviewId,
    Task,
    TaskDraft,
    TaskId,
    TaskMutation,
    TaskStatus,
    TaskType,
)
from .ports import (
    CalendarPort,
    IdentityRepository,
    ReviewRepository,
    TaskRepository,
)
from .ingestion import CaptureRequest, CaptureResult, IngestionService
from .principles import (
    DecisionFilter,
    PrincipleSection,
    PrinciplesIndex,
    ThinkingMode,
    clear_cache,
    get_principles,
    load_principles,
    parse_principles,
)
from .services import (
    PROCRASTINATION_THRESHOLD,
    MirageOrchestrator,
    TaskCaptureService,
    filter_actionable,
    flag_procrastinating,
    normalize_task_name,
    sort_by_priority,
)

__all__ = [
    "Availability",
    "AvailabilityWindow",
    "CalendarPort",
    "CaptureRequest",
    "CaptureResult",
    "ConfigError",
    "DependencyError",
    "DecisionFilter",
    "EnergyLevel",
    "IdentityId",
    "IdentityProfile",
    "IdentityRepository",
    "IdentityStatement",
    "IngestionService",
    "MirageConfig",
    "MirageCoreError",
    "MirageOrchestrator",
    "PrinciplesIndex",
    "PROCRASTINATION_THRESHOLD",
    "PrincipleSection",
    "Project",
    "ProjectId",
    "Review",
    "ReviewId",
    "ReviewRepository",
    "STATUS_ALIASES",
    "TYPE_ALIASES",
    "Task",
    "TaskDraft",
    "TaskCaptureService",
    "TaskId",
    "TaskMutation",
    "TaskRepository",
    "TaskStatus",
    "TaskType",
    "ThinkingMode",
    "ValidationError",
    "clear_cache",
    "get_principles",
    "load_principles",
    "parse_principles",
    "filter_actionable",
    "flag_procrastinating",
    "normalize_task_name",
    "resolve_status",
    "resolve_type",
    "sort_by_priority",
]
