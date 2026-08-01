"""AutoFlow AI - AI planner exceptions (generated from metadata).

A single exception hierarchy for the planning pipeline so callers can
catch one base type and inspect ``stage`` for granular handling.
"""

from typing import Optional


class PlannerError(Exception):
    """Base class for all AI planner errors."""

    def __init__(self, message: str = "", stage: str = "",
                 kind: str = "planner_error") -> None:
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.kind = kind


class NormalizationError(PlannerError):
    """Raised when a prompt cannot be normalized."""

    def __init__(self, message: str = "", stage: str = "normalize") -> None:
        super().__init__(message, stage=stage, kind="normalization_error")


class IntentError(PlannerError):
    """Raised when intent cannot be classified."""

    def __init__(self, message: str = "", stage: str = "intent") -> None:
        super().__init__(message, stage=stage, kind="intent_error")


class EntityExtractionError(PlannerError):
    """Raised when entity extraction fails."""

    def __init__(self, message: str = "", stage: str = "entities") -> None:
        super().__init__(message, stage=stage, kind="entity_extraction_error")


class ConnectorDiscoveryError(PlannerError):
    """Raised when connector discovery fails."""

    def __init__(self, message: str = "", stage: str = "connectors") -> None:
        super().__init__(message, stage=stage, kind="connector_discovery_error")


class CapabilityMatchError(PlannerError):
    """Raised when no connector capability matches a task."""

    def __init__(self, message: str = "", stage: str = "capabilities") -> None:
        super().__init__(message, stage=stage, kind="capability_match_error")


class ConstraintError(PlannerError):
    """Raised when plan constraints cannot be satisfied."""

    def __init__(self, message: str = "", stage: str = "constraints") -> None:
        super().__init__(message, stage=stage, kind="constraint_error")


class GraphError(PlannerError):
    """Raised when the workflow graph is invalid (cycles, disconnects)."""

    def __init__(self, message: str = "", stage: str = "graph") -> None:
        super().__init__(message, stage=stage, kind="graph_error")


class PlanValidationError(PlannerError):
    """Raised when the generated plan fails validation."""

    def __init__(self, message: str = "", stage: str = "validate",
                 errors: Optional[list] = None) -> None:
        super().__init__(message, stage=stage, kind="validation_error")
        self.errors = errors or []


class ProviderError(PlannerError):
    """Raised when an LLM provider call fails."""

    def __init__(self, message: str = "", stage: str = "llm",
                 provider: str = "") -> None:
        super().__init__(message, stage=stage, kind="provider_error")
        self.provider = provider


class ProviderNotConfiguredError(ProviderError):
    """Raised when the requested provider has no API key configured."""

    def __init__(self, provider: str = "", stage: str = "llm") -> None:
        super().__init__(f"Provider '{provider}' is not configured",
                         stage=stage, provider=provider)


class AmbiguityError(PlannerError):
    """Raised when the prompt is too ambiguous to plan safely."""

    def __init__(self, message: str = "", stage: str = "ambiguity",
                 questions: Optional[list] = None) -> None:
        super().__init__(message, stage=stage, kind="ambiguity_error")
        self.questions = questions or []
