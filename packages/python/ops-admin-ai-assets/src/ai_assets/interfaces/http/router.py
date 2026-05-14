from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from ai_assets.application import services
from ai_assets.interfaces.http.dtos import (
    PromptAssetRequest,
    PromptBindingRequest,
    PromptContractRequest,
    PromptTestRequest,
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


@router.get("/prompt-contracts")
def prompt_contracts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = "",
    owner_context: str = "",
    enabled: bool | None = None,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:view")),
) -> dict[str, Any]:
    return ok(
        services.list_contracts(
            page=page,
            page_size=page_size,
            keyword=keyword,
            owner_context=owner_context,
            enabled=enabled,
            current_user=current_user,
        )
    )


@router.post("/prompt-contracts")
def create_prompt_contract(
    payload: PromptContractRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:contracts:manage")),
) -> dict[str, Any]:
    return ok(services.save_contract(payload.model_dump(), current_user))


@router.put("/prompt-contracts/{contract_key}")
def update_prompt_contract(
    contract_key: str,
    payload: PromptContractRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:contracts:manage")),
) -> dict[str, Any]:
    return ok(services.save_contract(payload.model_dump(), current_user, contract_key=contract_key))


@router.get("/prompt-contracts/{contract_key}/compatible-prompts")
def compatible_prompts(
    contract_key: str,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:view")),
) -> dict[str, Any]:
    return ok(services.compatible_prompts(contract_key, current_user))


@router.get("/prompt-bindings")
def prompt_bindings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    contract_key: str = "",
    environment: str = "",
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:view")),
) -> dict[str, Any]:
    return ok(
        services.list_bindings(
            page=page,
            page_size=page_size,
            contract_key=contract_key,
            environment=environment,
            current_user=current_user,
        )
    )


@router.post("/prompt-bindings")
def create_prompt_binding(
    payload: PromptBindingRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:bindings:manage")),
) -> dict[str, Any]:
    return ok(services.create_binding(payload.model_dump(), current_user))


@router.post("/prompt-bindings/{binding_id}/enable")
def enable_prompt_binding(
    binding_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:bindings:manage")),
) -> dict[str, Any]:
    return ok(services.enable_binding(binding_id, current_user))


@router.post("/prompt-bindings/{binding_id}/disable")
def disable_prompt_binding(
    binding_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:bindings:manage")),
) -> dict[str, Any]:
    return ok(services.disable_binding(binding_id, current_user))


@router.post("/prompts/test")
def test_prompt(
    payload: PromptTestRequest,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:assets:manage")),
) -> dict[str, Any]:
    return ok(services.execute_prompt(payload.model_dump(), current_user))


@router.get("/prompt-runs")
def prompt_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    contract_key: str = "",
    status_filter: str = Query(default="", alias="status"),
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:runs:view")),
) -> dict[str, Any]:
    return ok(
        services.list_runs(
            page=page,
            page_size=page_size,
            contract_key=contract_key,
            status_filter=status_filter,
            current_user=current_user,
        )
    )


@router.get("/prompt-runs/{run_id}")
def prompt_run(
    run_id: int,
    current_user: dict[str, Any] = Depends(auth.require_permission("prompt:runs:view")),
) -> dict[str, Any]:
    return ok(services.get_run(run_id, current_user))
