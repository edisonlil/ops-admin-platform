from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException

from ai_applications.application import services as ai_application_services
from ai_capabilities.infrastructure.persistence import repositories
from ai_capabilities.infrastructure.persistence.bootstrap import require_ai_capabilities_schema
from identity_access.application import tenant_service
from llm_runtime.application import services as llm_services
from system.application.database import connect
from system.application.tenancy import reset_tenant_scope, set_tenant_scope
from system.domain.tenancy import TenantScope

from llm_runtime.application.services import require_database


def list_ai_capabilities() -> dict[str, Any]:
    return read_list(lambda conn: repositories.list_ai_capabilities(conn))


def list_platform_ai_capabilities() -> dict[str, Any]:
    return read_list(lambda conn: repositories.list_platform_ai_capabilities(conn))


def list_capability_model_options() -> dict[str, Any]:
    items = llm_services.list_models()
    return {"items": items, "pagination": {"page": 1, "page_size": len(items), "total": len(items)}}


def list_capability_model_options_for_tenant(tenant_id: int) -> dict[str, Any]:
    with tenant_scope_for_platform_preview(tenant_id):
        models = llm_services.list_models()
        policies = llm_services.list_routing_policies()
    return {
        "models": models.get("items", []),
        "routing_policies": policies.get("items", []),
    }


def get_ai_capability(capability_key: str) -> dict[str, Any]:
    capability = read_one(lambda conn: repositories.get_ai_capability(conn, capability_key))
    if not capability:
        raise HTTPException(status_code=404, detail="AI capability not found")
    return capability


def get_platform_ai_capability(capability_key: str) -> dict[str, Any]:
    capability = read_one(lambda conn: repositories.get_platform_ai_capability(conn, capability_key))
    if not capability:
        raise HTTPException(status_code=404, detail="Platform AI capability not found")
    return capability


def list_ai_capability_run_logs(capability_key: str, limit: int = 50) -> dict[str, Any]:
    capability = get_ai_capability(capability_key)
    return ai_application_services.list_ai_capability_run_logs(capability["capability_key"], limit=limit)


def list_platform_ai_capability_run_logs(capability_key: str, limit: int = 50) -> dict[str, Any]:
    capability = get_platform_ai_capability(capability_key)
    return ai_application_services.list_platform_ai_capability_run_logs(capability["capability_key"], limit=limit)


def save_ai_capability(payload: dict[str, Any]) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            require_ai_capabilities_schema(conn)
            existing = repositories.get_tenant_ai_capability(conn, str(payload.get("capability_key") or ""))
            if not existing:
                enforce_capability_quota(conn)
            normalize_capability_payload(payload, allow_platform_scope=False)
            return repositories.upsert_ai_capability(conn, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (sqlite3.Error, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def save_platform_ai_capability(payload: dict[str, Any]) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            require_ai_capabilities_schema(conn)
            payload["scope"] = "platform"
            normalize_capability_payload(payload, allow_platform_scope=True)
            return repositories.upsert_ai_capability(conn, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (sqlite3.Error, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def execute_ai_capability(capability_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    capability = get_ai_capability(capability_key)
    if not capability.get("enabled", True):
        raise HTTPException(status_code=409, detail="AI capability is disabled")
    if capability.get("binding_type") not in {"prompt_runtime", "workflow_runtime"}:
        raise HTTPException(status_code=422, detail="Only prompt_runtime and workflow_runtime capabilities are supported")
    validate_executable_capability(capability)
    run_payload = payload if "variables" in payload else {"variables": payload}
    app = capability_runtime_app(capability)
    return ai_application_services.execute_application(
        app,
        run_payload,
        caller_type="ai_capability",
        caller_key=capability["capability_key"],
        require_published=True,
    )


def preview_platform_ai_capability(capability_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = int(payload.get("tenant_id") or 0)
    if tenant_id <= 0:
        raise HTTPException(status_code=422, detail="tenant_id is required")
    capability = get_platform_ai_capability(capability_key)
    if not capability.get("enabled", True):
        raise HTTPException(status_code=409, detail="AI capability is disabled")
    if capability.get("binding_type") not in {"prompt_runtime", "workflow_runtime"}:
        raise HTTPException(status_code=422, detail="Only prompt_runtime and workflow_runtime capabilities are supported")
    validate_executable_capability(capability, model_override=str(payload.get("model") or ""))
    run_payload = {key: value for key, value in payload.items() if key != "tenant_id"}
    if "variables" not in run_payload:
        run_payload = {"variables": run_payload}
    app = capability_runtime_app(capability)
    app["tenant_id"] = tenant_id
    with tenant_scope_for_platform_preview(tenant_id):
        return ai_application_services.execute_application(
            app,
            run_payload,
            caller_type="ai_capability",
            caller_key=capability["capability_key"],
            require_published=True,
        )


def stream_ai_capability(capability_key: str, payload: dict[str, Any]) -> Any:
    capability = get_ai_capability(capability_key)
    if not capability.get("enabled", True):
        raise HTTPException(status_code=409, detail="AI capability is disabled")
    if capability.get("binding_type") not in {"prompt_runtime", "workflow_runtime"}:
        raise HTTPException(status_code=422, detail="Only prompt_runtime and workflow_runtime capabilities are supported")
    validate_executable_capability(capability)
    run_payload = payload if "variables" in payload else {"variables": payload}
    app = capability_runtime_app(capability)
    if app["app_type"] == "workflow":
        return ai_application_services.stream_workflow_application(
            app,
            run_payload,
            caller_type="ai_capability",
            require_published=True,
        )
    prepared = ai_application_services.prepare_single_turn_run(app, run_payload, require_published=True)
    return ai_application_services.stream_single_turn_application(
        prepared,
        caller_type="ai_capability",
        caller_key=capability["capability_key"],
    )


def capability_runtime_app(capability: dict[str, Any]) -> dict[str, Any]:
    binding_type = str(capability.get("binding_type") or "prompt_runtime")
    return {
        "tenant_id": capability.get("tenant_id"),
        "app_key": capability["capability_key"],
        "name": capability.get("name") or capability["capability_key"],
        "app_type": "workflow" if binding_type == "workflow_runtime" else "single_turn_generation",
        "status": "published",
        "lock_version": capability.get("lock_version") or 0,
        "system_prompt": capability.get("system_prompt") or "",
        "developer_prompt": capability.get("developer_prompt") or "",
        "user_prompt_template": capability.get("user_prompt_template") or "",
        "variables_schema": capability.get("input_schema") or {},
        "output_schema": capability.get("output_schema") or {},
        "model_preferences": capability.get("model_preferences") or {},
        "runtime_config": capability.get("runtime_config") or {},
    }


def validate_executable_capability(capability: dict[str, Any], *, model_override: str = "") -> None:
    if capability.get("binding_type") == "workflow_runtime":
        runtime_config = capability.get("runtime_config") if isinstance(capability.get("runtime_config"), dict) else {}
        if not isinstance(runtime_config.get("workflow"), dict):
            raise HTTPException(status_code=422, detail="runtime_config.workflow is required before execute")
        return
    if not str(capability.get("user_prompt_template") or "").strip():
        raise HTTPException(status_code=422, detail="user_prompt_template is required before execute")
    model_preferences = capability.get("model_preferences") if isinstance(capability.get("model_preferences"), dict) else {}
    if not str(model_override or model_preferences.get("model") or model_preferences.get("route_key") or "").strip():
        raise HTTPException(status_code=422, detail="model_preferences.model or model_preferences.route_key is required before execute")


def normalize_capability_payload(payload: dict[str, Any], *, allow_platform_scope: bool = False) -> None:
    payload["scope"] = str(payload.get("scope") or "tenant").strip() or "tenant"
    if payload["scope"] not in {"tenant", "platform"}:
        raise ValueError("scope must be tenant or platform")
    if payload["scope"] == "platform" and not allow_platform_scope:
        raise ValueError("tenant AI Studio can only create tenant scoped capabilities")
    if payload["scope"] == "tenant" and allow_platform_scope:
        raise ValueError("platform AI capability management requires platform scope")
    binding_type = str(payload.get("binding_type") or "prompt_runtime").strip()
    if binding_type not in {"prompt_runtime", "workflow_runtime"}:
        raise ValueError("binding_type must be prompt_runtime or workflow_runtime")
    payload["binding_type"] = binding_type
    payload["binding_key"] = repositories.normalize_key(payload.get("binding_key") or payload.get("capability_key"))
    model_preferences = payload.get("model_preferences") if isinstance(payload.get("model_preferences"), dict) else {}
    payload["model_preferences"] = model_preferences
    payload["input_schema"] = payload.get("input_schema") or {"type": "object", "required": ["question"]}
    payload["output_schema"] = payload.get("output_schema") or {}
    payload["runtime_config"] = payload.get("runtime_config") or {}
    payload["enabled"] = bool(payload.get("enabled", True))
    payload.setdefault("call_method", "aiService.execute")


def enforce_capability_quota(conn: Any) -> None:
    quota = ai_application_services.get_tenant_ai_quota()
    if not quota.get("enabled", True):
        raise ValueError("AI Studio is disabled for this tenant")
    usage = quota.get("usage") if isinstance(quota.get("usage"), dict) else {}
    if int(usage.get("capabilities") or 0) >= int(quota.get("max_capabilities") or 0):
        raise ValueError("tenant AI capability quota exceeded")


class tenant_scope_for_platform_preview:
    def __init__(self, tenant_id: int) -> None:
        self.tenant_id = tenant_id
        self._token: Any = None

    def __enter__(self) -> None:
        tenant = tenant_service.get_business_tenant_by_id(self.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="tenant not found")
        if str(tenant.get("status") or "active") != "active":
            raise HTTPException(status_code=409, detail="tenant is not active")
        self._token = set_tenant_scope(
            TenantScope(
                tenant_id=int(tenant["id"]),
                tenant_key=str(tenant.get("tenant_key") or tenant.get("key") or ""),
                tenant_name=str(tenant.get("name") or ""),
                is_platform_admin=True,
                source="platform_preview",
            )
        )

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._token is not None:
            reset_tenant_scope(self._token)


def read_list(loader: Any) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            require_ai_capabilities_schema(conn)
            items = loader(conn)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    return {"items": items, "pagination": {"page": 1, "page_size": len(items), "total": len(items)}}


def read_one(loader: Any) -> dict[str, Any] | None:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            require_ai_capabilities_schema(conn)
            return loader(conn)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
