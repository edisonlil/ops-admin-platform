from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from ai_applications.application import services
from ai_applications.interfaces.http.dtos import AIApplicationRequest, AIApplicationRunRequest, TenantAIQuotaRequest
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import ok


router = APIRouter()


@router.get("/ai-studio/overview", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def ai_studio_overview() -> dict[str, Any]:
    return ok(services.studio_overview())


@router.get("/ai-studio/items", dependencies=[Depends(auth.require_permission("ai_applications:read"))])
def ai_studio_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
) -> dict[str, Any]:
    return ok(services.list_ai_applications(page=page, page_size=page_size, keyword=keyword, status=status, sort_by=sort_by, sort_dir=sort_dir))


@router.get("/ai-studio/traces", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def ai_studio_traces(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
) -> dict[str, Any]:
    return ok(services.list_prompt_runtime_traces(page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir))


@router.get("/ai-applications", dependencies=[Depends(auth.require_permission("ai_applications:read"))])
def ai_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
) -> dict[str, Any]:
    return ok(services.list_ai_applications(page=page, page_size=page_size, keyword=keyword, status=status, sort_by=sort_by, sort_dir=sort_dir))


@router.get("/ai-applications/{app_key}", dependencies=[Depends(auth.require_permission("ai_applications:read"))])
def ai_application(app_key: str) -> dict[str, Any]:
    return ok(services.get_ai_application(app_key))


@router.get("/ai-studio/applications/{app_key}/run-logs", dependencies=[Depends(auth.require_permission("ai_applications:read"))])
def ai_application_run_logs(
    app_key: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
) -> dict[str, Any]:
    return ok(services.list_ai_application_run_logs(app_key, page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir))


@router.post("/ai-applications", dependencies=[Depends(auth.require_permission("ai_applications:manage"))])
def save_ai_application(payload: AIApplicationRequest) -> dict[str, Any]:
    return ok(services.save_ai_application(payload.model_dump()))


@router.put("/ai-applications/{app_key}", dependencies=[Depends(auth.require_permission("ai_applications:manage"))])
def update_ai_application(app_key: str, payload: AIApplicationRequest) -> dict[str, Any]:
    data = payload.model_dump()
    data["app_key"] = app_key
    return ok(services.save_ai_application(data))


@router.post("/ai-applications/{app_key}/publish", dependencies=[Depends(auth.require_permission("ai_applications:publish"))])
def publish_ai_application(app_key: str) -> dict[str, Any]:
    return ok(services.publish_ai_application(app_key))


@router.post("/ai-applications/{app_key}/run-draft", dependencies=[Depends(auth.require_permission("ai_applications:run"))])
def run_ai_application_draft(app_key: str, payload: AIApplicationRunRequest) -> dict[str, Any]:
    return ok(services.run_draft_application(app_key, payload.model_dump()))


@router.post("/ai-applications/{app_key}/run-draft/stream", dependencies=[Depends(auth.require_permission("ai_applications:run"))])
def stream_ai_application_draft(app_key: str, payload: AIApplicationRunRequest) -> StreamingResponse:
    return StreamingResponse(
        services.stream_draft_application(app_key, payload.model_dump()),
        media_type="text/event-stream",
    )


@router.post("/runtime/apps/{app_key}/run", dependencies=[Depends(auth.require_business_api_key_or_permission("ai_applications:run"))])
def run_published_ai_application(app_key: str, payload: AIApplicationRunRequest) -> dict[str, Any]:
    return services.run_published_application(app_key, payload.model_dump())


@router.get("/ai-runtime/prompt-runtime/traces", dependencies=[Depends(auth.require_permission("ai_runtime:trace:read"))])
def prompt_runtime_traces(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
) -> dict[str, Any]:
    return ok(services.list_prompt_runtime_traces(page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir))


@router.get("/ai-runtime/prompt-runtime/traces/{trace_id}", dependencies=[Depends(auth.require_permission("ai_runtime:trace:read"))])
def prompt_runtime_trace(trace_id: str) -> dict[str, Any]:
    return ok(services.get_prompt_runtime_trace(trace_id))


@router.get("/tenant-ai-quota", dependencies=[Depends(auth.require_permission("ai_studio:access"))])
def tenant_ai_quota() -> dict[str, Any]:
    return ok(services.get_tenant_ai_quota())


@router.get("/admin/tenants/{tenant_id}/ai-quota", dependencies=[Depends(auth.require_platform_admin)])
def admin_tenant_ai_quota(tenant_id: int) -> dict[str, Any]:
    return ok(services.get_admin_tenant_ai_quota(tenant_id))


@router.put("/admin/tenants/{tenant_id}/ai-quota", dependencies=[Depends(auth.require_platform_admin)])
def save_tenant_ai_quota(tenant_id: int, payload: TenantAIQuotaRequest) -> dict[str, Any]:
    return ok(services.save_tenant_ai_quota(tenant_id, payload.model_dump()))
