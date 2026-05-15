from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from identity_access.interfaces.http import dependencies as auth
from llm_runtime.application import ai_applications
from llm_runtime.application import services
from llm_runtime.interfaces.http.dtos import (
    AIApplicationRequest,
    AIApplicationRunRequest,
    LLMConfigRequest,
    LLMModelRequest,
    OpenAIChatCompletionRequest,
    LLMProviderRequest,
    LLMRoutingPolicyRequest,
    LLMTaskRequest,
    TenantAIQuotaRequest,
)
from system.interfaces.http import ok


router = APIRouter()


@router.get("/llm-config", dependencies=[Depends(auth.require_permission("llm_config:access"))])
def llm_config() -> dict[str, Any]:
    return ok(services.get_llm_config())


@router.put("/llm-config", dependencies=[Depends(auth.require_permission("llm_config:update"))])
def update_llm_config(payload: LLMConfigRequest) -> dict[str, Any]:
    return ok(services.save_llm_config(payload.model_dump()))


@router.get("/llm/providers", dependencies=[Depends(auth.require_permission("llm_config:access"))])
def llm_providers() -> dict[str, Any]:
    return ok(services.list_providers())


@router.post("/llm/providers", dependencies=[Depends(auth.require_permission("llm:providers:save"))])
def save_llm_provider(payload: LLMProviderRequest) -> dict[str, Any]:
    return ok(services.save_provider(payload.model_dump()))


@router.put("/llm/providers/{provider_key}", dependencies=[Depends(auth.require_permission("llm:providers:save"))])
def update_llm_provider(provider_key: str, payload: LLMProviderRequest) -> dict[str, Any]:
    data = payload.model_dump()
    data["provider_key"] = provider_key
    return ok(services.save_provider(data))


@router.get("/llm/models", dependencies=[Depends(auth.require_permission("llm_config:access"))])
def llm_models() -> dict[str, Any]:
    return ok(services.list_models())


@router.post("/llm/models", dependencies=[Depends(auth.require_permission("llm:models:save"))])
def save_llm_model(payload: LLMModelRequest) -> dict[str, Any]:
    return ok(services.save_model(payload.model_dump()))


@router.put("/llm/models/{model_key}", dependencies=[Depends(auth.require_permission("llm:models:save"))])
def update_llm_model(model_key: str, payload: LLMModelRequest) -> dict[str, Any]:
    data = payload.model_dump()
    data["model_key"] = model_key
    return ok(services.save_model(data))


@router.get("/llm/tasks", dependencies=[Depends(auth.require_permission("llm_config:access"))])
def llm_tasks() -> dict[str, Any]:
    return ok(services.list_tasks())


@router.post("/llm/tasks/register", dependencies=[Depends(auth.require_permission("llm:tasks:register"))])
def register_llm_task(payload: LLMTaskRequest) -> dict[str, Any]:
    return ok(services.register_task(payload.model_dump()))


@router.get("/llm/routing-policies", dependencies=[Depends(auth.require_permission("llm_config:access"))])
def llm_routing_policies() -> dict[str, Any]:
    return ok(services.list_routing_policies())


@router.post("/llm/routing-policies", dependencies=[Depends(auth.require_permission("llm:routing_policies:save"))])
def save_llm_routing_policy(payload: LLMRoutingPolicyRequest) -> dict[str, Any]:
    return ok(services.save_routing_policy(payload.model_dump()))


@router.put("/llm/routing-policies/{route_key}", dependencies=[Depends(auth.require_permission("llm:routing_policies:save"))])
def update_llm_routing_policy(route_key: str, payload: LLMRoutingPolicyRequest) -> dict[str, Any]:
    data = payload.model_dump()
    data["route_key"] = route_key
    return ok(services.save_routing_policy(data))


@router.get("/llm/call-logs", dependencies=[Depends(auth.require_permission("llm_debug:access"))])
def llm_call_logs(limit: int = 50) -> dict[str, Any]:
    return ok(services.list_call_logs(limit=limit))


@router.get("/ai-studio/overview", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def ai_studio_overview() -> dict[str, Any]:
    return ok(ai_applications.studio_overview())


@router.get("/ai-studio/items", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def ai_studio_items() -> dict[str, Any]:
    return ok(ai_applications.list_ai_applications())


@router.get("/ai-studio/traces", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def ai_studio_traces(limit: int = 50) -> dict[str, Any]:
    return ok(ai_applications.list_prompt_runtime_traces(limit=limit))


@router.get("/llm/ai-applications", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def llm_ai_applications() -> dict[str, Any]:
    return ok(ai_applications.list_ai_applications())


@router.get("/llm/ai-applications/{app_key}", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def llm_ai_application(app_key: str) -> dict[str, Any]:
    return ok(ai_applications.get_ai_application(app_key))


@router.get("/ai-studio/applications/{app_key}/run-logs", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def llm_ai_application_run_logs(app_key: str, limit: int = 50) -> dict[str, Any]:
    return ok(ai_applications.list_ai_application_run_logs(app_key, limit=limit))


@router.post("/llm/ai-applications", dependencies=[Depends(auth.require_permission("ai_applications:manage"))])
def save_llm_ai_application(payload: AIApplicationRequest) -> dict[str, Any]:
    return ok(ai_applications.save_ai_application(payload.model_dump()))


@router.put("/llm/ai-applications/{app_key}", dependencies=[Depends(auth.require_permission("ai_applications:manage"))])
def update_llm_ai_application(app_key: str, payload: AIApplicationRequest) -> dict[str, Any]:
    data = payload.model_dump()
    data["app_key"] = app_key
    return ok(ai_applications.save_ai_application(data))


@router.post("/llm/ai-applications/{app_key}/publish", dependencies=[Depends(auth.require_permission("ai_applications:publish"))])
def publish_llm_ai_application(app_key: str) -> dict[str, Any]:
    return ok(ai_applications.publish_ai_application(app_key))


@router.post("/llm/ai-applications/{app_key}/run-draft", dependencies=[Depends(auth.require_permission("ai_applications:run"))])
def run_llm_ai_application_draft(app_key: str, payload: AIApplicationRunRequest) -> dict[str, Any]:
    return ok(ai_applications.run_draft_application(app_key, payload.model_dump()))


@router.post("/llm/ai-applications/{app_key}/run-draft/stream", dependencies=[Depends(auth.require_permission("ai_applications:run"))])
def stream_llm_ai_application_draft(app_key: str, payload: AIApplicationRunRequest) -> StreamingResponse:
    return StreamingResponse(
        ai_applications.stream_draft_application(app_key, payload.model_dump()),
        media_type="text/event-stream",
    )


@router.post("/runtime/apps/{app_key}/run", dependencies=[Depends(auth.require_business_api_key_or_permission("ai_applications:run"))])
def run_published_ai_application(app_key: str, payload: AIApplicationRunRequest) -> dict[str, Any]:
    return ai_applications.run_published_application(app_key, payload.model_dump())


@router.get("/llm/prompt-runtime/traces", dependencies=[Depends(auth.require_permission("ai_runtime:trace:read"))])
def llm_prompt_runtime_traces(limit: int = 50) -> dict[str, Any]:
    return ok(ai_applications.list_prompt_runtime_traces(limit=limit))


@router.get("/llm/prompt-runtime/traces/{trace_id}", dependencies=[Depends(auth.require_permission("ai_runtime:trace:read"))])
def llm_prompt_runtime_trace(trace_id: str) -> dict[str, Any]:
    return ok(ai_applications.get_prompt_runtime_trace(trace_id))


@router.get("/llm/tenant-ai-quota", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def llm_tenant_ai_quota() -> dict[str, Any]:
    return ok(ai_applications.get_tenant_ai_quota())


@router.get("/llm/admin/tenants/{tenant_id}/ai-quota", dependencies=[Depends(auth.require_platform_admin)])
def llm_admin_tenant_ai_quota(tenant_id: int) -> dict[str, Any]:
    return ok(ai_applications.get_admin_tenant_ai_quota(tenant_id))


@router.put("/llm/admin/tenants/{tenant_id}/ai-quota", dependencies=[Depends(auth.require_platform_admin)])
def save_llm_tenant_ai_quota(tenant_id: int, payload: TenantAIQuotaRequest) -> dict[str, Any]:
    return ok(ai_applications.save_tenant_ai_quota(tenant_id, payload.model_dump()))


@router.get("/llm/openai/v1/models", dependencies=[Depends(auth.require_auth)])
def openai_models() -> dict[str, Any]:
    return services.list_openai_models()


@router.post("/llm/openai/v1/chat/completions", dependencies=[Depends(auth.require_business_api_key_or_permission("llm_debug:send"))])
def openai_chat_completions(payload: OpenAIChatCompletionRequest) -> dict[str, Any]:
    data = payload.model_dump()
    if data.get("stream", False):
        return StreamingResponse(
            iter(services.create_openai_chat_completion_stream(data)),
            media_type="text/event-stream",
        )
    return services.create_openai_chat_completion(data)
