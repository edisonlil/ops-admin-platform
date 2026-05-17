from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ai_capabilities.application import services
from ai_capabilities.interfaces.http.dtos import AICapabilityRequest, AICapabilityRunRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import ok


router = APIRouter()


@router.get("/ai-capabilities", dependencies=[Depends(auth.require_permission("ai_capabilities:read"))])
def ai_capabilities() -> dict[str, Any]:
    return ok(services.list_ai_capabilities())


@router.get("/admin/ai-capabilities", dependencies=[Depends(auth.require_platform_permission("ai_capabilities:platform_manage"))])
def platform_ai_capabilities() -> dict[str, Any]:
    return ok(services.list_platform_ai_capabilities())


@router.get("/ai-capabilities/model-options", dependencies=[Depends(auth.require_permission("ai_capabilities:manage"))])
def ai_capability_model_options() -> dict[str, Any]:
    return ok(services.list_capability_model_options())


@router.get("/ai-capabilities/{capability_key}", dependencies=[Depends(auth.require_permission("ai_capabilities:read"))])
def ai_capability(capability_key: str) -> dict[str, Any]:
    return ok(services.get_ai_capability(capability_key))


@router.get("/admin/ai-capabilities/{capability_key}", dependencies=[Depends(auth.require_platform_permission("ai_capabilities:platform_manage"))])
def platform_ai_capability(capability_key: str) -> dict[str, Any]:
    return ok(services.get_platform_ai_capability(capability_key))


@router.get("/ai-studio/capabilities/{capability_key}/run-logs", dependencies=[Depends(auth.require_permission("ai_capabilities:read"))])
def ai_capability_run_logs(capability_key: str, limit: int = 50) -> dict[str, Any]:
    return ok(services.list_ai_capability_run_logs(capability_key, limit=limit))


@router.post("/ai-capabilities", dependencies=[Depends(auth.require_permission("ai_capabilities:manage"))])
def save_ai_capability(payload: AICapabilityRequest) -> dict[str, Any]:
    return ok(services.save_ai_capability(payload.model_dump()))


@router.post("/admin/ai-capabilities", dependencies=[Depends(auth.require_platform_permission("ai_capabilities:platform_manage"))])
def save_platform_ai_capability(payload: AICapabilityRequest) -> dict[str, Any]:
    return ok(services.save_platform_ai_capability(payload.model_dump()))


@router.put("/ai-capabilities/{capability_key}", dependencies=[Depends(auth.require_permission("ai_capabilities:manage"))])
def update_ai_capability(capability_key: str, payload: AICapabilityRequest) -> dict[str, Any]:
    data = payload.model_dump()
    data["capability_key"] = capability_key
    return ok(services.save_ai_capability(data))


@router.put("/admin/ai-capabilities/{capability_key}", dependencies=[Depends(auth.require_platform_permission("ai_capabilities:platform_manage"))])
def update_platform_ai_capability(capability_key: str, payload: AICapabilityRequest) -> dict[str, Any]:
    data = payload.model_dump()
    data["capability_key"] = capability_key
    return ok(services.save_platform_ai_capability(data))


@router.post(
    "/ai-capabilities/{capability_key}/execute",
    dependencies=[Depends(auth.require_business_api_key_or_permission("ai_capabilities:execute"))],
)
def execute_ai_capability(capability_key: str, payload: AICapabilityRunRequest) -> dict[str, Any]:
    return ok(services.execute_ai_capability(capability_key, payload.model_dump()))


@router.post(
    "/ai-capabilities/{capability_key}/execute/stream",
    dependencies=[Depends(auth.require_permission("ai_capabilities:execute"))],
)
def stream_ai_capability(capability_key: str, payload: AICapabilityRunRequest) -> StreamingResponse:
    return StreamingResponse(
        services.stream_ai_capability(capability_key, payload.model_dump()),
        media_type="text/event-stream",
    )
