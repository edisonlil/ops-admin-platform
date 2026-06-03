"""Shared AI runtime primitives.

This framework package intentionally contains no HTTP, database, tenant, RBAC,
or product-domain ownership. Bounded contexts provide adapters around it.
"""

from ai_runtime_core.workflow_runtime import WorkflowLLMRequest
from ai_runtime_core.workflow_runtime import WorkflowLLMResult
from ai_runtime_core.workflow_runtime import WorkflowFileExtractRequest
from ai_runtime_core.workflow_runtime import WorkflowFileExtractResult
from ai_runtime_core.workflow_runtime import WorkflowRunResult
from ai_runtime_core.workflow_runtime import WorkflowRuntimeError
from ai_runtime_core.workflow_runtime import execute_workflow
from ai_runtime_core.workflow_runtime import iter_workflow_events


__all__ = [
    "WorkflowLLMRequest",
    "WorkflowLLMResult",
    "WorkflowFileExtractRequest",
    "WorkflowFileExtractResult",
    "WorkflowRunResult",
    "WorkflowRuntimeError",
    "execute_workflow",
    "iter_workflow_events",
]
