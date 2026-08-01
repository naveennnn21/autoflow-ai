"""AutoFlow AI - Prompt compiler exceptions (generated from metadata)."""


class CompilerError(Exception):
    """Base error for the prompt compiler."""


class ParserError(CompilerError):
    """Raised when a WorkflowPlan cannot be parsed."""


class ASTBuildError(CompilerError):
    """Raised when the AST cannot be constructed from a plan."""


class IRBuildError(CompilerError):
    """Raised when the IR cannot be constructed from an AST."""


class ValidationError(CompilerError):
    """Raised when a compiled graph or specification fails validation."""


class GraphValidationError(ValidationError):
    """Raised when a graph structure is invalid."""


class CycleDetectedError(GraphValidationError):
    """Raised when a dependency cycle is detected."""


class DisconnectedGraphError(GraphValidationError):
    """Raised when a graph has unreachable nodes."""


class UndefinedVariableError(ValidationError):
    """Raised when a variable is referenced but not defined."""


class UnusedVariableError(ValidationError):
    """Raised when a declared variable is never used."""


class InvalidExpressionError(ValidationError):
    """Raised when an expression cannot be compiled."""


class InvalidConditionError(ValidationError):
    """Raised when a condition cannot be compiled."""


class InvalidLoopError(ValidationError):
    """Raised when a loop specification is invalid."""


class OptimizationError(CompilerError):
    """Raised when an optimization pass fails."""


class SerializationError(CompilerError):
    """Raised when a specification cannot be serialized."""


class DeserializationError(CompilerError):
    """Raised when a specification cannot be loaded."""


class VersionError(CompilerError):
    """Raised for unsupported specification versions."""


class MigrationError(CompilerError):
    """Raised when automatic migration fails."""
