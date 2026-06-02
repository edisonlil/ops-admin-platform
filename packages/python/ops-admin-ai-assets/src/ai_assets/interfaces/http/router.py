from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from ai_assets.application import services
from ai_assets.interfaces.http.dtos import (
    PromptPolishRequest,
    PromptAssetRequest,
    PromptVersionRequest,
    SkillAssetRequest,
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
    tags: list[str] = Query(default_factory=list),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:view")),
) -> dict[str, Any]:
    return ok(
        services.list_prompt_assets(
            page=page,
            page_size=page_size,
            keyword=keyword,
            status_filter=status_filter,
            tags=tags,
            sort_by=sort_by,
            sort_dir=sort_dir,
            current_user=current_user,
        )
    )


@router.post("/prompts")
def create_prompt_asset(
    payload: PromptAssetRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.save_prompt_asset(payload.model_dump(), current_user))


@router.get("/prompts/published")
def published_prompt_assets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    keyword: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:view")),
) -> dict[str, Any]:
    return ok(
        services.list_published_prompt_assets(
            page=page,
            page_size=page_size,
            keyword=keyword,
            sort_by=sort_by,
            sort_dir=sort_dir,
            current_user=current_user,
        )
    )


@router.get("/prompts/published/{prompt_key}")
def published_prompt_asset(
    prompt_key: str,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:view")),
) -> dict[str, Any]:
    return ok(services.get_published_prompt_asset(prompt_key, current_user))


@router.post("/prompts/assist/polish")
def polish_prompt(
    payload: PromptPolishRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.polish_prompt(payload.model_dump(), current_user))


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


@router.get("/skills")
def skill_assets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = "",
    status_filter: str = Query(default="", alias="status"),
    tags: list[str] = Query(default_factory=list),
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:view")),
) -> dict[str, Any]:
    return ok(
        services.list_skill_assets(
            page=page,
            page_size=page_size,
            keyword=keyword,
            status_filter=status_filter,
            tags=tags,
            sort_by=sort_by,
            sort_dir=sort_dir,
            current_user=current_user,
        )
    )


@router.post("/skills")
def create_skill_asset(
    payload: SkillAssetRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:manage")),
) -> dict[str, Any]:
    return ok(services.save_skill_asset(payload.model_dump(), current_user))


@router.post("/skills/upload")
async def upload_skill_asset(
    package: UploadFile = File(...),
    version: str = Form(default="1.0.0"),
    skill_key: str = Form(default=""),
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:manage")),
) -> dict[str, Any]:
    return ok(
        services.upload_skill_asset(
            {
                "version": version,
                "skill_key": skill_key,
                "filename": package.filename or "",
                "package_bytes": await package.read(),
            },
            current_user,
        )
    )


@router.get("/skills/published")
def published_skill_assets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    keyword: str = "",
    sort_by: str | None = Query(default=None),
    sort_dir: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:view")),
) -> dict[str, Any]:
    return ok(
        services.list_published_skill_assets(
            page=page,
            page_size=page_size,
            keyword=keyword,
            sort_by=sort_by,
            sort_dir=sort_dir,
            current_user=current_user,
        )
    )


@router.get("/skills/published/{skill_key}")
def published_skill_asset(
    skill_key: str,
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:view")),
) -> dict[str, Any]:
    return ok(services.get_published_skill_asset(skill_key, current_user))


@router.get("/skills/{skill_id}")
def skill_asset(
    skill_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:view")),
) -> dict[str, Any]:
    return ok(services.get_skill_asset(skill_id, current_user))


@router.put("/skills/{skill_id}")
def update_skill_asset(
    skill_id: int,
    payload: SkillAssetRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:manage")),
) -> dict[str, Any]:
    return ok(services.save_skill_asset(payload.model_dump(), current_user, skill_id=skill_id))


@router.delete("/skills/{skill_id}")
def delete_skill_asset(
    skill_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:manage")),
) -> dict[str, Any]:
    return ok(services.delete_skill_asset(skill_id, current_user))


@router.get("/skills/{skill_id}/versions")
def skill_versions(
    skill_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:view")),
) -> dict[str, Any]:
    return ok(services.list_skill_versions(skill_id, current_user))


@router.post("/skills/{skill_id}/versions")
async def create_skill_version(
    skill_id: int,
    package: UploadFile = File(...),
    version: str = Form(...),
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:manage")),
) -> dict[str, Any]:
    return ok(
        services.save_skill_version(
            skill_id,
            {
                "version": version,
                "filename": package.filename or "",
                "package_bytes": await package.read(),
            },
            current_user,
        )
    )


@router.put("/skills/{skill_id}/versions/{version_id}")
async def update_skill_version(
    skill_id: int,
    version_id: int,
    package: UploadFile = File(...),
    version: str = Form(...),
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:manage")),
) -> dict[str, Any]:
    return ok(
        services.save_skill_version(
            skill_id,
            {
                "version": version,
                "filename": package.filename or "",
                "package_bytes": await package.read(),
            },
            current_user,
            version_id=version_id,
        )
    )


@router.post("/skills/{skill_id}/versions/{version_id}/publish")
def publish_skill_version(
    skill_id: int,
    version_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:manage")),
) -> dict[str, Any]:
    return ok(services.publish_skill_version(skill_id, version_id, current_user))


@router.post("/skills/{skill_id}/versions/{version_id}/deprecate")
def deprecate_skill_version(
    skill_id: int,
    version_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("skill:assets:manage")),
) -> dict[str, Any]:
    return ok(services.deprecate_skill_version(skill_id, version_id, current_user))
