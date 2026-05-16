from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from system.application.tenancy import current_tenant_scope


def now_text() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def json_text(value: Any) -> str:
    return json.dumps(value if isinstance(value, dict) else {}, ensure_ascii=False)


def json_list_text(value: Any) -> str:
    return json.dumps(value if isinstance(value, list) else [], ensure_ascii=False)


def bool_value(value: Any) -> bool:
    return bool(value)


def current_tenant_id() -> int:
    return int(current_tenant_scope().tenant_id)


DEFAULT_AI_QUOTA = {
    "max_applications": 5,
    "max_capabilities": 50,
    "max_assets": 200,
    "daily_run_limit": 1000,
    "monthly_token_limit": 1000000,
    "enabled": True,
}


def normalize_key(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "-")


def list_ai_capabilities(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM ai_capabilities
        WHERE tenant_id = ? AND deleted = 0
        ORDER BY update_time DESC, id DESC
        """,
        (current_tenant_id(),),
    ).fetchall()
    return [ai_capability_from_row(dict(row)) for row in rows]


def get_ai_capability(conn: Any, capability_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM ai_capabilities
        WHERE tenant_id = ? AND capability_key = ? AND deleted = 0
        """,
        (current_tenant_id(), normalize_key(capability_key)),
    ).fetchone()
    return ai_capability_from_row(dict(row)) if row else None


def count_ai_capabilities(conn: Any, tenant_id: int | None = None) -> int:
    effective_tenant_id = current_tenant_id() if tenant_id is None else int(tenant_id)
    row = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM ai_capabilities
        WHERE tenant_id = ? AND deleted = 0
        """,
        (effective_tenant_id,),
    ).fetchone()
    return int(row["total"] if row else 0)


def upsert_ai_capability(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    capability_key = normalize_key(payload.get("capability_key"))
    if not capability_key:
        raise ValueError("capability_key is required")
    name = str(payload.get("name") or capability_key).strip()
    if not name:
        raise ValueError("name is required")
    binding_type = str(payload.get("binding_type") or "prompt_runtime").strip()
    if binding_type not in {"prompt_runtime", "workflow_runtime"}:
        raise ValueError("binding_type must be prompt_runtime or workflow_runtime")
    binding_key = normalize_key(payload.get("binding_key"))
    if not binding_key:
        binding_key = capability_key
    existing = conn.execute(
        "SELECT * FROM ai_capabilities WHERE tenant_id = ? AND capability_key = ? AND deleted = 0",
        (tenant_id, capability_key),
    ).fetchone()
    timestamp = now_text()
    values = (
        name,
        str(payload.get("description") or "").strip(),
        str(payload.get("scope") or "tenant").strip() or "tenant",
        binding_type,
        binding_key,
        str(payload.get("call_method") or "aiService.execute").strip() or "aiService.execute",
        str(payload.get("system_prompt") or ""),
        str(payload.get("developer_prompt") or ""),
        str(payload.get("user_prompt_template") or ""),
        json_text(payload.get("input_schema")),
        json_text(payload.get("output_schema")),
        json_text(payload.get("model_preferences")),
        json_text(payload.get("runtime_config")),
        1 if bool(payload.get("enabled", True)) else 0,
        timestamp,
    )
    if existing:
        conn.execute(
            """
            UPDATE ai_capabilities
            SET name = ?,
                description = ?,
                scope = ?,
                binding_type = ?,
                binding_key = ?,
                call_method = ?,
                system_prompt = ?,
                developer_prompt = ?,
                user_prompt_template = ?,
                input_schema_json = ?,
                output_schema_json = ?,
                model_preferences_json = ?,
                runtime_config_json = ?,
                enabled = ?,
                update_time = ?,
                lock_version = lock_version + 1
            WHERE tenant_id = ? AND capability_key = ?
            """,
            (*values, tenant_id, capability_key),
        )
    else:
        conn.execute(
            """
            INSERT INTO ai_capabilities (
                tenant_id, capability_key, name, description, scope, binding_type,
                binding_key, call_method, system_prompt, developer_prompt,
                user_prompt_template, input_schema_json, output_schema_json,
                model_preferences_json, runtime_config_json, enabled, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, capability_key, *values[:-1], timestamp, timestamp),
        )
    return get_ai_capability(conn, capability_key) or {}


def ai_capability_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "tenant_id": int(row["tenant_id"]),
        "capability_key": str(row.get("capability_key") or ""),
        "name": str(row.get("name") or ""),
        "description": str(row.get("description") or ""),
        "scope": str(row.get("scope") or "tenant"),
        "binding_type": str(row.get("binding_type") or "prompt_runtime"),
        "binding_key": str(row.get("binding_key") or ""),
        "call_method": str(row.get("call_method") or "aiService.execute"),
        "system_prompt": str(row.get("system_prompt") or ""),
        "developer_prompt": str(row.get("developer_prompt") or ""),
        "user_prompt_template": str(row.get("user_prompt_template") or ""),
        "input_schema": parse_json_object(row.get("input_schema_json")),
        "output_schema": parse_json_object(row.get("output_schema_json")),
        "model_preferences": parse_json_object(row.get("model_preferences_json")),
        "runtime_config": parse_json_object(row.get("runtime_config_json")),
        "enabled": bool_value(row.get("enabled", True)),
        "lock_version": int(row.get("lock_version") or 0),
        "create_time": str(row.get("create_time") or ""),
        "update_time": str(row.get("update_time") or ""),
    }
