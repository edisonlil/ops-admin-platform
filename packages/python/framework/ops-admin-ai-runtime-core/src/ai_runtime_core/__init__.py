"""Shared AI runtime primitives.

This framework package intentionally contains no HTTP, database, tenant, RBAC,
or product-domain ownership. Bounded contexts provide adapters around it.
"""

from ai_runtime_core.workflow_runtime import WorkflowLLMRequest
from ai_runtime_core.workflow_runtime import WorkflowLLMResult
from ai_runtime_core.workflow_runtime import WorkflowRunResult
from ai_runtime_core.workflow_runtime import WorkflowRuntimeError
from ai_runtime_core.workflow_runtime import execute_workflow


__all__ = [
    "WorkflowLLMRequest",
    "WorkflowLLMResult",
    "WorkflowRunResult",
    "WorkflowRuntimeError",
    "execute_workflow",
]
