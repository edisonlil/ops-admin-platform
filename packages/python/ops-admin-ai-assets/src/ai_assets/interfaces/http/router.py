from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from ai_assets.application import services
from ai_assets.interfaces.http.dtos import (
    PromptAssetRequest,
    PromptVersionRequest,
)
from identity_access.interfaces.http import dependencies as auth
from system.interfaces.http import ok


router = APIRouter()


@router.get("/prompts")
def prompt_assets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = "",
    status_filter: str = Query(default="", alias="status"),
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:view")),
) -> dict[str, Any]:
    return ok(
        services.list_prompt_assets(
            page=page,
            page_size=page_size,
            keyword=keyword,
            status_filter=status_filter,
            current_user=current_user,
        )
    )


@router.post("/prompts")
def create_prompt_asset(
    payload: PromptAssetRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.save_prompt_asset(payload.model_dump(), current_user))


@router.get("/prompts/{prompt_id}")
def prompt_asset(
    prompt_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:view")),
) -> dict[str, Any]:
    return ok(services.get_prompt_asset(prompt_id, current_user))


@router.post("/prompts/{prompt_id}/copy")
def copy_prompt_asset(
    prompt_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.copy_prompt_asset(prompt_id, current_user))


@router.put("/prompts/{prompt_id}")
def update_prompt_asset(
    prompt_id: int,
    payload: PromptAssetRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.save_prompt_asset(payload.model_dump(), current_user, prompt_id=prompt_id))


@router.delete("/prompts/{prompt_id}")
def delete_prompt_asset(
    prompt_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.delete_prompt_asset(prompt_id, current_user))


@router.get("/prompts/{prompt_id}/versions")
def prompt_versions(
    prompt_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:view")),
) -> dict[str, Any]:
    return ok(services.list_prompt_versions(prompt_id, current_user))


@router.post("/prompts/{prompt_id}/versions")
def create_prompt_version(
    prompt_id: int,
    payload: PromptVersionRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.save_prompt_version(prompt_id, payload.model_dump(), current_user))


@router.put("/prompts/{prompt_id}/versions/{version_id}")
def update_prompt_version(
    prompt_id: int,
    version_id: int,
    payload: PromptVersionRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.save_prompt_version(prompt_id, payload.model_dump(), current_user, version_id=version_id))


@router.post("/prompts/{prompt_id}/versions/{version_id}/publish")
def publish_prompt_version(
    prompt_id: int,
    version_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.publish_prompt_version(prompt_id, version_id, current_user))


@router.post("/prompts/{prompt_id}/versions/{version_id}/deprecate")
def deprecate_prompt_version(
    prompt_id: int,
    version_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.deprecate_prompt_version(prompt_id, version_id, current_user))
