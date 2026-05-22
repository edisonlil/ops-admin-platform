from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from system.application.tenancy import current_tenant_scope
from system.infrastructure.persistence.dialect import table_exists


DEFAULT_AI_QUOTA = {
    "max_applications": 5,
    "max_capabilities": 50,
    "max_assets": 200,
    "daily_run_limit": 1000,
    "monthly_token_limit": 1000000,
    "enabled": True,
}


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


def parse_json_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not value:
        return []
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def bool_value(value: Any) -> bool:
    return bool(value)


def current_tenant_id() -> int:
    return int(current_tenant_scope().tenant_id)


def normalize_key(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "-")


def list_ai_applications(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM ai_applications
        WHERE tenant_id = ? AND deleted = 0
        ORDER BY update_time DESC, id DESC
        """,
        (current_tenant_id(),),
    ).fetchall()
    return [ai_application_from_row(dict(row)) for row in rows]


def get_ai_application(conn: Any, app_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM ai_applications
        WHERE tenant_id = ? AND app_key = ? AND deleted = 0
        """,
        (current_tenant_id(), normalize_key(app_key)),
    ).fetchone()
    return ai_application_from_row(dict(row)) if row else None


def count_ai_applications(conn: Any, tenant_id: int | None = None) -> int:
    effective_tenant_id = current_tenant_id() if tenant_id is None else int(tenant_id)
    row = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM ai_applications
        WHERE tenant_id = ? AND deleted = 0
        """,
        (effective_tenant_id,),
    ).fetchone()
    return int(row["total"] if row else 0)


def prompt_asset_is_referenced_by_ai_application(conn: Any, *, tenant_id: int, prompt_key: str) -> bool:
    rows = conn.execute(
        """
        SELECT runtime_config_json
        FROM ai_applications
        WHERE tenant_id = ? AND deleted = 0
        """,
        (tenant_id,),
    ).fetchall()
    normalized_prompt_key = str(prompt_key or "").strip()
    for row in rows:
        runtime_config = parse_json_object(row["runtime_config_json"])
        if str(runtime_config.get("system_prompt_asset_key") or "").strip() == normalized_prompt_key:
            return True
    return False


def upsert_ai_application(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    app_key = normalize_key(payload.get("app_key"))
    if not app_key:
        raise ValueError("app_key is required")
    name = str(payload.get("name") or app_key).strip()
    if not name:
        raise ValueError("name is required")
    existing = conn.execute(
        "SELECT * FROM ai_applications WHERE tenant_id = ? AND app_key = ? AND deleted = 0",
        (tenant_id, app_key),
    ).fetchone()
    timestamp = now_text()
    values = (
        name,
        str(payload.get("description") or "").strip(),
        str(payload.get("app_type") or "single_turn_generation").strip(),
        str(payload.get("status") or "draft").strip(),
        normalize_key(payload.get("endpoint_slug") or app_key),
        str(payload.get("system_prompt") or ""),
        str(payload.get("developer_prompt") or ""),
        str(payload.get("user_prompt_template") or ""),
        json_text(payload.get("variables_schema")),
        json_text(payload.get("output_schema")),
        json_text(payload.get("model_preferences")),
        json_text(payload.get("auth_policy")),
        json_text(payload.get("quota_policy")),
        json_text(payload.get("trace_policy")),
        json_text(payload.get("runtime_config")),
        timestamp,
    )
    if existing:
        conn.execute(
            """
            UPDATE ai_applications
            SET name = ?,
                description = ?,
                app_type = ?,
                status = ?,
                endpoint_slug = ?,
                system_prompt = ?,
                developer_prompt = ?,
                user_prompt_template = ?,
                variables_schema_json = ?,
                output_schema_json = ?,
                model_preferences_json = ?,
                auth_policy_json = ?,
                quota_policy_json = ?,
                trace_policy_json = ?,
                runtime_config_json = ?,
                update_time = ?,
                lock_version = lock_version + 1
            WHERE tenant_id = ? AND app_key = ?
            """,
            (*values, tenant_id, app_key),
        )
    else:
        conn.execute(
            """
            INSERT INTO ai_applications (
                tenant_id, app_key, name, description, app_type, status, endpoint_slug,
                system_prompt, developer_prompt, user_prompt_template, variables_schema_json,
                output_schema_json, model_preferences_json, auth_policy_json, quota_policy_json,
                trace_policy_json, runtime_config_json, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, app_key, *values[:-1], timestamp, timestamp),
        )
    return get_ai_application(conn, app_key) or {}


def publish_ai_application(conn: Any, app_key: str) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    timestamp = now_text()
    conn.execute(
        """
        UPDATE ai_applications
        SET status = 'published',
            published_time = ?,
            update_time = ?,
            lock_version = lock_version + 1
        WHERE tenant_id = ? AND app_key = ? AND deleted = 0
        """,
        (timestamp, timestamp, tenant_id, normalize_key(app_key)),
    )
    return get_ai_application(conn, app_key) or {}


def create_agent_conversation(conn: Any, app_key: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    normalized_app_key = normalize_key(app_key)
    conversation_key = normalize_key((payload or {}).get("conversation_key")) or f"conv_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    title = str((payload or {}).get("title") or "新的 Agent 会话").strip() or "新的 Agent 会话"
    timestamp = now_text()
    conn.execute(
        """
        INSERT INTO ai_application_agent_conversations (
            tenant_id, conversation_key, app_key, title, status, metadata_json,
            create_time, update_time
        )
        VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
        """,
        (tenant_id, conversation_key, normalized_app_key, title, json_text((payload or {}).get("metadata")), timestamp, timestamp),
    )
    return get_agent_conversation(conn, normalized_app_key, conversation_key) or {}


def get_agent_conversation(conn: Any, app_key: str, conversation_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM ai_application_agent_conversations
        WHERE tenant_id = ? AND app_key = ? AND conversation_key = ? AND deleted = 0
        """,
        (current_tenant_id(), normalize_key(app_key), normalize_key(conversation_key)),
    ).fetchone()
    return agent_conversation_from_row(dict(row)) if row else None


def list_agent_conversations(conn: Any, app_key: str, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM ai_application_agent_conversations
        WHERE tenant_id = ? AND app_key = ? AND deleted = 0
        ORDER BY update_time DESC, id DESC
        LIMIT ?
        """,
        (current_tenant_id(), normalize_key(app_key), int(limit)),
    ).fetchall()
    return [agent_conversation_from_row(dict(row)) for row in rows]


def insert_agent_message(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    app_key = normalize_key(payload.get("app_key"))
    conversation_key = normalize_key(payload.get("conversation_key"))
    message_key = normalize_key(payload.get("message_key")) or f"msg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    role = str(payload.get("role") or "").strip()
    if role not in {"user", "assistant", "system", "tool"}:
        raise ValueError("role must be user, assistant, system, or tool")
    timestamp = now_text()
    conn.execute(
        """
        INSERT INTO ai_application_agent_messages (
            tenant_id, conversation_key, message_key, app_key, role, content,
            content_json, status, trace_id, error_code, error_message, metadata_json,
            create_time, update_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            conversation_key,
            message_key,
            app_key,
            role,
            str(payload.get("content") or ""),
            json_text(payload.get("content_json")),
            str(payload.get("status") or "completed"),
            str(payload.get("trace_id") or ""),
            str(payload.get("error_code") or ""),
            str(payload.get("error_message") or "")[:1000],
            json_text(payload.get("metadata")),
            timestamp,
            timestamp,
        ),
    )
    update_agent_conversation_summary(
        conn,
        app_key=app_key,
        conversation_key=conversation_key,
        role=role,
        content=str(payload.get("content") or ""),
        timestamp=timestamp,
    )
    return get_agent_message(conn, message_key) or {}


def update_agent_message(conn: Any, message_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    timestamp = now_text()
    conn.execute(
        """
        UPDATE ai_application_agent_messages
        SET content = ?,
            content_json = ?,
            status = ?,
            trace_id = ?,
            error_code = ?,
            error_message = ?,
            metadata_json = ?,
            update_time = ?,
            lock_version = lock_version + 1
        WHERE tenant_id = ? AND message_key = ? AND deleted = 0
        """,
        (
            str(payload.get("content") or ""),
            json_text(payload.get("content_json")),
            str(payload.get("status") or "completed"),
            str(payload.get("trace_id") or ""),
            str(payload.get("error_code") or ""),
            str(payload.get("error_message") or "")[:1000],
            json_text(payload.get("metadata")),
            timestamp,
            current_tenant_id(),
            normalize_key(message_key),
        ),
    )
    message = get_agent_message(conn, message_key) or {}
    if message:
        update_agent_conversation_summary(
            conn,
            app_key=str(message.get("app_key") or ""),
            conversation_key=str(message.get("conversation_key") or ""),
            role=str(message.get("role") or ""),
            content=str(message.get("content") or ""),
            timestamp=timestamp,
        )
    return message


def update_agent_conversation_summary(
    conn: Any,
    *,
    app_key: str,
    conversation_key: str,
    role: str,
    content: str,
    timestamp: str,
) -> None:
    preview = content.replace("\n", " ").strip()[:240]
    conn.execute(
        """
        UPDATE ai_application_agent_conversations
        SET last_message_role = ?,
            last_message_preview = ?,
            last_message_time = ?,
            update_time = ?,
            lock_version = lock_version + 1
        WHERE tenant_id = ? AND app_key = ? AND conversation_key = ? AND deleted = 0
        """,
        (role, preview, timestamp, timestamp, current_tenant_id(), normalize_key(app_key), normalize_key(conversation_key)),
    )


def get_agent_message(conn: Any, message_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM ai_application_agent_messages
        WHERE tenant_id = ? AND message_key = ? AND deleted = 0
        """,
        (current_tenant_id(), normalize_key(message_key)),
    ).fetchone()
    return agent_message_from_row(dict(row)) if row else None


def list_agent_messages(conn: Any, app_key: str, conversation_key: str, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM ai_application_agent_messages
        WHERE tenant_id = ? AND app_key = ? AND conversation_key = ? AND deleted = 0
        ORDER BY id ASC
        LIMIT ?
        """,
        (current_tenant_id(), normalize_key(app_key), normalize_key(conversation_key), int(limit)),
    ).fetchall()
    return [agent_message_from_row(dict(row)) for row in rows]


def list_recent_agent_messages(conn: Any, app_key: str, conversation_key: str, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM (
            SELECT *
            FROM ai_application_agent_messages
            WHERE tenant_id = ?
              AND app_key = ?
              AND conversation_key = ?
              AND deleted = 0
              AND status = 'completed'
              AND role IN ('user', 'assistant')
            ORDER BY id DESC
            LIMIT ?
        ) AS recent_messages
        ORDER BY id ASC
        """,
        (current_tenant_id(), normalize_key(app_key), normalize_key(conversation_key), int(limit)),
    ).fetchall()
    return [agent_message_from_row(dict(row)) for row in rows]


def ai_application_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "tenant_id": int(row["tenant_id"]),
        "app_key": str(row.get("app_key") or ""),
        "name": str(row.get("name") or ""),
        "description": str(row.get("description") or ""),
        "app_type": str(row.get("app_type") or "single_turn_generation"),
        "status": str(row.get("status") or "draft"),
        "endpoint_slug": str(row.get("endpoint_slug") or ""),
        "system_prompt": str(row.get("system_prompt") or ""),
        "developer_prompt": str(row.get("developer_prompt") or ""),
        "user_prompt_template": str(row.get("user_prompt_template") or ""),
        "variables_schema": parse_json_object(row.get("variables_schema_json")),
        "output_schema": parse_json_object(row.get("output_schema_json")),
        "model_preferences": parse_json_object(row.get("model_preferences_json")),
        "auth_policy": parse_json_object(row.get("auth_policy_json")),
        "quota_policy": parse_json_object(row.get("quota_policy_json")),
        "trace_policy": parse_json_object(row.get("trace_policy_json")),
        "runtime_config": parse_json_object(row.get("runtime_config_json")),
        "lock_version": int(row.get("lock_version") or 0),
        "published_time": str(row["published_time"]) if row.get("published_time") is not None else None,
        "create_time": str(row.get("create_time") or ""),
        "update_time": str(row.get("update_time") or ""),
    }


def agent_conversation_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "tenant_id": int(row["tenant_id"]),
        "conversation_key": str(row.get("conversation_key") or ""),
        "app_key": str(row.get("app_key") or ""),
        "title": str(row.get("title") or ""),
        "status": str(row.get("status") or "active"),
        "last_message_role": str(row.get("last_message_role") or ""),
        "last_message_preview": str(row.get("last_message_preview") or ""),
        "last_message_time": str(row["last_message_time"]) if row.get("last_message_time") is not None else None,
        "metadata": parse_json_object(row.get("metadata_json")),
        "lock_version": int(row.get("lock_version") or 0),
        "create_time": str(row.get("create_time") or ""),
        "update_time": str(row.get("update_time") or ""),
    }


def agent_message_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "tenant_id": int(row["tenant_id"]),
        "conversation_key": str(row.get("conversation_key") or ""),
        "message_key": str(row.get("message_key") or ""),
        "app_key": str(row.get("app_key") or ""),
        "role": str(row.get("role") or ""),
        "content": str(row.get("content") or ""),
        "content_json": parse_json_object(row.get("content_json")),
        "status": str(row.get("status") or "completed"),
        "trace_id": str(row.get("trace_id") or ""),
        "error_code": str(row.get("error_code") or ""),
        "error_message": str(row.get("error_message") or ""),
        "metadata": parse_json_object(row.get("metadata_json")),
        "lock_version": int(row.get("lock_version") or 0),
        "create_time": str(row.get("create_time") or ""),
        "update_time": str(row.get("update_time") or ""),
    }


def get_tenant_ai_quota(conn: Any, tenant_id: int | None = None) -> dict[str, Any]:
    tenant_id = current_tenant_id() if tenant_id is None else int(tenant_id)
    row = conn.execute(
        "SELECT * FROM tenant_ai_quotas WHERE tenant_id = ? AND deleted = 0",
        (tenant_id,),
    ).fetchone()
    quota = dict(DEFAULT_AI_QUOTA)
    quota["tenant_id"] = tenant_id
    if row:
        payload = dict(row)
        quota.update(
            {
                "max_applications": int(payload.get("max_applications") or 0),
                "max_capabilities": int(payload.get("max_capabilities") or 0),
                "max_assets": int(payload.get("max_assets") or 0),
                "daily_run_limit": int(payload.get("daily_run_limit") or 0),
                "monthly_token_limit": int(payload.get("monthly_token_limit") or 0),
                "enabled": bool_value(payload.get("enabled", True)),
            }
        )
    quota["usage"] = {
        "applications": count_ai_applications(conn, tenant_id=tenant_id),
        "capabilities": count_ai_capabilities_for_quota(conn, tenant_id=tenant_id),
    }
    return quota


def count_ai_capabilities_for_quota(conn: Any, tenant_id: int) -> int:
    if not table_exists(conn, "ai_capabilities"):
        return 0
    row = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM ai_capabilities
        WHERE tenant_id = ? AND deleted = 0
        """,
        (tenant_id,),
    ).fetchone()
    return int(row["total"] if row else 0)


def upsert_tenant_ai_quota(conn: Any, tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    timestamp = now_text()
    values = (
        int(payload.get("max_applications", DEFAULT_AI_QUOTA["max_applications"])),
        int(payload.get("max_capabilities", DEFAULT_AI_QUOTA["max_capabilities"])),
        int(payload.get("max_assets", DEFAULT_AI_QUOTA["max_assets"])),
        int(payload.get("daily_run_limit", DEFAULT_AI_QUOTA["daily_run_limit"])),
        int(payload.get("monthly_token_limit", DEFAULT_AI_QUOTA["monthly_token_limit"])),
        1 if bool(payload.get("enabled", True)) else 0,
        timestamp,
    )
    existing = conn.execute("SELECT id FROM tenant_ai_quotas WHERE tenant_id = ?", (tenant_id,)).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE tenant_ai_quotas
            SET max_applications = ?,
                max_capabilities = ?,
                max_assets = ?,
                daily_run_limit = ?,
                monthly_token_limit = ?,
                enabled = ?,
                update_time = ?,
                lock_version = lock_version + 1,
                deleted = 0
            WHERE tenant_id = ?
            """,
            (*values, tenant_id),
        )
    else:
        conn.execute(
            """
            INSERT INTO tenant_ai_quotas (
                tenant_id, max_applications, max_capabilities, max_assets,
                daily_run_limit, monthly_token_limit, enabled, create_time, update_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, *values[:-1], timestamp, timestamp),
        )
    return get_tenant_ai_quota(conn, tenant_id=tenant_id)


def record_prompt_runtime_trace(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    timestamp = now_text()
    tenant_id = current_tenant_id()
    trace_id = str(payload.get("trace_id") or "")
    conn.execute(
        """
        INSERT INTO prompt_runtime_traces (
            tenant_id, trace_id, caller_type, caller_key, app_key, app_version,
            route_key, model_key, provider_key, status, input_variables_json,
            rendered_messages_json, rendered_prompt, answer_text, usage_json,
            elapsed_ms, error_code, error_message, request_id, correlation_id,
            create_time, update_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            trace_id,
            str(payload.get("caller_type") or "studio_draft"),
            str(payload.get("caller_key") or ""),
            str(payload.get("app_key") or ""),
            str(payload.get("app_version") or ""),
            str(payload.get("route_key") or ""),
            str(payload.get("model_key") or ""),
            str(payload.get("provider_key") or ""),
            str(payload.get("status") or ""),
            json_text(payload.get("input_variables")),
            json_list_text(payload.get("rendered_messages")),
            str(payload.get("rendered_prompt") or ""),
            str(payload.get("answer") or ""),
            json_text(payload.get("usage")),
            int(payload.get("elapsed_ms") or 0),
            str(payload.get("error_code") or ""),
            str(payload.get("error_message") or "")[:1000],
            str(payload.get("request_id") or ""),
            str(payload.get("correlation_id") or ""),
            timestamp,
            timestamp,
        ),
    )
    return get_prompt_runtime_trace(conn, trace_id) or {}


def get_prompt_runtime_trace(conn: Any, trace_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM prompt_runtime_traces
        WHERE tenant_id = ? AND trace_id = ? AND deleted = 0
        """,
        (current_tenant_id(), trace_id),
    ).fetchone()
    return prompt_runtime_trace_from_row(dict(row)) if row else None


def list_prompt_runtime_traces(conn: Any, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM prompt_runtime_traces
        WHERE tenant_id = ? AND deleted = 0
        ORDER BY create_time DESC, id DESC
        LIMIT ?
        """,
        (current_tenant_id(), limit),
    ).fetchall()
    return [prompt_runtime_trace_from_row(dict(row)) for row in rows]


def list_ai_application_run_logs(conn: Any, app_key: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM prompt_runtime_traces
        WHERE tenant_id = ? AND app_key = ? AND deleted = 0
        ORDER BY create_time DESC, id DESC
        LIMIT ?
        """,
        (current_tenant_id(), app_key, limit),
    ).fetchall()
    return [ai_application_run_log_from_trace(dict(row)) for row in rows]


def list_ai_capability_run_logs(conn: Any, capability_key: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM prompt_runtime_traces
        WHERE tenant_id = ? AND caller_type = 'ai_capability' AND caller_key = ? AND deleted = 0
        ORDER BY create_time DESC, id DESC
        LIMIT ?
        """,
        (current_tenant_id(), normalize_key(capability_key), limit),
    ).fetchall()
    return [ai_application_run_log_from_trace(dict(row)) for row in rows]


def list_platform_ai_capability_run_logs(conn: Any, capability_key: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM prompt_runtime_traces
        WHERE caller_type = 'ai_capability' AND caller_key = ? AND deleted = 0
        ORDER BY create_time DESC, id DESC
        LIMIT ?
        """,
        (normalize_key(capability_key), limit),
    ).fetchall()
    return [ai_application_run_log_from_trace(dict(row)) for row in rows]


def ai_application_run_log_from_trace(row: dict[str, Any]) -> dict[str, Any]:
    trace = prompt_runtime_trace_from_row(row)
    return {
        "run_id": trace["trace_id"],
        "trace_id": trace["trace_id"],
        "app_key": trace["app_key"],
        "app_version": trace["app_version"],
        "run_mode": trace["caller_type"],
        "status": trace["status"],
        "model": trace["model_key"] or trace["route_key"],
        "input_variables": trace["input_variables"],
        "answer": trace["answer"],
        "usage": trace["usage"],
        "elapsed_ms": trace["elapsed_ms"],
        "error_code": trace["error_code"],
        "error_message": trace["error_message"],
        "request_id": trace["request_id"],
        "create_time": trace["create_time"],
    }


def prompt_runtime_trace_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": str(row.get("trace_id") or ""),
        "caller_type": str(row.get("caller_type") or ""),
        "caller_key": str(row.get("caller_key") or ""),
        "app_key": str(row.get("app_key") or ""),
        "app_version": str(row.get("app_version") or ""),
        "route_key": str(row.get("route_key") or ""),
        "model_key": str(row.get("model_key") or ""),
        "provider_key": str(row.get("provider_key") or ""),
        "status": str(row.get("status") or ""),
        "input_variables": parse_json_object(row.get("input_variables_json")),
        "rendered_messages": parse_json_list(row.get("rendered_messages_json")),
        "rendered_prompt": str(row.get("rendered_prompt") or ""),
        "answer": str(row.get("answer_text") or ""),
        "usage": parse_json_object(row.get("usage_json")),
        "elapsed_ms": int(row.get("elapsed_ms") or 0),
        "error_code": str(row.get("error_code") or ""),
        "error_message": str(row.get("error_message") or ""),
        "request_id": str(row.get("request_id") or ""),
        "correlation_id": str(row.get("correlation_id") or ""),
        "create_time": str(row.get("create_time") or ""),
    }
