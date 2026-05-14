from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import HTTPException, status

from ai_assets.domain.exceptions import (
    AIAssetsError,
    PromptAssetNameConflict,
    PromptAssetNotFound,
    PromptVersionImmutable,
    PromptVersionNotFound,
    PromptVersionStateConflict,
)
from ai_assets.domain.models import (
    PROMPT_ASSET_STATUS_ARCHIVED,
    PROMPT_VERSION_STATUS_DEPRECATED,
    PROMPT_VERSION_STATUS_PUBLISHED,
    PromptAsset,
)
from ai_assets.infrastructure.persistence import repositories


def list_prompt_assets(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    keyword: str = "",
    status_filter: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repositories.list_prompt_assets(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            keyword=keyword.strip(),
            status=status_filter.strip(),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def get_prompt_asset(prompt_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_prompt_asset(prompt_id, current_user)
    versions = repositories.list_prompt_versions(tenant_id=item.tenant_id, prompt_id=prompt_id)
    return {"item": item.to_dict(), "versions": [version.to_dict() for version in versions]}


def save_prompt_asset(payload: dict[str, Any], current_user: dict[str, Any], prompt_id: int | None = None) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        existing = repositories.get_prompt_asset(tenant_id=tenant_id, prompt_id=prompt_id) if prompt_id else None
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if prompt_id and not existing:
        raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    prompt_key = existing.prompt_key if existing else str(payload.get("prompt_key") or "").strip()
    if not prompt_key:
        prompt_key = generate_prompt_key(tenant_id=tenant_id, name=payload.get("name"))
    name = normalize_required(payload.get("name"), "name")
    if repositories.prompt_name_exists(tenant_id=tenant_id, name=name, exclude_prompt_id=prompt_id):
        raise domain_http_error(PromptAssetNameConflict("prompt title already exists"))
    data = {
        "prompt_key": prompt_key,
        "name": name,
        "description": str(payload.get("description") or "").strip(),
        "tags": normalize_string_list(payload.get("tags")),
        "status": str(payload.get("status") or "draft").strip() or "draft",
    }
    try:
        item = repositories.save_prompt_asset(
            tenant_id=tenant_id,
            prompt_id=prompt_id,
            payload=data,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    return {"item": item.to_dict()}


def copy_prompt_asset(prompt_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    source = load_prompt_asset(prompt_id, current_user)
    copy_name = next_copy_prompt_name(tenant_id=source.tenant_id, source_name=source.name)
    try:
        item = repositories.copy_prompt_asset(
            tenant_id=source.tenant_id,
            source_prompt_id=prompt_id,
            prompt_key=generate_prompt_key(tenant_id=source.tenant_id, name=copy_name),
            name=copy_name,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    return {"item": item.to_dict()}


def next_copy_prompt_name(*, tenant_id: int, source_name: str) -> str:
    base = f"{source_name} 副本"
    if not repositories.prompt_name_exists(tenant_id=tenant_id, name=base):
        return base
    for index in range(2, 1000):
        candidate = f"{base} {index}"
        if not repositories.prompt_name_exists(tenant_id=tenant_id, name=candidate):
            return candidate
    return f"{base} {uuid.uuid4().hex[:8]}"


def generate_prompt_key(*, tenant_id: int, name: Any) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", str(name or "prompt").strip().lower()).strip("_") or "prompt"
    base = base[:48].strip("_") or "prompt"
    for _ in range(8):
        candidate = f"{base}_{uuid.uuid4().hex[:8]}"
        if not repositories.prompt_key_exists(tenant_id=tenant_id, prompt_key=candidate):
            return candidate
    return f"{base}_{uuid.uuid4().hex[:16]}"


def delete_prompt_asset(prompt_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    item = load_prompt_asset(prompt_id, current_user)
    if item.status == PROMPT_ASSET_STATUS_ARCHIVED:
        try:
            deleted = repositories.delete_archived_prompt_asset(
                tenant_id=tenant_id,
                prompt_id=prompt_id,
                actor=current_actor(current_user),
                actor_id=current_user_id_or_none(current_user),
            )
        except RuntimeError as exc:
            raise storage_unavailable(exc) from exc
        if not deleted:
            raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
        return {"id": prompt_id, "archived": False, "deleted": True}

    try:
        archived = repositories.archive_prompt_asset(
            tenant_id=tenant_id,
            prompt_id=prompt_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not archived:
        raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    return {"id": prompt_id, "archived": True, "deleted": False}


def list_prompt_versions(prompt_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_prompt_asset(prompt_id, current_user)
    versions = repositories.list_prompt_versions(tenant_id=item.tenant_id, prompt_id=prompt_id)
    return {"items": [version.to_dict() for version in versions]}


def save_prompt_version(
    prompt_id: int,
    payload: dict[str, Any],
    current_user: dict[str, Any],
    version_id: int | None = None,
) -> dict[str, Any]:
    asset = load_prompt_asset(prompt_id, current_user)
    if version_id:
        existing = repositories.get_prompt_version(tenant_id=asset.tenant_id, version_id=version_id)
        if not existing or existing.prompt_id != prompt_id:
            raise domain_http_error(PromptVersionNotFound("prompt version not found"))
        if existing.status == PROMPT_VERSION_STATUS_PUBLISHED:
            raise domain_http_error(PromptVersionImmutable("published prompt versions cannot be edited"))
        requested_version = normalize_required(payload.get("version"), "version")
        if requested_version != existing.version:
            raise domain_http_error(PromptVersionImmutable("prompt version number cannot be changed; create a new version instead"))
    else:
        requested_version = normalize_required(payload.get("version"), "version")
    data = {
        "version": requested_version,
        "system_prompt": str(payload.get("system_prompt") or ""),
        "developer_prompt": str(payload.get("developer_prompt") or ""),
        "user_prompt_template": str(payload.get("user_prompt_template") or ""),
        "variables_schema": normalize_dict(payload.get("variables_schema")),
        "output_schema": normalize_dict(payload.get("output_schema")),
        "example_inputs": normalize_list_of_dict(payload.get("example_inputs")),
        "example_outputs": normalize_list_of_dict(payload.get("example_outputs")),
        "model_preferences": normalize_dict(payload.get("model_preferences")),
        "render_engine": str(payload.get("render_engine") or "simple").strip() or "simple",
        "status": str(payload.get("status") or "draft").strip() or "draft",
    }
    try:
        item = repositories.save_prompt_version(
            tenant_id=asset.tenant_id,
            prompt_id=prompt_id,
            version_id=version_id,
            payload=data,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(PromptVersionNotFound("prompt version not found"))
    return {"item": item.to_dict()}


def publish_prompt_version(prompt_id: int, version_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    return set_prompt_version_status(prompt_id, version_id, PROMPT_VERSION_STATUS_PUBLISHED, current_user)


def deprecate_prompt_version(prompt_id: int, version_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    return set_prompt_version_status(prompt_id, version_id, PROMPT_VERSION_STATUS_DEPRECATED, current_user)


def set_prompt_version_status(prompt_id: int, version_id: int, new_status: str, current_user: dict[str, Any]) -> dict[str, Any]:
    asset = load_prompt_asset(prompt_id, current_user)
    version = repositories.get_prompt_version(tenant_id=asset.tenant_id, version_id=version_id)
    if not version or version.prompt_id != prompt_id:
        raise domain_http_error(PromptVersionNotFound("prompt version not found"))
    if new_status == PROMPT_VERSION_STATUS_DEPRECATED and version.status == PROMPT_VERSION_STATUS_PUBLISHED:
        published_count = repositories.count_prompt_versions_by_status(
            tenant_id=asset.tenant_id,
            prompt_id=prompt_id,
            status=PROMPT_VERSION_STATUS_PUBLISHED,
        )
        if published_count <= 1:
            raise domain_http_error(
                PromptVersionStateConflict(
                    "cannot deprecate the only published prompt version; archive the prompt asset or publish another version first"
                )
            )
    item = repositories.set_prompt_version_status(
        tenant_id=asset.tenant_id,
        prompt_id=prompt_id,
        version_id=version_id,
        status=new_status,
        published_time=repositories.now_iso() if new_status == PROMPT_VERSION_STATUS_PUBLISHED else None,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    if not item:
        raise domain_http_error(PromptVersionNotFound("prompt version not found"))
    return {"item": item.to_dict()}


def load_prompt_asset(prompt_id: int, current_user: dict[str, Any]) -> PromptAsset:
    tenant_id = current_tenant_id(current_user)
    try:
        item = repositories.get_prompt_asset(tenant_id=tenant_id, prompt_id=prompt_id)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    return item


def normalize_required(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} is required")
    return text


def normalize_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def normalize_list_of_dict(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def current_tenant_id(current_user: dict[str, Any]) -> int:
    current = current_user.get("current_tenant") or {}
    tenant_id = current.get("id") or current_user.get("tenant_id") or 0
    return int(tenant_id)


def current_actor(current_user: dict[str, Any]) -> str:
    return str(current_user.get("username") or current_user.get("name") or "system")


def current_user_id_or_none(current_user: dict[str, Any]) -> int | None:
    user_id = int(current_user.get("id", 0) or 0)
    return user_id or None


def storage_unavailable(exc: RuntimeError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


def domain_http_error(exc: AIAssetsError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))
