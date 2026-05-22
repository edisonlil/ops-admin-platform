from __future__ import annotations

import json
from datetime import date
from datetime import datetime
from datetime import time
from typing import Any

from system.application.tenancy import current_tenant_scope
from system.application.sorting import build_order_by
from system.application.sorting import parse_sort_params
from system.infrastructure.persistence.dialect import table_exists


DEFAULT_AI_QUOTA = {
    "max_applications": 5,
    "max_capabilities": 50,
    "max_assets": 200,
    "daily_run_limit": 1000,
    "monthly_token_limit": 1000000,
    "enabled": True,
}

DATA_URL_PREFIXES = ("data:image/", "data:audio/", "data:video/", "data:application/")
TRACE_LIST_COLUMNS = """
    id, tenant_id, trace_id, caller_type, caller_key, app_key, app_version,
    route_key, model_key, provider_key, status, input_variables_json,
    rendered_prompt, answer_text, usage_json, elapsed_ms, error_code,
    error_message, request_id, correlation_id, create_time
"""
TRACE_DEFAULT_ORDER_BY = "create_time DESC, id DESC"


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
    return json.dumps(sanitize_trace_value(value) if isinstance(value, dict) else {}, ensure_ascii=False)


def json_list_text(value: Any) -> str:
    return json.dumps(sanitize_trace_value(value) if isinstance(value, list) else [], ensure_ascii=False)


def json_any_text(value: Any) -> str:
    return json.dumps(sanitize_trace_value(value), ensure_ascii=False)


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
    sanitized_variables = sanitize_trace_value(payload.get("input_variables"))
    sanitized_messages = sanitize_trace_value(payload.get("rendered_messages"))
    if not isinstance(sanitized_variables, dict):
        sanitized_variables = {}
    if not isinstance(sanitized_messages, list):
        sanitized_messages = []
    answer = str(payload.get("answer") or "")
    rendered_prompt = str(payload.get("rendered_prompt") or "")
    input_preview = trace_input_preview(sanitized_variables)
    answer_preview = text_preview(answer)
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
            json_text(input_preview),
            json_list_text([]),
            text_preview(rendered_prompt),
            answer_preview,
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
    conn.execute(
        """
        INSERT INTO prompt_runtime_trace_details (
            tenant_id, trace_id, input_variables_json, rendered_messages_json,
            rendered_prompt, answer_text, metadata_json, create_time, update_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            trace_id,
            json_text(sanitized_variables),
            json_any_text(sanitized_messages),
            text_preview(rendered_prompt, max_chars=20000),
            answer,
            json_text(trace_metadata(payload, sanitized_variables, sanitized_messages)),
            timestamp,
            timestamp,
        ),
    )
    return get_prompt_runtime_trace(conn, trace_id) or {}


def get_prompt_runtime_trace(conn: Any, trace_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT
            t.*,
            d.input_variables_json AS detail_input_variables_json,
            d.rendered_messages_json AS detail_rendered_messages_json,
            d.rendered_prompt AS detail_rendered_prompt,
            d.answer_text AS detail_answer_text,
            d.metadata_json AS detail_metadata_json
        FROM prompt_runtime_traces t
        LEFT JOIN prompt_runtime_trace_details d
          ON d.tenant_id = t.tenant_id AND d.trace_id = t.trace_id AND d.deleted = 0
        WHERE t.tenant_id = ? AND t.trace_id = ? AND t.deleted = 0
        """,
        (current_tenant_id(), trace_id),
    ).fetchone()
    return prompt_runtime_trace_from_row(dict(row)) if row else None


def list_prompt_runtime_traces(
    conn: Any,
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    allowed_sort: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    safe_page, safe_page_size, offset = pagination_bounds(page, page_size)
    order_by = trace_order_by(sort_by, sort_dir, allowed_sort)
    tenant_id = current_tenant_id()
    total = count_traces(conn, "tenant_id = ? AND deleted = 0", (tenant_id,))
    rows = conn.execute(
        f"""
        SELECT {TRACE_LIST_COLUMNS}
        FROM prompt_runtime_traces
        WHERE tenant_id = ? AND deleted = 0
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        (tenant_id, safe_page_size, offset),
    ).fetchall()
    return [prompt_runtime_trace_from_row(dict(row)) for row in rows], total


def list_ai_application_run_logs(
    conn: Any,
    app_key: str,
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    allowed_sort: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    safe_page, safe_page_size, offset = pagination_bounds(page, page_size)
    order_by = trace_order_by(sort_by, sort_dir, allowed_sort)
    tenant_id = current_tenant_id()
    normalized_app_key = normalize_key(app_key)
    total = count_traces(conn, "tenant_id = ? AND app_key = ? AND deleted = 0", (tenant_id, normalized_app_key))
    rows = conn.execute(
        f"""
        SELECT {TRACE_LIST_COLUMNS}
        FROM prompt_runtime_traces
        WHERE tenant_id = ? AND app_key = ? AND deleted = 0
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        (tenant_id, normalized_app_key, safe_page_size, offset),
    ).fetchall()
    return [ai_application_run_log_from_trace(dict(row)) for row in rows], total


def list_ai_capability_run_logs(
    conn: Any,
    capability_key: str,
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    allowed_sort: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    safe_page, safe_page_size, offset = pagination_bounds(page, page_size)
    order_by = trace_order_by(sort_by, sort_dir, allowed_sort)
    tenant_id = current_tenant_id()
    normalized_key = normalize_key(capability_key)
    total = count_traces(
        conn,
        "tenant_id = ? AND caller_type = 'ai_capability' AND caller_key = ? AND deleted = 0",
        (tenant_id, normalized_key),
    )
    rows = conn.execute(
        f"""
        SELECT {TRACE_LIST_COLUMNS}
        FROM prompt_runtime_traces
        WHERE tenant_id = ? AND caller_type = 'ai_capability' AND caller_key = ? AND deleted = 0
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        (tenant_id, normalized_key, safe_page_size, offset),
    ).fetchall()
    return [ai_application_run_log_from_trace(dict(row)) for row in rows], total


def list_platform_ai_capability_run_logs(
    conn: Any,
    capability_key: str,
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    allowed_sort: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    safe_page, safe_page_size, offset = pagination_bounds(page, page_size)
    order_by = trace_order_by(sort_by, sort_dir, allowed_sort)
    normalized_key = normalize_key(capability_key)
    total = count_traces(
        conn,
        "caller_type = 'ai_capability' AND caller_key = ? AND deleted = 0",
        (normalized_key,),
    )
    rows = conn.execute(
        f"""
        SELECT {TRACE_LIST_COLUMNS}
        FROM prompt_runtime_traces
        WHERE caller_type = 'ai_capability' AND caller_key = ? AND deleted = 0
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        (normalized_key, safe_page_size, offset),
    ).fetchall()
    return [ai_application_run_log_from_trace(dict(row)) for row in rows], total


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
    detail_input = row.get("detail_input_variables_json")
    detail_messages = row.get("detail_rendered_messages_json")
    detail_prompt = row.get("detail_rendered_prompt")
    detail_answer = row.get("detail_answer_text")
    detail_metadata = row.get("detail_metadata_json")
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
        "input_variables": parse_json_object(detail_input if detail_input is not None else row.get("input_variables_json")),
        "input_preview": parse_json_object(row.get("input_variables_json")),
        "rendered_messages": parse_json_list(detail_messages if detail_messages is not None else row.get("rendered_messages_json")),
        "rendered_prompt": str(detail_prompt if detail_prompt is not None else row.get("rendered_prompt") or ""),
        "rendered_prompt_preview": str(row.get("rendered_prompt") or ""),
        "answer": str(detail_answer if detail_answer is not None else row.get("answer_text") or ""),
        "answer_preview": str(row.get("answer_text") or ""),
        "usage": parse_json_object(row.get("usage_json")),
        "elapsed_ms": int(row.get("elapsed_ms") or 0),
        "error_code": str(row.get("error_code") or ""),
        "error_message": str(row.get("error_message") or ""),
        "request_id": str(row.get("request_id") or ""),
        "correlation_id": str(row.get("correlation_id") or ""),
        "metadata": parse_json_object(detail_metadata),
        "create_time": str(row.get("create_time") or ""),
    }


def pagination_bounds(page: int = 1, page_size: int = 20) -> tuple[int, int, int]:
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, min(100, int(page_size or 20)))
    return safe_page, safe_page_size, (safe_page - 1) * safe_page_size


def count_traces(conn: Any, where_sql: str, params: tuple[Any, ...]) -> int:
    row = conn.execute(
        f"SELECT COUNT(*) AS total FROM prompt_runtime_traces WHERE {where_sql}",
        params,
    ).fetchone()
    return int(row["total"] if row else 0)


def trace_order_by(sort_by: str | None, sort_dir: str | None, allowed_sort: dict[str, str] | None) -> str:
    sort = parse_sort_params(sort_by, sort_dir)
    return build_order_by(
        sort,
        allowed=allowed_sort or {},
        default=TRACE_DEFAULT_ORDER_BY,
        tie_breaker="id DESC",
    )


def trace_input_preview(value: dict[str, Any]) -> dict[str, Any]:
    return {key: preview_value(item) for key, item in value.items()}


def preview_value(value: Any) -> Any:
    if is_media_ref(value):
        return media_preview(value)
    if isinstance(value, dict):
        return {key: preview_value(item) for key, item in list(value.items())[:20]}
    if isinstance(value, list):
        return [preview_value(item) for item in value[:20]]
    if isinstance(value, str):
        return text_preview(value)
    return value


def sanitize_trace_value(value: Any) -> Any:
    if is_media_ref(value):
        return sanitize_media_ref(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        if "image_url" in value and isinstance(value.get("image_url"), dict):
            item = dict(value)
            image_url = dict(item["image_url"])
            image_url["url"] = sanitize_possible_data_url(image_url.get("url"), name="image")
            item["image_url"] = image_url
            return {key: sanitize_trace_value(item_value) for key, item_value in item.items()}
        if "input_audio" in value and isinstance(value.get("input_audio"), dict):
            item = dict(value)
            input_audio = dict(item["input_audio"])
            input_audio["data"] = sanitize_possible_data_url(input_audio.get("data"), name="audio")
            item["input_audio"] = input_audio
            return {key: sanitize_trace_value(item_value) for key, item_value in item.items()}
        return {key: sanitize_trace_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_trace_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_trace_value(item) for item in value]
    if isinstance(value, str):
        return sanitize_possible_data_url(value)
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def is_media_ref(value: Any) -> bool:
    return isinstance(value, dict) and str(value.get("type") or "").strip().lower() in {"image", "file", "audio", "video"}


def sanitize_media_ref(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": str(value.get("type") or "file"),
        "name": str(value.get("name") or ""),
        "mime_type": str(value.get("mime_type") or ""),
        "size": int(value.get("size") or value.get("size_bytes") or 0),
        "redacted": bool(value.get("redacted") or value.get("data_url")),
    }
    for key in ("file_ref", "file_id", "sha256", "preview_url", "storage_status", "reason", "text"):
        if value.get(key) not in (None, ""):
            result[key] = value.get(key)
    if "file_ref" not in result and value.get("file_id") not in (None, ""):
        result["file_ref"] = f"file_{value.get('file_id')}"
    if "storage_status" not in result:
        result["storage_status"] = "stored" if result.get("file_ref") else "unavailable"
    return result


def media_preview(value: dict[str, Any]) -> dict[str, Any]:
    result = sanitize_media_ref(value)
    result.pop("text", None)
    return result


def sanitize_possible_data_url(value: Any, *, name: str = "media") -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if is_data_url(text) or looks_like_large_base64(text):
        return {
            "redacted": True,
            "name": name,
            "reason": "binary_media_redacted",
            "size": len(text),
        }
    return text_preview(value)


def is_data_url(value: str) -> bool:
    return value.startswith(DATA_URL_PREFIXES) and ";base64," in value[:100]


def looks_like_large_base64(value: str) -> bool:
    if len(value) < 8192:
        return False
    sample = value[:256]
    return all(char.isalnum() or char in "+/=\n\r" for char in sample)


def text_preview(value: str, *, max_chars: int = 2000) -> str:
    text = str(value or "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"...[truncated {len(text) - max_chars} chars]"


def trace_metadata(payload: dict[str, Any], variables: dict[str, Any], messages: Any) -> dict[str, Any]:
    media = collect_media_refs({"variables": variables, "messages": messages})
    return {
        "media_count": len(media),
        "total_media_bytes": sum(int(item.get("size") or 0) for item in media),
        "has_redacted_media": any(bool(item.get("redacted")) for item in media),
        "storage_statuses": sorted({str(item.get("storage_status") or "unknown") for item in media}),
        "request_id": str(payload.get("request_id") or ""),
    }


def collect_media_refs(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if is_media_ref(value):
        result.append(sanitize_media_ref(value))
    elif isinstance(value, dict):
        for item in value.values():
            result.extend(collect_media_refs(item))
    elif isinstance(value, list):
        for item in value:
            result.extend(collect_media_refs(item))
    return result
