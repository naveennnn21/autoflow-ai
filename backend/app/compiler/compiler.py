"""AutoFlow AI - Prompt compiler facade (generated from metadata).

Public entry point: transforms a WorkflowPlan into a versioned
Workflow Specification v1 consumable by the Workflow Runtime.

The compiler ONLY compiles. It never executes workflows and never calls
connectors.
"""

from typing import Any, Dict, List, Optional

from app.compiler.events import emit_compile_completed, emit_compile_failed
from app.compiler.metrics import CompilationMetrics
from app.compiler.models import CompileOptions, CompileReport
from app.compiler.pipeline import CompilationPipeline
from app.compiler.serializer import (
    export_schema, to_binary, to_json, to_yaml,
)
from app.compiler.versioning import SpecVersionManager
from app.compiler.workflow_spec import (
    SPEC_VERSION, WorkflowSpecification,
)


class PromptCompiler:
    """Compiles WorkflowPlans into Workflow Specifications."""

    def __init__(self, options: Optional[CompileOptions] = None,
                 connector_names: Optional[List[str]] = None,
                 permissions: Optional[Dict[str, List[str]]] = None,
                 pipeline: Optional[CompilationPipeline] = None):
        self.options = options or CompileOptions()
        self.pipeline = pipeline or CompilationPipeline(
            options=self.options,
            connector_names=connector_names,
            permissions=permissions,
        )
        self.metrics = CompilationMetrics()
        self.version_manager = SpecVersionManager()

    def compile(self, plan: Any,
                request_id: Optional[str] = None
                ) -> WorkflowSpecification:
        """Compile a WorkflowPlan into a Workflow Specification."""
        spec, report = self.pipeline.run(plan, request_id=request_id)
        if self.options.collect_metrics:
            self.metrics.record_compile(
                len(spec.nodes), len(spec.edges), ok=True,
                optimization_stats=report.optimization_stats,
            )
        return spec

    def compile_with_report(self, plan: Any,
                            request_id: Optional[str] = None
                            ) -> tuple:
        """Compile and return ``(spec, report)``."""
        spec, report = self.pipeline.run(plan, request_id=request_id)
        if self.options.collect_metrics:
            self.metrics.record_compile(
                len(spec.nodes), len(spec.edges), ok=True,
                optimization_stats=report.optimization_stats,
            )
        return spec, report

    # -- serialization helpers ------------------------------------------

    def compile_to_dict(self, plan: Any) -> Dict[str, Any]:
        return self.compile(plan).to_dict()

    def compile_to_json(self, plan: Any, pretty: bool = False) -> str:
        return to_json(self.compile(plan), pretty=pretty)

    def compile_to_yaml(self, plan: Any) -> str:
        return to_yaml(self.compile(plan))

    def compile_to_binary(self, plan: Any) -> str:
        return to_binary(self.compile(plan))

    # -- spec utilities -------------------------------------------------

    @staticmethod
    def load_spec(data: Dict[str, Any]) -> WorkflowSpecification:
        return WorkflowSpecification.from_dict(data)

    def spec_schema(self) -> Dict[str, Any]:
        return export_schema()

    def version_report(self) -> Dict[str, Any]:
        return {
            "current_version": self.version_manager.current_version(),
            "supported_versions": list(self.version_manager.supported),
        }

    def metrics_dict(self) -> Dict[str, Any]:
        return self.metrics.to_dict()
