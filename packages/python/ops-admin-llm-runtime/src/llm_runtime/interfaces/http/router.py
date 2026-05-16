from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from identity_access.interfaces.http import dependencies as auth
from llm_runtime.application import services
from llm_runtime.interfaces.http.dtos import (
    LLMConfigRequest,
    LLMModelRequest,
    OpenAIChatCompletionRequest,
    LLMProviderRequest,
    LLMRoutingPolicyRequest,
    LLMTaskRequest,
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
