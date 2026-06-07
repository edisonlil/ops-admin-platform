from __future__ import annotations

import base64
import hashlib
import io
import re
import uuid
import zipfile
from typing import Any, Callable

from ai_service_api import AIServiceError, AIServiceUnavailable, get_ai_service
from fastapi import HTTPException, status

from ai_assets.application.ports import AIAssetsRepository
from ai_assets.domain.exceptions import (
    AIAssetsError,
    PromptAssetInUse,
    PromptAssetNameConflict,
    PromptAssetNotFound,
    PromptVersionImmutable,
    PromptVersionNotFound,
    PromptVersionStateConflict,
    InvalidSkillPackage,
    SkillAssetInUse,
    SkillAssetNameConflict,
    SkillAssetNotFound,
    SkillVersionImmutable,
    SkillVersionNotFound,
    SkillVersionStateConflict,
)
from ai_assets.domain.models import (
    PROMPT_ASSET_STATUS_ARCHIVED,
    PROMPT_ASSET_STATUS_PUBLISHED,
    PROMPT_VERSION_STATUS_DEPRECATED,
    PROMPT_VERSION_STATUS_PUBLISHED,
    SKILL_ASSET_STATUS_ARCHIVED,
    SKILL_ASSET_STATUS_PUBLISHED,
    SKILL_VERSION_STATUS_DEPRECATED,
    SKILL_VERSION_STATUS_PUBLISHED,
    PromptAsset,
    SkillAsset,
)
from system.application.sorting import InvalidSortError
from system.application.data_access import (
    ResourceDescriptor,
    data_access_for,
    data_owner_fields,
)

PromptAssetReferenceChecker = Callable[[int, str], bool]
SkillAssetReferenceChecker = Callable[[int, str], bool]

repository: AIAssetsRepository | None = None
_prompt_asset_reference_checkers: list[PromptAssetReferenceChecker] = []
_skill_asset_reference_checkers: list[SkillAssetReferenceChecker] = []
PROMPT_ASSET_RESOURCE = ResourceDescriptor(resource_key="prompt.asset")
SKILL_ASSET_RESOURCE = ResourceDescriptor(resource_key="ai_asset.skill")
MAX_SKILL_CONTENT_LENGTH = 200_000
MAX_SKILL_PACKAGE_BYTES = 5_000_000
MAX_SKILL_FILE_COUNT = 200
SKILL_RUNTIME_KINDS = {
    "",
    "prompt",
    "prompt_context",
    "context",
    "llm_task",
    "sandbox",
    "sandbox_python",
    "sandbox_shell",
    "python",
    "shell",
    "builtin",
    "builtin_executor",
}


def configure_repository(ai_assets_repository: AIAssetsRepository) -> None:
    global repository
    repository = ai_assets_repository


def repo() -> AIAssetsRepository:
    if repository is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ai assets repository is not configured")
    return repository


def list_prompt_assets(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    keyword: str = "",
    status_filter: str = "",
    tags: list[str] | str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repo().list_prompt_assets(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            keyword=keyword.strip(),
            status=status_filter.strip(),
            tags=normalize_filter_tags(tags),
            data_scope=data_access_for(current_user, PROMPT_ASSET_RESOURCE).read(),
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except InvalidSortError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def get_prompt_asset(prompt_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_prompt_asset(prompt_id, current_user)
    versions = repo().list_prompt_versions(tenant_id=item.tenant_id, prompt_id=prompt_id)
    return {"item": item.to_dict(), "versions": [version.to_dict() for version in versions]}


def list_published_prompt_assets(
    *,
    current_user: dict[str, Any],
    keyword: str = "",
    page: int = 1,
    page_size: int = 100,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    return list_prompt_assets(
        page=page,
        page_size=page_size,
        current_user=current_user,
        keyword=keyword,
        status_filter=PROMPT_ASSET_STATUS_PUBLISHED,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def get_published_prompt_asset(prompt_key: str, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    return resolve_published_prompt(prompt_key=prompt_key, tenant_id=tenant_id)


def polish_prompt(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt is required")
    variables = {
        "title": str(payload.get("title") or "").strip(),
        "prompt": prompt,
    }
    try:
        result = get_ai_service().execute("prompt.polish", variables)
    except AIServiceUnavailable as exc:
        raise HTTPException(status_code=503, detail="AI service is not available") from exc
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc) or "AI service execution failed") from exc
    return {
        "answer": result.answer,
        "trace_id": result.trace_id,
        "usage": result.usage,
    }


def resolve_published_prompt(*, prompt_key: str, tenant_id: int) -> dict[str, Any]:
    normalized_key = str(prompt_key or "").strip()
    if not normalized_key:
        raise domain_http_error(PromptAssetNotFound("published prompt asset not found"))
    try:
        asset = repo().get_prompt_asset_by_key(tenant_id=tenant_id, prompt_key=normalized_key)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not asset or asset.status != PROMPT_ASSET_STATUS_PUBLISHED:
        raise domain_http_error(PromptAssetNotFound("published prompt asset not found"))
    try:
        version = repo().get_published_prompt_version(tenant_id=tenant_id, prompt_id=asset.id)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not version:
        raise domain_http_error(PromptAssetNotFound("published prompt version not found"))
    version_payload = version.to_dict()
    return {
        "asset": asset.to_dict(),
        "version": version_payload,
        "prompt_key": asset.prompt_key,
        "asset_key": asset.prompt_key,
        "name": asset.name,
        "description": asset.description,
        "resolved_version": version.version,
        "system_prompt": version.system_prompt or version.user_prompt_template,
        "developer_prompt": version.developer_prompt,
        "user_prompt_template": version.user_prompt_template,
        "variables_schema": version.variables_schema,
        "output_schema": version.output_schema,
        "model_preferences": version.model_preferences,
        "published_time": version.published_time,
    }


def register_prompt_asset_reference_checker(checker: PromptAssetReferenceChecker) -> None:
    if checker not in _prompt_asset_reference_checkers:
        _prompt_asset_reference_checkers.append(checker)


def unregister_prompt_asset_reference_checker(checker: PromptAssetReferenceChecker) -> None:
    if checker in _prompt_asset_reference_checkers:
        _prompt_asset_reference_checkers.remove(checker)


def register_skill_asset_reference_checker(checker: SkillAssetReferenceChecker) -> None:
    if checker not in _skill_asset_reference_checkers:
        _skill_asset_reference_checkers.append(checker)


def unregister_skill_asset_reference_checker(checker: SkillAssetReferenceChecker) -> None:
    if checker in _skill_asset_reference_checkers:
        _skill_asset_reference_checkers.remove(checker)


def save_prompt_asset(payload: dict[str, Any], current_user: dict[str, Any], prompt_id: int | None = None) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        existing = (
            repo().get_prompt_asset(
                tenant_id=tenant_id,
                prompt_id=prompt_id,
                data_scope=data_access_for(current_user, PROMPT_ASSET_RESOURCE).write(),
            )
            if prompt_id
            else None
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if prompt_id and not existing:
        raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    prompt_key = existing.prompt_key if existing else str(payload.get("prompt_key") or "").strip()
    if not prompt_key:
        prompt_key = generate_prompt_key(tenant_id=tenant_id, name=payload.get("name"))
    name = normalize_required(payload.get("name"), "name")
    if repo().prompt_name_exists(tenant_id=tenant_id, name=name, exclude_prompt_id=prompt_id):
        raise domain_http_error(PromptAssetNameConflict("prompt title already exists"))
    data = {
        "prompt_key": prompt_key,
        "name": name,
        "description": str(payload.get("description") or "").strip(),
        "tags": normalize_string_list(payload.get("tags")),
        "status": str(payload.get("status") or "draft").strip() or "draft",
        **data_owner_fields(current_user),
    }
    try:
        item = repo().save_prompt_asset(
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
        item = repo().copy_prompt_asset(
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
    if not repo().prompt_name_exists(tenant_id=tenant_id, name=base):
        return base
    for index in range(2, 1000):
        candidate = f"{base} {index}"
        if not repo().prompt_name_exists(tenant_id=tenant_id, name=candidate):
            return candidate
    return f"{base} {uuid.uuid4().hex[:8]}"


def generate_prompt_key(*, tenant_id: int, name: Any) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", str(name or "prompt").strip().lower()).strip("_") or "prompt"
    base = base[:48].strip("_") or "prompt"
    for _ in range(8):
        candidate = f"{base}_{uuid.uuid4().hex[:8]}"
        if not repo().prompt_key_exists(tenant_id=tenant_id, prompt_key=candidate):
            return candidate
    return f"{base}_{uuid.uuid4().hex[:16]}"


def delete_prompt_asset(prompt_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    item = load_prompt_asset(prompt_id, current_user, action="manage")
    if item.status == PROMPT_ASSET_STATUS_ARCHIVED:
        try:
            deleted = repo().delete_archived_prompt_asset(
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

    ensure_prompt_asset_not_in_use(tenant_id=tenant_id, prompt_key=item.prompt_key)
    try:
        archived = repo().archive_prompt_asset(
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


def ensure_prompt_asset_not_in_use(*, tenant_id: int, prompt_key: str) -> None:
    for checker in list(_prompt_asset_reference_checkers):
        if checker(tenant_id, prompt_key):
            raise domain_http_error(PromptAssetInUse("提示词已被 AI 应用引用，不能归档"))


def list_prompt_versions(prompt_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_prompt_asset(prompt_id, current_user)
    versions = repo().list_prompt_versions(tenant_id=item.tenant_id, prompt_id=prompt_id)
    return {"items": [version.to_dict() for version in versions]}


def save_prompt_version(
    prompt_id: int,
    payload: dict[str, Any],
    current_user: dict[str, Any],
    version_id: int | None = None,
) -> dict[str, Any]:
    asset = load_prompt_asset(prompt_id, current_user, action="write")
    if version_id:
        existing = repo().get_prompt_version(tenant_id=asset.tenant_id, version_id=version_id)
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
        item = repo().save_prompt_version(
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
    asset = load_prompt_asset(prompt_id, current_user, action="manage")
    version = repo().get_prompt_version(tenant_id=asset.tenant_id, version_id=version_id)
    if not version or version.prompt_id != prompt_id:
        raise domain_http_error(PromptVersionNotFound("prompt version not found"))
    if new_status == PROMPT_VERSION_STATUS_DEPRECATED and version.status == PROMPT_VERSION_STATUS_PUBLISHED:
        published_count = repo().count_prompt_versions_by_status(
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
    item = repo().set_prompt_version_status(
        tenant_id=asset.tenant_id,
        prompt_id=prompt_id,
        version_id=version_id,
        status=new_status,
        published_time=repo().now_iso() if new_status == PROMPT_VERSION_STATUS_PUBLISHED else None,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    if not item:
        raise domain_http_error(PromptVersionNotFound("prompt version not found"))
    return {"item": item.to_dict()}


def load_prompt_asset(prompt_id: int, current_user: dict[str, Any], action: str = "read") -> PromptAsset:
    tenant_id = current_tenant_id(current_user)
    try:
        item = repo().get_prompt_asset(
            tenant_id=tenant_id,
            prompt_id=prompt_id,
            data_scope=data_access_for(current_user, PROMPT_ASSET_RESOURCE).predicate(action),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    return item


def list_skill_assets(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    keyword: str = "",
    status_filter: str = "",
    tags: list[str] | str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repo().list_skill_assets(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            keyword=keyword.strip(),
            status=status_filter.strip(),
            tags=normalize_filter_tags(tags),
            data_scope=data_access_for(current_user, SKILL_ASSET_RESOURCE).read(),
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except InvalidSortError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def get_skill_asset(skill_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_skill_asset(skill_id, current_user)
    versions = repo().list_skill_versions(tenant_id=item.tenant_id, skill_id=skill_id)
    return {"item": item.to_dict(), "versions": [version.to_dict() for version in versions]}


def list_published_skill_assets(
    *,
    current_user: dict[str, Any],
    keyword: str = "",
    page: int = 1,
    page_size: int = 100,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    return list_skill_assets(
        page=page,
        page_size=page_size,
        current_user=current_user,
        keyword=keyword,
        status_filter=SKILL_ASSET_STATUS_PUBLISHED,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def get_published_skill_asset(skill_key: str, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    payload = resolve_published_skill(skill_key=skill_key, tenant_id=tenant_id)
    payload.pop("package_data_base64", None)
    return payload


def resolve_published_skill(*, skill_key: str, tenant_id: int) -> dict[str, Any]:
    normalized_key = str(skill_key or "").strip()
    if not normalized_key:
        raise domain_http_error(SkillAssetNotFound("published skill asset not found"))
    try:
        asset = repo().get_skill_asset_by_key(tenant_id=tenant_id, skill_key=normalized_key)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not asset or asset.status != SKILL_ASSET_STATUS_PUBLISHED:
        raise domain_http_error(SkillAssetNotFound("published skill asset not found"))
    try:
        version = repo().get_published_skill_version(tenant_id=tenant_id, skill_id=asset.id)
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not version:
        raise domain_http_error(SkillAssetNotFound("published skill version not found"))
    version_payload = version.to_dict()
    return {
        "asset": asset.to_dict(),
        "version": version_payload,
        "skill_key": asset.skill_key,
        "asset_key": asset.skill_key,
        "name": asset.name,
        "description": asset.description,
        "resolved_version": version.version,
        "manifest": version.manifest,
        "content": version.content,
        "content_sha256": version.content_sha256,
        "entrypoint": version.entrypoint,
        "runtime_constraints": version.runtime_constraints,
        "package_sha256": version.package_sha256,
        "package_size": version.package_size,
        "package_data_base64": version.package_data_base64,
        "package_files": version.package_files,
        "validation_report": version.validation_report,
        "published_time": version.published_time,
    }


def save_skill_asset(payload: dict[str, Any], current_user: dict[str, Any], skill_id: int | None = None) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        existing = (
            repo().get_skill_asset(
                tenant_id=tenant_id,
                skill_id=skill_id,
                data_scope=data_access_for(current_user, SKILL_ASSET_RESOURCE).write(),
            )
            if skill_id
            else None
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if skill_id and not existing:
        raise domain_http_error(SkillAssetNotFound("skill asset not found"))
    skill_key = existing.skill_key if existing else str(payload.get("skill_key") or "").strip()
    if not skill_key:
        skill_key = generate_skill_key(tenant_id=tenant_id, name=payload.get("name"))
    name = normalize_required(payload.get("name"), "name")
    if repo().skill_name_exists(tenant_id=tenant_id, name=name, exclude_skill_id=skill_id):
        raise domain_http_error(SkillAssetNameConflict("skill title already exists"))
    data = {
        "skill_key": skill_key,
        "name": name,
        "description": str(payload.get("description") or "").strip(),
        "tags": normalize_string_list(payload.get("tags")),
        "status": str(payload.get("status") or "draft").strip() or "draft",
        "source_type": str(payload.get("source_type") or "upload").strip() or "upload",
        **data_owner_fields(current_user),
    }
    try:
        item = repo().save_skill_asset(
            tenant_id=tenant_id,
            skill_id=skill_id,
            payload=data,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(SkillAssetNotFound("skill asset not found"))
    return {"item": item.to_dict()}


def upload_skill_asset(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    package = normalize_skill_package_from_zip(payload)
    asset_payload = {
        "skill_key": package.get("skill_key") or payload.get("skill_key") or "",
        "name": package["name"],
        "description": package["description"],
        "tags": package["tags"],
        "status": "draft",
        "source_type": "upload",
    }
    saved = save_skill_asset(asset_payload, current_user)
    version = save_skill_version(
        int(saved["item"]["id"]),
        {
            "version": str(payload.get("version") or "1.0.0"),
            "filename": payload.get("filename") or "",
            "package_bytes": payload.get("package_bytes"),
            "status": "draft",
        },
        current_user,
    )
    return {"item": saved["item"], "version": version["item"]}


def generate_skill_key(*, tenant_id: int, name: Any) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", str(name or "skill").strip().lower()).strip("_") or "skill"
    base = base[:48].strip("_") or "skill"
    for _ in range(8):
        candidate = f"{base}_{uuid.uuid4().hex[:8]}"
        if not repo().skill_key_exists(tenant_id=tenant_id, skill_key=candidate):
            return candidate
    return f"{base}_{uuid.uuid4().hex[:16]}"


def delete_skill_asset(skill_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    item = load_skill_asset(skill_id, current_user, action="manage")
    if item.status == SKILL_ASSET_STATUS_ARCHIVED:
        try:
            deleted = repo().delete_archived_skill_asset(
                tenant_id=tenant_id,
                skill_id=skill_id,
                actor=current_actor(current_user),
                actor_id=current_user_id_or_none(current_user),
            )
        except RuntimeError as exc:
            raise storage_unavailable(exc) from exc
        if not deleted:
            raise domain_http_error(SkillAssetNotFound("skill asset not found"))
        return {"id": skill_id, "archived": False, "deleted": True}

    ensure_skill_asset_not_in_use(tenant_id=tenant_id, skill_key=item.skill_key)
    try:
        archived = repo().archive_skill_asset(
            tenant_id=tenant_id,
            skill_id=skill_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not archived:
        raise domain_http_error(SkillAssetNotFound("skill asset not found"))
    return {"id": skill_id, "archived": True, "deleted": False}


def ensure_skill_asset_not_in_use(*, tenant_id: int, skill_key: str) -> None:
    for checker in list(_skill_asset_reference_checkers):
        if checker(tenant_id, skill_key):
            raise domain_http_error(SkillAssetInUse("技能已被 AI 应用引用，不能归档"))


def list_skill_versions(skill_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    item = load_skill_asset(skill_id, current_user)
    versions = repo().list_skill_versions(tenant_id=item.tenant_id, skill_id=skill_id)
    return {"items": [version.to_dict() for version in versions]}


def save_skill_version(
    skill_id: int,
    payload: dict[str, Any],
    current_user: dict[str, Any],
    version_id: int | None = None,
) -> dict[str, Any]:
    asset = load_skill_asset(skill_id, current_user, action="write")
    if version_id:
        existing = repo().get_skill_version(tenant_id=asset.tenant_id, version_id=version_id)
        if not existing or existing.skill_id != skill_id:
            raise domain_http_error(SkillVersionNotFound("skill version not found"))
        if existing.status == SKILL_VERSION_STATUS_PUBLISHED:
            raise domain_http_error(SkillVersionImmutable("published skill versions cannot be edited"))
        requested_version = normalize_required(payload.get("version"), "version")
        if requested_version != existing.version:
            raise domain_http_error(SkillVersionImmutable("skill version number cannot be changed; create a new version instead"))
    else:
        requested_version = normalize_required(payload.get("version"), "version")
    package = normalize_skill_package_from_zip(payload)
    data = {
        "version": requested_version,
        "manifest": package["manifest"],
        "content": package["content"],
        "content_sha256": hashlib.sha256(package["content"].encode("utf-8")).hexdigest(),
        "entrypoint": package["entrypoint"],
        "runtime_constraints": package["runtime_constraints"],
        "package_sha256": package["package_sha256"],
        "package_size": package["package_size"],
        "package_data_base64": package["package_data_base64"],
        "package_files": package["package_files"],
        "validation_report": package["validation_report"],
        "status": str(payload.get("status") or "draft").strip() or "draft",
    }
    try:
        item = repo().save_skill_version(
            tenant_id=asset.tenant_id,
            skill_id=skill_id,
            version_id=version_id,
            payload=data,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(SkillVersionNotFound("skill version not found"))
    return {"item": item.to_dict()}


def publish_skill_version(skill_id: int, version_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    return set_skill_version_status(skill_id, version_id, SKILL_VERSION_STATUS_PUBLISHED, current_user)


def deprecate_skill_version(skill_id: int, version_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    return set_skill_version_status(skill_id, version_id, SKILL_VERSION_STATUS_DEPRECATED, current_user)


def set_skill_version_status(skill_id: int, version_id: int, new_status: str, current_user: dict[str, Any]) -> dict[str, Any]:
    asset = load_skill_asset(skill_id, current_user, action="manage")
    version = repo().get_skill_version(tenant_id=asset.tenant_id, version_id=version_id)
    if not version or version.skill_id != skill_id:
        raise domain_http_error(SkillVersionNotFound("skill version not found"))
    if new_status == SKILL_VERSION_STATUS_DEPRECATED and version.status == SKILL_VERSION_STATUS_PUBLISHED:
        published_count = repo().count_skill_versions_by_status(
            tenant_id=asset.tenant_id,
            skill_id=skill_id,
            status=SKILL_VERSION_STATUS_PUBLISHED,
        )
        if published_count <= 1:
            raise domain_http_error(
                SkillVersionStateConflict(
                    "cannot deprecate the only published skill version; archive the skill asset or publish another version first"
                )
            )
    item = repo().set_skill_version_status(
        tenant_id=asset.tenant_id,
        skill_id=skill_id,
        version_id=version_id,
        status=new_status,
        published_time=repo().now_iso() if new_status == SKILL_VERSION_STATUS_PUBLISHED else None,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    if not item:
        raise domain_http_error(SkillVersionNotFound("skill version not found"))
    return {"item": item.to_dict()}


def load_skill_asset(skill_id: int, current_user: dict[str, Any], action: str = "read") -> SkillAsset:
    tenant_id = current_tenant_id(current_user)
    try:
        item = repo().get_skill_asset(
            tenant_id=tenant_id,
            skill_id=skill_id,
            data_scope=data_access_for(current_user, SKILL_ASSET_RESOURCE).predicate(action),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(SkillAssetNotFound("skill asset not found"))
    return item


def find_skill_entry(archive: zipfile.ZipFile) -> zipfile.ZipInfo:
    candidates: list[tuple[str, zipfile.ZipInfo]] = []
    for entry in archive.infolist():
        if entry.is_dir():
            continue
        normalized = normalize_zip_entry_name(entry.filename)
        if not normalized:
            continue
        if normalized == "SKILL.md" or normalized.endswith("/SKILL.md"):
            candidates.append((normalized, entry))
    if not candidates:
        raise domain_http_error(InvalidSkillPackage("ZIP 技能包内必须包含 SKILL.md"))
    root_candidates = [entry for path, entry in candidates if path == "SKILL.md"]
    if root_candidates:
        return root_candidates[0]
    if len(candidates) == 1:
        return candidates[0][1]
    raise domain_http_error(InvalidSkillPackage("ZIP 技能包内存在多个 SKILL.md，请仅保留一个入口文件"))


def normalize_zip_entry_name(name: str) -> str:
    normalized = name.replace("\\", "/").strip("/")
    if not normalized or normalized.startswith("__MACOSX/"):
        return ""
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise domain_http_error(InvalidSkillPackage("ZIP 技能包包含不安全路径"))
    if ":" in parts[0]:
        raise domain_http_error(InvalidSkillPackage("ZIP 技能包包含不安全路径"))
    return normalized


def validate_skill_archive_entries(archive: zipfile.ZipFile) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    file_count = 0
    for entry in archive.infolist():
        normalized = normalize_zip_entry_name(entry.filename)
        if not normalized:
            continue
        if entry.flag_bits & 0x1:
            raise domain_http_error(InvalidSkillPackage("encrypted ZIP skill packages are not supported"))
        if entry.is_dir():
            continue
        file_count += 1
        if file_count > MAX_SKILL_FILE_COUNT:
            raise domain_http_error(InvalidSkillPackage("ZIP skill package contains too many files"))
        data = archive.read(entry)
        entries.append({"path": normalized, "size": int(entry.file_size or 0), "sha256": hashlib.sha256(data).hexdigest()})
    return entries


def normalize_skill_archive_package(archive: zipfile.ZipFile) -> tuple[bytes, list[dict[str, Any]], bytes]:
    skill_entry = find_skill_entry(archive)
    skill_path = normalize_zip_entry_name(skill_entry.filename)
    root_prefix = skill_path[: -len("SKILL.md")] if skill_path != "SKILL.md" else ""
    package_files: list[dict[str, Any]] = []
    raw_content = b""
    seen_paths: set[str] = set()
    file_count = 0
    canonical_buffer = io.BytesIO()
    with zipfile.ZipFile(canonical_buffer, "w", compression=zipfile.ZIP_DEFLATED) as canonical:
        for entry in archive.infolist():
            normalized = normalize_zip_entry_name(entry.filename)
            if not normalized:
                continue
            if entry.flag_bits & 0x1:
                raise domain_http_error(InvalidSkillPackage("encrypted ZIP skill packages are not supported"))
            if entry.is_dir():
                continue
            relative_path = normalized
            if root_prefix:
                if not normalized.startswith(root_prefix):
                    continue
                relative_path = normalized[len(root_prefix):]
            if not relative_path:
                continue
            validate_relative_skill_package_path(relative_path)
            if relative_path in seen_paths:
                raise domain_http_error(InvalidSkillPackage(f"duplicate skill package path: {relative_path}"))
            seen_paths.add(relative_path)
            file_count += 1
            if file_count > MAX_SKILL_FILE_COUNT:
                raise domain_http_error(InvalidSkillPackage("ZIP skill package contains too many files"))
            data = archive.read(entry)
            canonical.writestr(relative_path, data)
            package_files.append({"path": relative_path, "size": int(entry.file_size or 0), "sha256": hashlib.sha256(data).hexdigest()})
            if relative_path == "SKILL.md":
                raw_content = data
    if not raw_content:
        raise domain_http_error(InvalidSkillPackage("ZIP skill package must contain SKILL.md"))
    return raw_content, package_files, canonical_buffer.getvalue()


def validate_relative_skill_package_path(path: str) -> None:
    normalized = path.replace("\\", "/").strip("/")
    parts = normalized.split("/")
    if not normalized or any(part in {"", ".", ".."} for part in parts) or ":" in parts[0]:
        raise domain_http_error(InvalidSkillPackage("ZIP skill package contains unsafe path"))


def normalize_skill_package_from_zip(payload: dict[str, Any]) -> dict[str, Any]:
    filename = str(payload.get("filename") or "").strip()
    if filename and not filename.lower().endswith(".zip"):
        raise domain_http_error(InvalidSkillPackage("only ZIP skill packages are supported"))
    raw_package_bytes = payload.get("package_bytes")
    if not isinstance(raw_package_bytes, (bytes, bytearray)) or not raw_package_bytes:
        raise domain_http_error(InvalidSkillPackage("please upload a ZIP skill package"))
    package_bytes = bytes(raw_package_bytes)
    if len(package_bytes) > MAX_SKILL_PACKAGE_BYTES:
        raise domain_http_error(InvalidSkillPackage("ZIP skill package is too large"))
    try:
        with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
            raw_content, package_files, normalized_package_bytes = normalize_skill_archive_package(archive)
    except zipfile.BadZipFile as exc:
        raise domain_http_error(InvalidSkillPackage("ZIP skill package is invalid")) from exc
    except RuntimeError as exc:
        raise domain_http_error(InvalidSkillPackage("failed to read ZIP skill package")) from exc
    if len(raw_content) > MAX_SKILL_CONTENT_LENGTH:
        raise domain_http_error(InvalidSkillPackage("SKILL.md content is too large"))
    try:
        content = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise domain_http_error(InvalidSkillPackage("SKILL.md must be UTF-8 encoded")) from exc
    package = normalize_skill_package_content(
        {
            **payload,
            "content": content,
            "entrypoint": "SKILL.md",
            "package_files": package_files,
        }
    )
    package.update(
        {
            "package_sha256": hashlib.sha256(normalized_package_bytes).hexdigest(),
            "package_size": len(normalized_package_bytes),
            "package_data_base64": base64.b64encode(normalized_package_bytes).decode("ascii"),
        }
    )
    return package


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


def normalize_filter_tags(value: list[str] | str | None) -> list[str]:
    raw_items = value if isinstance(value, list) else [value] if value else []
    normalized: list[str] = []
    for item in raw_items:
        for tag in str(item or "").split(","):
            text = tag.strip()
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


def parse_skill_markdown_frontmatter(content: str) -> dict[str, Any]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    block: list[str] = []
    for line in lines[1:160]:
        if line.strip() == "---":
            return parse_simple_frontmatter(block)
        block.append(line.rstrip("\n"))
    return {}


def parse_simple_frontmatter(lines: list[str]) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if stripped.startswith("- "):
            if isinstance(parent, list):
                parent.append(parse_frontmatter_scalar(stripped[2:].strip()))
            continue
        if ":" not in stripped or not isinstance(parent, dict):
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            continue
        if not raw_value:
            next_container: dict[str, Any] | list[Any]
            next_container = [] if next_nonempty_line_is_list(lines, line) else {}
            parent[key] = next_container
            stack.append((indent, next_container))
            continue
        if raw_value in {"|", ">"}:
            parent[key] = ""
            continue
        parent[key] = parse_frontmatter_scalar(raw_value)
    return root


def next_nonempty_line_is_list(lines: list[str], current_line: str) -> bool:
    try:
        start = lines.index(current_line) + 1
    except ValueError:
        return False
    current_indent = len(current_line) - len(current_line.lstrip(" "))
    for line in lines[start:]:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        return indent > current_indent and line.strip().startswith("- ")
    return False


def parse_frontmatter_scalar(value: str) -> Any:
    text = value.strip().strip('"').strip("'")
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    return text


def infer_skill_package_name(payload: dict[str, Any], manifest: dict[str, Any]) -> str:
    for value in (payload.get("name"), manifest.get("name"), payload.get("skill_key"), manifest.get("skill_key")):
        text = str(value or "").strip()
        if text:
            return text
    filename = str(payload.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if filename.lower().endswith(".zip"):
        filename = filename[:-4]
    filename = re.sub(r"[-_. ]*v?\d+(?:\.\d+){1,3}$", "", filename, flags=re.IGNORECASE).strip("-_. ")
    return filename or "uploaded-skill"


def normalize_skill_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9_.-]+", "_", text).strip("._-")
    return normalized[:80].strip("._-")


def normalize_skill_package_content(payload: dict[str, Any]) -> dict[str, Any]:
    content = str(payload.get("content") or payload.get("skill_content") or "").strip()
    if not content:
        raise domain_http_error(InvalidSkillPackage("skill content is required"))
    if len(content) > MAX_SKILL_CONTENT_LENGTH:
        raise domain_http_error(InvalidSkillPackage("skill content is too large"))
    manifest = {**parse_skill_markdown_frontmatter(content), **normalize_dict(payload.get("manifest"))}
    package_files = normalize_list_of_dict(payload.get("package_files"))
    manifest = normalize_skill_manifest(manifest, package_files=package_files)
    name = infer_skill_package_name(payload, manifest)
    description = str(payload.get("description") or manifest.get("description") or "").strip()
    tags = normalize_string_list(payload.get("tags") or manifest.get("tags"))
    skill_key = normalize_skill_key(payload.get("skill_key") or manifest.get("skill_key") or name)
    manifest.update({"name": name, "skill_key": skill_key, "description": description})
    if tags:
        manifest["tags"] = tags
    entrypoint = runtime_entrypoint(manifest, fallback=str(payload.get("entrypoint") or "SKILL.md"))
    validate_skill_package_runtime(manifest, entrypoint=entrypoint, package_files=package_files)
    runtime_constraints = {**manifest_runtime_constraints(manifest), **normalize_dict(payload.get("runtime_constraints"))}
    return {
        "skill_key": skill_key,
        "name": name,
        "description": description,
        "tags": tags,
        "manifest": manifest,
        "content": content,
        "entrypoint": entrypoint,
        "runtime_constraints": runtime_constraints,
        "package_sha256": str(payload.get("package_sha256") or ""),
        "package_size": int(payload.get("package_size") or 0),
        "package_data_base64": str(payload.get("package_data_base64") or ""),
        "package_files": package_files,
        "validation_report": {
            "valid": True,
            "entrypoint": entrypoint,
            "runtime_kind": skill_runtime_kind(manifest),
            "file_count": len(package_files),
            "checks": [
                {"code": "name", "message": "skill name is present", "passed": True},
                {"code": "content", "message": "SKILL.md is present", "passed": True},
                {"code": "entrypoint", "message": "entrypoint is valid for runtime", "passed": True},
                {"code": "package", "message": "complete ZIP package is persisted", "passed": True},
            ],
        },
    }


def normalize_skill_manifest(manifest: dict[str, Any], *, package_files: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = dict(manifest)
    runtime = normalize_dict(normalized.get("runtime"))
    if not runtime:
        runtime = {}
    kind = normalize_runtime_kind(runtime.get("kind") or runtime.get("type") or normalized.get("runtime_kind"))
    if kind:
        runtime["kind"] = kind
    elif not runtime:
        runtime["kind"] = "prompt_context"
    normalized["runtime"] = runtime
    if package_files:
        normalized["package_files"] = package_files
    return normalized


def skill_runtime_kind(manifest: dict[str, Any]) -> str:
    runtime = normalize_dict(manifest.get("runtime"))
    return normalize_runtime_kind(runtime.get("kind") or runtime.get("type") or manifest.get("runtime_kind"))


def normalize_runtime_kind(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"promptcontext", "prompt_context"}:
        normalized = "prompt_context"
    if normalized in {"llm", "llm_skill", "llm_task"}:
        normalized = "llm_task"
    return normalized


def runtime_entrypoint(manifest: dict[str, Any], *, fallback: str) -> str:
    runtime = normalize_dict(manifest.get("runtime"))
    entrypoint = str(runtime.get("entrypoint") or manifest.get("entrypoint") or fallback or "SKILL.md").strip()
    return entrypoint.replace("\\", "/").lstrip("/") or "SKILL.md"


def manifest_runtime_constraints(manifest: dict[str, Any]) -> dict[str, Any]:
    runtime = normalize_dict(manifest.get("runtime"))
    result: dict[str, Any] = {}
    for key in ("network", "timeout_seconds", "requirements", "image", "memory", "cpus"):
        if key in runtime:
            result[key] = runtime[key]
    return result


def validate_skill_package_runtime(manifest: dict[str, Any], *, entrypoint: str, package_files: list[dict[str, Any]]) -> None:
    kind = skill_runtime_kind(manifest)
    if kind not in SKILL_RUNTIME_KINDS:
        raise domain_http_error(InvalidSkillPackage(f"unsupported skill runtime kind: {kind}"))
    file_paths = {str(item.get("path") or "") for item in package_files}
    if entrypoint not in file_paths:
        raise domain_http_error(InvalidSkillPackage(f"skill entrypoint not found in package: {entrypoint}"))
    runtime = normalize_dict(manifest.get("runtime"))
    requirements = str(runtime.get("requirements") or "").strip().replace("\\", "/").lstrip("/")
    if requirements and requirements not in file_paths:
        raise domain_http_error(InvalidSkillPackage(f"skill requirements file not found in package: {requirements}"))


