"""AutoFlow AI - Prompt Compiler package (generated from metadata).

The Prompt Compiler transforms a WorkflowPlan produced by the AI Planner
into a deterministic, versioned Workflow Specification v1 consumed by the
Workflow Runtime.

Design rule: the AI Planner reasons, the Prompt Compiler compiles, the
Workflow Runtime executes, the Connector Framework communicates. The
compiler never executes workflows and never calls connectors.
"""

from app.compiler.compiler import PromptCompiler
from app.compiler.exceptions import (
    ASTBuildError, CompilerError, CycleDetectedError,
    DeserializationError, DisconnectedGraphError, GraphValidationError,
    InvalidConditionError, InvalidExpressionError, InvalidLoopError,
    IRBuildError, MigrationError, OptimizationError, ParserError,
    SerializationError, UndefinedVariableError, UnusedVariableError,
    ValidationError, VersionError,
)
from app.compiler.metrics import CompilationMetrics
from app.compiler.models import (
    CompileOptions, CompileReport, ConditionSpec, ConnectorBinding,
    ConstantDef, ErrorHandlingConfig, ExpressionSpec, LoopSpec,
    OptimizationStat, OutputSpec, RetryPolicy, RuntimeSettings,
    TimeoutConfig, VariableDef,
)
from app.compiler.pipeline import CompilationPipeline, STAGE_NAMES
from app.compiler.serializer import (
    export_schema, pretty_print, to_binary, to_json, to_yaml,
)
from app.compiler.validator import WorkflowSpecificationValidator
from app.compiler.versioning import SpecVersionManager
from app.compiler.workflow_spec import (
    SPEC_VERSION, SUPPORTED_SPEC_VERSIONS, WorkflowSpecification,
)

__all__ = [
    "ASTBuildError", "CompilationMetrics", "CompilationPipeline",
    "CompileOptions", "CompileReport", "CompilerError",
    "ConditionSpec", "ConnectorBinding", "ConstantDef", "CycleDetectedError",
    "DeserializationError", "DisconnectedGraphError", "ErrorHandlingConfig",
    "ExpressionSpec", "GraphValidationError", "IRBuildError",
    "InvalidConditionError", "InvalidExpressionError", "InvalidLoopError",
    "LoopSpec", "MigrationError", "OptimizationError", "OptimizationStat",
    "OutputSpec", "ParserError", "PromptCompiler", "RetryPolicy",
    "RuntimeSettings", "SPEC_VERSION", "STAGE_NAMES", "SUPPORTED_SPEC_VERSIONS",
    "SerializationError", "SpecVersionManager", "TimeoutConfig",
    "UndefinedVariableError", "UnusedVariableError", "ValidationError",
    "VariableDef", "VersionError", "WorkflowSpecification",
    "WorkflowSpecificationValidator", "export_schema", "pretty_print",
    "to_binary", "to_json", "to_yaml",
]
