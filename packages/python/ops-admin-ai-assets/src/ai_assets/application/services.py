from __future__ import annotations

import json
import re
import time
from typing import Any

from fastapi import HTTPException, status

from ai_assets.domain.exceptions import (
    AIAssetsError,
    PromptAssetNotFound,
    PromptBindingNotFound,
    PromptCompatibilityError,
    PromptContractNotFound,
    PromptRenderError,
    PromptRunNotFound,
    PromptVersionImmutable,
    PromptVersionNotFound,
)
from ai_assets.domain.models import (
    PROMPT_RUN_STATUS_FAILED,
    PROMPT_RUN_STATUS_SUCCEEDED,
    PROMPT_VERSION_STATUS_DEPRECATED,
    PROMPT_VERSION_STATUS_PUBLISHED,
    PromptAsset,
    PromptTaskContract,
    PromptVersion,
)
from ai_assets.infrastructure.persistence import repositories
from llm_runtime.application import gateway as llm_gateway
from system.interfaces.http import current_request_id


VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_\.]*)\s*}}")


def list_prompt_assets(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    keyword: str = "",
    category: str = "",
    owner_context: str = "",
    status_filter: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repositories.list_prompt_assets(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            keyword=keyword.strip(),
            category=category.strip(),
            owner_context=owner_context.strip(),
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
    data = {
        "prompt_key": normalize_required(payload.get("prompt_key"), "prompt_key"),
        "name": normalize_required(payload.get("name"), "name"),
        "description": str(payload.get("description") or "").strip(),
        "category": str(payload.get("category") or "general").strip() or "general",
        "tags": normalize_string_list(payload.get("tags")),
        "owner_context": str(payload.get("owner_context") or "general").strip() or "general",
        "visibility": str(payload.get("visibility") or "tenant").strip() or "tenant",
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


def delete_prompt_asset(prompt_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        deleted = repositories.delete_prompt_asset(
            tenant_id=tenant_id,
            prompt_id=prompt_id,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not deleted:
        raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    return {"id": prompt_id, "deleted": True}


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
    data = {
        "version": normalize_required(payload.get("version"), "version"),
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


def list_contracts(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    keyword: str = "",
    owner_context: str = "",
    enabled: bool | None = None,
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repositories.list_contracts(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            keyword=keyword.strip(),
            owner_context=owner_context.strip(),
            enabled=enabled,
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def save_contract(payload: dict[str, Any], current_user: dict[str, Any], contract_key: str | None = None) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    key = str(contract_key or payload.get("contract_key") or "").strip()
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contract_key is required")
    data = {
        "contract_key": key,
        "owner_context": str(payload.get("owner_context") or "general").strip() or "general",
        "task_kind": str(payload.get("task_kind") or "single_call").strip() or "single_call",
        "display_name": str(payload.get("display_name") or key).strip() or key,
        "description": str(payload.get("description") or "").strip(),
        "llm_task_key": str(payload.get("llm_task_key") or key).strip() or key,
        "input_schema": normalize_dict(payload.get("input_schema")),
        "output_schema": normalize_dict(payload.get("output_schema")),
        "required_capabilities": normalize_string_list(payload.get("required_capabilities")),
        "allowed_prompt_scopes": normalize_dict(payload.get("allowed_prompt_scopes")),
        "enabled": bool(payload.get("enabled", True)),
    }
    try:
        item = repositories.save_contract(
            tenant_id=tenant_id,
            contract_key=contract_key,
            payload=data,
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(PromptContractNotFound("prompt contract not found"))
    return {"item": item.to_dict()}


def compatible_prompts(contract_key: str, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    contract = repositories.get_contract_by_key(tenant_id=tenant_id, contract_key=contract_key)
    if not contract:
        raise domain_http_error(PromptContractNotFound("prompt contract not found"))
    items: list[dict[str, Any]] = []
    for asset, version in repositories.list_prompt_versions_for_compatibility(tenant_id=tenant_id):
        compatible, reasons = check_compatibility(contract, asset, version)
        if compatible:
            items.append({"prompt": asset.to_dict(), "version": version.to_dict(), "reasons": reasons})
    return {"items": items}


def list_bindings(
    *,
    page: int,
    page_size: int,
    current_user: dict[str, Any],
    contract_key: str = "",
    environment: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    try:
        items, total = repositories.list_bindings(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            contract_key=contract_key.strip(),
            environment=environment.strip(),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def create_binding(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    contract_id = int(payload.get("contract_id") or 0)
    prompt_id = int(payload.get("prompt_id") or 0)
    prompt_version_id = int(payload.get("prompt_version_id") or 0)
    contract = repositories.get_contract(tenant_id=tenant_id, contract_id=contract_id)
    asset = repositories.get_prompt_asset(tenant_id=tenant_id, prompt_id=prompt_id)
    version = repositories.get_prompt_version(tenant_id=tenant_id, version_id=prompt_version_id)
    if not contract:
        raise domain_http_error(PromptContractNotFound("prompt contract not found"))
    if not asset:
        raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    if not version or version.prompt_id != prompt_id:
        raise domain_http_error(PromptVersionNotFound("prompt version not found"))
    compatible, reasons = check_compatibility(contract, asset, version)
    if not compatible:
        raise domain_http_error(PromptCompatibilityError("; ".join(reasons)))
    try:
        item = repositories.save_binding(
            tenant_id=tenant_id,
            payload={
                "contract_id": contract_id,
                "prompt_id": prompt_id,
                "prompt_version_id": prompt_version_id,
                "binding_name": str(payload.get("binding_name") or "").strip(),
                "priority": int(payload.get("priority") or 100),
                "environment": str(payload.get("environment") or "dev").strip() or "dev",
                "enabled": bool(payload.get("enabled", True)),
                "effective_from": payload.get("effective_from"),
                "effective_to": payload.get("effective_to"),
            },
            actor=current_actor(current_user),
            actor_id=current_user_id_or_none(current_user),
        )
    except RuntimeError as exc:
        raise storage_unavailable(exc) from exc
    if not item:
        raise domain_http_error(PromptBindingNotFound("prompt binding not found"))
    return {"item": item.to_dict()}


def enable_binding(binding_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    return set_binding_enabled(binding_id, True, current_user)


def disable_binding(binding_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    return set_binding_enabled(binding_id, False, current_user)


def set_binding_enabled(binding_id: int, enabled: bool, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    item = repositories.set_binding_enabled(
        tenant_id=tenant_id,
        binding_id=binding_id,
        enabled=enabled,
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    if not item:
        raise domain_http_error(PromptBindingNotFound("prompt binding not found"))
    return {"item": item.to_dict()}


def execute_prompt(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    contract_key = str(payload.get("contract_key") or "").strip()
    variables = normalize_dict(payload.get("variables"))
    environment = str(payload.get("environment") or "prod").strip() or "prod"
    prompt_version_id = int(payload["prompt_version_id"]) if payload.get("prompt_version_id") else None
    contract = repositories.get_contract_by_key(tenant_id=tenant_id, contract_key=contract_key)
    if not contract or not contract.enabled:
        raise domain_http_error(PromptContractNotFound("prompt contract not found"))
    if prompt_version_id:
        version = repositories.get_prompt_version(tenant_id=tenant_id, version_id=prompt_version_id)
        if not version:
            raise domain_http_error(PromptVersionNotFound("prompt version not found"))
        asset = repositories.get_prompt_asset(tenant_id=tenant_id, prompt_id=version.prompt_id)
        if not asset:
            raise domain_http_error(PromptAssetNotFound("prompt asset not found"))
    else:
        binding = repositories.effective_binding(tenant_id=tenant_id, contract_id=contract.id, environment=environment)
        if not binding:
            raise domain_http_error(PromptBindingNotFound("prompt binding not found"))
        version = repositories.get_prompt_version(tenant_id=tenant_id, version_id=binding.prompt_version_id)
        asset = repositories.get_prompt_asset(tenant_id=tenant_id, prompt_id=binding.prompt_id)
        if not version or not asset:
            raise domain_http_error(PromptVersionNotFound("prompt version not found"))
    compatible, reasons = check_compatibility(contract, asset, version)
    if not compatible:
        raise domain_http_error(PromptCompatibilityError("; ".join(reasons)))
    input_errors = validate_required_fields(contract.input_schema, variables, "input")
    input_errors.extend(validate_required_fields(version.variables_schema, variables, "variables"))
    if input_errors:
        raise domain_http_error(PromptRenderError("; ".join(input_errors)))
    messages = render_messages(version, variables)
    started = time.perf_counter()
    output_text = ""
    output_json: dict[str, Any] | None = None
    validation_errors: list[str] = []
    run_status = PROMPT_RUN_STATUS_FAILED
    request_id = current_request_id()
    correlation_id = str(payload.get("correlation_id") or request_id)
    try:
        response = llm_gateway.generate(
            task_key=contract.llm_task_key,
            messages=messages,
            response_format="json" if contract.output_schema or version.output_schema else None,
            correlation_id=correlation_id,
        )
        output_text = response.content
        output_json = parse_output_json(output_text)
        validation_errors = validate_output(contract.output_schema, version.output_schema, output_json)
        run_status = PROMPT_RUN_STATUS_SUCCEEDED if not validation_errors else PROMPT_RUN_STATUS_FAILED
    except Exception as exc:
        validation_errors = [str(exc)]
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    run = repositories.create_run(
        tenant_id=tenant_id,
        payload={
            "contract_key": contract.contract_key,
            "prompt_id": asset.id,
            "prompt_version_id": version.id,
            "llm_task_key": contract.llm_task_key,
            "input": variables,
            "rendered_messages": messages,
            "output_text": output_text,
            "output_json": output_json,
            "schema_valid": run_status == PROMPT_RUN_STATUS_SUCCEEDED,
            "validation_errors": validation_errors,
            "status": run_status,
            "elapsed_ms": elapsed_ms,
            "request_id": request_id,
            "correlation_id": correlation_id,
        },
        actor=current_actor(current_user),
        actor_id=current_user_id_or_none(current_user),
    )
    if run_status == PROMPT_RUN_STATUS_FAILED and not output_text:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="prompt execution failed: " + "; ".join(validation_errors))
    return {
        "run": run.to_dict(),
        "rendered_messages": messages,
        "output_text": output_text,
        "output_json": output_json,
        "schema_valid": run_status == PROMPT_RUN_STATUS_SUCCEEDED,
        "validation_errors": validation_errors,
    }


def list_runs(
    *, page: int, page_size: int, current_user: dict[str, Any], contract_key: str = "", status_filter: str = ""
) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    items, total = repositories.list_runs(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        contract_key=contract_key.strip(),
        status=status_filter.strip(),
    )
    return {
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


def get_run(run_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id(current_user)
    item = repositories.get_run(tenant_id=tenant_id, run_id=run_id)
    if not item:
        raise domain_http_error(PromptRunNotFound("prompt run not found"))
    return {"item": item.to_dict()}


def check_compatibility(contract: PromptTaskContract, asset: PromptAsset, version: PromptVersion) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    allowed = contract.allowed_prompt_scopes or {}
    allowed_owner_contexts = normalize_string_list(allowed.get("owner_contexts"))
    allowed_categories = normalize_string_list(allowed.get("categories"))
    allowed_tags = normalize_string_list(allowed.get("tags"))
    allowed_prompt_keys = normalize_string_list(allowed.get("prompt_keys"))
    allowed_visibility = normalize_string_list(allowed.get("visibility"))
    if allowed_owner_contexts and asset.owner_context not in allowed_owner_contexts:
        reasons.append("owner_context is outside the contract scope")
    if allowed_categories and asset.category not in allowed_categories:
        reasons.append("category is outside the contract scope")
    if allowed_prompt_keys and asset.prompt_key not in allowed_prompt_keys:
        reasons.append("prompt_key is outside the contract scope")
    if allowed_visibility and asset.visibility not in allowed_visibility:
        reasons.append("visibility is outside the contract scope")
    if allowed_tags and not set(asset.tags).intersection(allowed_tags):
        reasons.append("tags do not match the contract scope")

    contract_input_props = schema_properties(contract.input_schema)
    version_input_props = schema_properties(version.variables_schema)
    version_required = schema_required(version.variables_schema)
    contract_required = schema_required(contract.input_schema)
    missing_for_prompt = sorted(version_required - contract_input_props)
    missing_contract_required = sorted(contract_required - version_input_props) if version_input_props else []
    if missing_for_prompt:
        reasons.append("version requires variables outside contract input: " + ", ".join(missing_for_prompt))
    if missing_contract_required:
        reasons.append("version variables miss contract required fields: " + ", ".join(missing_contract_required))

    contract_output_required = schema_required(contract.output_schema)
    version_output_props = schema_properties(version.output_schema)
    if contract_output_required and version_output_props:
        missing_output = sorted(contract_output_required - version_output_props)
        if missing_output:
            reasons.append("version output schema misses contract required fields: " + ", ".join(missing_output))
    return not reasons, (["compatible"] if not reasons else reasons)


def render_messages(version: PromptVersion, variables: dict[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for role, template in (
        ("system", version.system_prompt),
        ("developer", version.developer_prompt),
        ("user", version.user_prompt_template),
    ):
        if not template:
            continue
        messages.append({"role": role, "content": render_template(template, variables)})
    return messages


def render_template(template: str, variables: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = nested_value(variables, key)
        if value is None:
            raise domain_http_error(PromptRenderError(f"missing variable: {key}"))
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    return VARIABLE_PATTERN.sub(replace, template)


def nested_value(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def validate_required_fields(schema: dict[str, Any], payload: dict[str, Any], label: str) -> list[str]:
    return [f"{label}.{name} is required" for name in sorted(schema_required(schema)) if name not in payload]


def validate_output(
    contract_schema: dict[str, Any], version_schema: dict[str, Any], output_json: dict[str, Any] | None
) -> list[str]:
    if not contract_schema and not version_schema:
        return []
    if output_json is None:
        return ["output is not valid JSON"]
    errors = validate_required_fields(contract_schema, output_json, "output")
    errors.extend(validate_required_fields(version_schema, output_json, "output"))
    return errors


def parse_output_json(output_text: str) -> dict[str, Any] | None:
    text = output_text.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def schema_properties(schema: dict[str, Any]) -> set[str]:
    props = schema.get("properties") if isinstance(schema, dict) else None
    return set(props) if isinstance(props, dict) else set()


def schema_required(schema: dict[str, Any]) -> set[str]:
    required = schema.get("required") if isinstance(schema, dict) else None
    return {str(item) for item in required} if isinstance(required, list) else set()


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
