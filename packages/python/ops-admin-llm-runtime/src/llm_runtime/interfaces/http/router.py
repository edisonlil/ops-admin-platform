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


@router.get("/llm-config")
def llm_config(current_user: dict[str, Any] = Depends(auth.require_permission("llm_config:access"))) -> dict[str, Any]:
    return ok(services.get_llm_config(current_user=current_user))


@router.put("/llm-config")
def update_llm_config(
    payload: LLMConfigRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("llm_config:update")),
) -> dict[str, Any]:
    return ok(services.save_llm_config(payload.model_dump(), current_user=current_user))


@router.get("/llm/providers")
def llm_providers(current_user: dict[str, Any] = Depends(auth.require_permission("llm_config:access"))) -> dict[str, Any]:
    return ok(services.list_providers(current_user=current_user))


@router.post("/llm/providers")
def save_llm_provider(
    payload: LLMProviderRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("llm:providers:save")),
) -> dict[str, Any]:
    return ok(services.save_provider(payload.model_dump(), current_user=current_user))


@router.put("/llm/providers/{provider_key}")
def update_llm_provider(
    provider_key: str,
    payload: LLMProviderRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("llm:providers:save")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["provider_key"] = provider_key
    return ok(services.save_provider(data, current_user=current_user))


@router.get("/llm/models")
def llm_models(current_user: dict[str, Any] = Depends(auth.require_permission("llm_config:access"))) -> dict[str, Any]:
    return ok(services.list_models(current_user=current_user))


@router.post("/llm/models")
def save_llm_model(
    payload: LLMModelRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("llm:models:save")),
) -> dict[str, Any]:
    return ok(services.save_model(payload.model_dump(), current_user=current_user))


@router.put("/llm/models/{model_key}")
def update_llm_model(
    model_key: str,
    payload: LLMModelRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("llm:models:save")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["model_key"] = model_key
    return ok(services.save_model(data, current_user=current_user))


@router.get("/llm/tasks")
def llm_tasks(current_user: dict[str, Any] = Depends(auth.require_permission("llm_config:access"))) -> dict[str, Any]:
    return ok(services.list_tasks(current_user=current_user))


@router.post("/llm/tasks/register")
def register_llm_task(
    payload: LLMTaskRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("llm:tasks:register")),
) -> dict[str, Any]:
    return ok(services.register_task(payload.model_dump(), current_user=current_user))


@router.get("/llm/routing-policies")
def llm_routing_policies(current_user: dict[str, Any] = Depends(auth.require_permission("llm_config:access"))) -> dict[str, Any]:
    return ok(services.list_routing_policies(current_user=current_user))


@router.post("/llm/routing-policies")
def save_llm_routing_policy(
    payload: LLMRoutingPolicyRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("llm:routing_policies:save")),
) -> dict[str, Any]:
    return ok(services.save_routing_policy(payload.model_dump(), current_user=current_user))


@router.put("/llm/routing-policies/{route_key}")
def update_llm_routing_policy(
    route_key: str,
    payload: LLMRoutingPolicyRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("llm:routing_policies:save")),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["route_key"] = route_key
    return ok(services.save_routing_policy(data, current_user=current_user))


@router.get("/llm/call-logs")
def llm_call_logs(
    limit: int = 50,
    current_user: dict[str, Any] = Depends(auth.require_permission("llm_debug:access")),
) -> dict[str, Any]:
    return ok(services.list_call_logs(limit=limit, current_user=current_user))


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
