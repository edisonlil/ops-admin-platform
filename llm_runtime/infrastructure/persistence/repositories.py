from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from llm_runtime.domain.models import RoutingEntry, RoutingPolicy, RouteResolution
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


def bool_value(value: Any) -> bool:
    return bool(value)


def current_tenant_id() -> int:
    return int(current_tenant_scope().tenant_id)


def register_task(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    task_key = str(payload.get("task_key", "")).strip()
    if not task_key:
        raise ValueError("task_key is required")
    parts = task_key.split(".")
    context_key = str(payload.get("context_key") or (parts[0] if parts else "")).strip()
    scene_key = str(payload.get("scene_key") or (parts[1] if len(parts) > 1 else "")).strip()
    task_name = str(payload.get("task_name") or (parts[-1] if parts else "")).strip()
    row = conn.execute("SELECT * FROM llm_tasks WHERE tenant_id = ? AND task_key = ?", (tenant_id, task_key)).fetchone()
    timestamp = now_text()
    values = (
        context_key,
        scene_key,
        task_name,
        str(payload.get("display_name", "")).strip(),
        str(payload.get("description", "")).strip(),
        str(payload.get("owner_context") or context_key).strip(),
        1 if bool(payload.get("enabled", True)) else 0,
        timestamp,
    )
    if row:
        conn.execute(
            """
            UPDATE llm_tasks
            SET context_key = ?,
                scene_key = ?,
                task_name = ?,
                display_name = ?,
                description = ?,
                owner_context = ?,
                enabled = ?,
                updated_at = ?
            WHERE tenant_id = ? AND task_key = ?
            """,
            (*values, tenant_id, task_key),
        )
    else:
        conn.execute(
            """
            INSERT INTO llm_tasks (
                tenant_id, task_key, context_key, scene_key, task_name, display_name,
                description, owner_context, enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, task_key, *values, timestamp),
        )
    return get_task(conn, task_key) or {}


def get_task(conn: Any, task_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM llm_tasks WHERE tenant_id = ? AND task_key = ?",
        (current_tenant_id(), task_key),
    ).fetchone()
    return dict(row) if row else None


def list_tasks(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM llm_tasks WHERE tenant_id = ? ORDER BY context_key, scene_key, task_key",
        (current_tenant_id(),),
    ).fetchall()
    return [dict(row) for row in rows]


def upsert_provider(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    provider_key = str(payload.get("provider_key") or payload.get("provider", "")).strip().lower()
    if not provider_key:
        raise ValueError("provider_key is required")
    existing = conn.execute(
        "SELECT * FROM llm_providers WHERE tenant_id = ? AND provider_key = ?",
        (tenant_id, provider_key),
    ).fetchone()
    api_key = resolve_secret(payload, dict(existing) if existing else None)
    timestamp = now_text()
    values = (
        str(payload.get("display_name") or provider_key).strip(),
        str(payload.get("base_url", "")).strip(),
        api_key,
        str(payload.get("auth_type") or "bearer").strip().lower(),
        json_text(payload.get("extra_headers")),
        json_text(payload.get("extra_body")),
        1 if bool(payload.get("enabled", True)) else 0,
        timestamp,
    )
    if existing:
        conn.execute(
            """
            UPDATE llm_providers
            SET display_name = ?,
                base_url = ?,
                api_key = ?,
                auth_type = ?,
                extra_headers = ?,
                extra_body = ?,
                enabled = ?,
                updated_at = ?
            WHERE tenant_id = ? AND provider_key = ?
            """,
            (*values, tenant_id, provider_key),
        )
    else:
        conn.execute(
            """
            INSERT INTO llm_providers (
                tenant_id, provider_key, display_name, base_url, api_key, auth_type,
                extra_headers, extra_body, enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, provider_key, *values, timestamp),
        )
    return public_provider(get_provider(conn, provider_key) or {})


def resolve_secret(payload: dict[str, Any], existing: dict[str, Any] | None) -> str:
    if bool(payload.get("clear_api_key", False)):
        return ""
    api_key = str(payload.get("api_key", "")).strip()
    if api_key:
        return api_key
    return str((existing or {}).get("api_key", "") or "")


def get_provider(conn: Any, provider_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM llm_providers WHERE tenant_id = ? AND provider_key = ?",
        (current_tenant_id(), provider_key),
    ).fetchone()
    return dict(row) if row else None


def list_providers(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM llm_providers WHERE tenant_id = ? ORDER BY provider_key",
        (current_tenant_id(),),
    ).fetchall()
    return [public_provider(dict(row)) for row in rows]


def public_provider(row: dict[str, Any]) -> dict[str, Any]:
    api_key = str(row.get("api_key", "") or "")
    return {
        "provider_key": str(row.get("provider_key", "")),
        "display_name": str(row.get("display_name", "")),
        "base_url": str(row.get("base_url", "")),
        "auth_type": str(row.get("auth_type", "bearer")),
        "extra_headers": parse_json_object(row.get("extra_headers")),
        "extra_body": parse_json_object(row.get("extra_body")),
        "enabled": bool_value(row.get("enabled", True)),
        "api_key_configured": bool(api_key),
        "api_key_mask": mask_secret(api_key),
        "updated_at": str(row.get("updated_at", "")),
    }


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def upsert_model(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    model_key = str(payload.get("model_key", "")).strip().lower()
    provider_key = str(payload.get("provider_key", "")).strip().lower()
    model_name = str(payload.get("model_name") or payload.get("model", "")).strip()
    if not model_key:
        raise ValueError("model_key is required")
    if not provider_key:
        raise ValueError("provider_key is required")
    if not model_name:
        raise ValueError("model_name is required")
    timestamp = now_text()
    values = (
        provider_key,
        model_name,
        str(payload.get("display_name") or model_name).strip(),
        json_text(payload.get("capabilities")),
        payload.get("context_window"),
        1 if bool(payload.get("enabled", True)) else 0,
        timestamp,
    )
    existing = conn.execute(
        "SELECT * FROM llm_models WHERE tenant_id = ? AND model_key = ?",
        (tenant_id, model_key),
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE llm_models
            SET provider_key = ?,
                model_name = ?,
                display_name = ?,
                capabilities = ?,
                context_window = ?,
                enabled = ?,
                updated_at = ?
            WHERE tenant_id = ? AND model_key = ?
            """,
            (*values, tenant_id, model_key),
        )
    else:
        conn.execute(
            """
            INSERT INTO llm_models (
                tenant_id, model_key, provider_key, model_name, display_name, capabilities,
                context_window, enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, model_key, *values, timestamp),
        )
    return get_model(conn, model_key) or {}


def get_model(conn: Any, model_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM llm_models WHERE tenant_id = ? AND model_key = ?",
        (current_tenant_id(), model_key),
    ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["capabilities"] = parse_json_object(result.get("capabilities"))
    result["enabled"] = bool_value(result.get("enabled", True))
    return result


def list_models(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM llm_models WHERE tenant_id = ? ORDER BY provider_key, model_key",
        (current_tenant_id(),),
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["capabilities"] = parse_json_object(item.get("capabilities"))
        item["enabled"] = bool_value(item.get("enabled", True))
        result.append(item)
    return result


def upsert_routing_policy(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = current_tenant_id()
    route_key = str(payload.get("route_key", "")).strip()
    if not route_key:
        raise ValueError("route_key is required")
    timestamp = now_text()
    existing = conn.execute(
        "SELECT * FROM llm_routing_policies WHERE tenant_id = ? AND route_key = ?",
        (tenant_id, route_key),
    ).fetchone()
    values = (
        str(payload.get("display_name") or route_key).strip(),
        str(payload.get("strategy") or "priority").strip().lower(),
        1 if bool(payload.get("enabled", True)) else 0,
        timestamp,
    )
    if existing:
        conn.execute(
            """
            UPDATE llm_routing_policies
            SET display_name = ?,
                strategy = ?,
                enabled = ?,
                updated_at = ?
            WHERE tenant_id = ? AND route_key = ?
            """,
            (*values, tenant_id, route_key),
        )
        policy_id = int(dict(existing)["id"])
    else:
        conn.execute(
            """
            INSERT INTO llm_routing_policies (tenant_id, route_key, display_name, strategy, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, route_key, *values, timestamp),
        )
        policy_id = int(dict(conn.execute(
            "SELECT id FROM llm_routing_policies WHERE tenant_id = ? AND route_key = ?",
            (tenant_id, route_key),
        ).fetchone())["id"])

    if "entries" in payload:
        conn.execute(
            "DELETE FROM llm_routing_policy_entries WHERE tenant_id = ? AND policy_id = ?",
            (tenant_id, policy_id),
        )
        for entry in payload.get("entries") or []:
            insert_policy_entry(conn, policy_id, entry)

    policy = get_policy(conn, route_key)
    return policy_to_dict(policy) if policy else {}


def insert_policy_entry(conn: Any, policy_id: int, payload: dict[str, Any]) -> None:
    tenant_id = current_tenant_id()
    model_key = str(payload.get("model_key", "")).strip().lower()
    if not model_key:
        raise ValueError("policy entry model_key is required")
    timestamp = now_text()
    conn.execute(
        """
        INSERT INTO llm_routing_policy_entries (
            tenant_id, policy_id, model_key, priority, temperature, timeout_seconds,
            max_retries, response_format, extra_body, enabled, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            policy_id,
            model_key,
            int(payload.get("priority", 100)),
            float(payload.get("temperature", 0.1)),
            float(payload.get("timeout_seconds", 120)),
            int(payload.get("max_retries", 0)),
            str(payload.get("response_format") or "text").strip().lower(),
            json_text(payload.get("extra_body")),
            1 if bool(payload.get("enabled", True)) else 0,
            timestamp,
            timestamp,
        ),
    )


def get_policy(conn: Any, route_key: str) -> RoutingPolicy | None:
    tenant_id = current_tenant_id()
    policy_row = conn.execute(
        "SELECT * FROM llm_routing_policies WHERE tenant_id = ? AND route_key = ? AND enabled = TRUE",
        (tenant_id, route_key),
    ).fetchone()
    if not policy_row:
        return None
    policy = dict(policy_row)
    entry_rows = conn.execute(
        """
        SELECT
            e.*,
            m.provider_key,
            m.model_name,
            m.capabilities,
            p.display_name AS provider_display_name,
            p.base_url,
            p.api_key,
            p.extra_body AS provider_extra_body
        FROM llm_routing_policy_entries e
        JOIN llm_models m ON m.model_key = e.model_key AND m.tenant_id = e.tenant_id
        JOIN llm_providers p ON p.provider_key = m.provider_key AND p.tenant_id = e.tenant_id
        WHERE e.policy_id = ?
          AND e.tenant_id = ?
          AND m.tenant_id = ?
          AND e.enabled = TRUE
          AND m.enabled = TRUE
          AND p.enabled = TRUE
        ORDER BY e.priority ASC, e.id ASC
        """,
        (policy["id"], tenant_id, tenant_id),
    ).fetchall()
    entries = [entry_from_row(dict(row)) for row in entry_rows]
    return RoutingPolicy(
        id=int(policy["id"]),
        route_key=str(policy["route_key"]),
        display_name=str(policy.get("display_name", "")),
        strategy=str(policy.get("strategy", "priority")),
        entries=entries,
    )


def entry_for_model(conn: Any, model_key: str) -> RoutingEntry | None:
    tenant_id = current_tenant_id()
    lookup_key = model_key.strip().lower()
    row = conn.execute(
        """
        SELECT
            m.id AS model_id,
            m.model_key,
            m.provider_key,
            m.model_name,
            m.capabilities,
            p.display_name AS provider_display_name,
            p.base_url,
            p.api_key,
            p.extra_body AS provider_extra_body
        FROM llm_models m
        JOIN llm_providers p ON p.provider_key = m.provider_key AND p.tenant_id = m.tenant_id
        WHERE m.tenant_id = ?
          AND (m.model_key = ? OR m.model_name = ?)
          AND m.enabled = TRUE
          AND p.enabled = TRUE
        ORDER BY CASE WHEN m.model_key = ? THEN 0 ELSE 1 END, m.id ASC
        LIMIT 1
        """,
        (tenant_id, lookup_key, model_key.strip(), lookup_key),
    ).fetchone()
    if not row:
        return None
    payload = dict(row)
    return RoutingEntry(
        id=0,
        policy_id=0,
        model_key=str(payload["model_key"]),
        provider_key=str(payload["provider_key"]),
        model_name=str(payload["model_name"]),
        provider_display_name=str(payload.get("provider_display_name") or payload.get("provider_key") or ""),
        base_url=str(payload.get("base_url", "") or ""),
        api_key=str(payload.get("api_key", "") or ""),
        provider_extra_body=parse_json_object(payload.get("provider_extra_body")),
        model_capabilities=parse_json_object(payload.get("capabilities")),
        priority=1,
        temperature=0.1,
        timeout_seconds=120.0,
        max_retries=0,
        response_format="text",
        extra_body={},
        enable_think_output=bool(parse_json_object(payload.get("provider_extra_body")).get("enable_think_output", False)),
    )


def entry_from_row(row: dict[str, Any]) -> RoutingEntry:
    provider_extra_body = parse_json_object(row.get("provider_extra_body"))
    entry_extra_body = parse_json_object(row.get("extra_body"))
    enable_think_output = bool(
        entry_extra_body.get("enable_think_output", provider_extra_body.get("enable_think_output", False))
    )
    return RoutingEntry(
        id=int(row["id"]),
        policy_id=int(row["policy_id"]),
        model_key=str(row["model_key"]),
        provider_key=str(row["provider_key"]),
        model_name=str(row["model_name"]),
        provider_display_name=str(row.get("provider_display_name") or row.get("provider_key") or ""),
        base_url=str(row.get("base_url", "") or ""),
        api_key=str(row.get("api_key", "") or ""),
        provider_extra_body=provider_extra_body,
        model_capabilities=parse_json_object(row.get("capabilities")),
        priority=int(row.get("priority", 100)),
        temperature=float(row.get("temperature") if row.get("temperature") is not None else 0.1),
        timeout_seconds=float(row.get("timeout_seconds") if row.get("timeout_seconds") is not None else 120),
        max_retries=int(row.get("max_retries", 0)),
        response_format=str(row.get("response_format") or "text"),
        extra_body=entry_extra_body,
        enable_think_output=enable_think_output,
    )


def resolve_route(conn: Any, task_key: str) -> RouteResolution | None:
    for route_key in route_candidates(task_key):
        policy = get_policy(conn, route_key)
        if policy and policy.entries:
            return RouteResolution(task_key=task_key, route_key=route_key, policy=policy)
    return None


def route_candidates(task_key: str) -> list[str]:
    parts = [part for part in task_key.strip().split(".") if part]
    candidates: list[str] = []
    if parts:
        candidates.append(".".join(parts))
    if len(parts) >= 2:
        candidates.append(".".join([*parts[:-1], "default"]))
    if parts:
        candidates.append(f"{parts[0]}.default")
    candidates.append("default")
    result: list[str] = []
    for candidate in candidates:
        if candidate not in result:
            result.append(candidate)
    return result


def list_policies(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM llm_routing_policies WHERE tenant_id = ? ORDER BY route_key",
        (current_tenant_id(),),
    ).fetchall()
    result = []
    for row in rows:
        policy = get_policy(conn, str(dict(row)["route_key"]))
        if policy:
            result.append(policy_to_dict(policy))
        else:
            item = dict(row)
            item["enabled"] = bool_value(item.get("enabled", True))
            item["entries"] = []
            result.append(item)
    return result


def policy_to_dict(policy: RoutingPolicy) -> dict[str, Any]:
    return {
        "id": policy.id,
        "route_key": policy.route_key,
        "display_name": policy.display_name,
        "strategy": policy.strategy,
        "entries": [
            {
                "id": entry.id,
                "policy_id": entry.policy_id,
                "model_key": entry.model_key,
                "provider_key": entry.provider_key,
                "model_name": entry.model_name,
                "priority": entry.priority,
                "temperature": entry.temperature,
                "timeout_seconds": entry.timeout_seconds,
                "max_retries": entry.max_retries,
                "response_format": entry.response_format,
                "extra_body": entry.extra_body,
                "enabled": True,
            }
            for entry in policy.entries
        ],
    }


def record_call_log(conn: Any, payload: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO llm_call_logs (
            tenant_id, task_key, route_key, policy_id, entry_id, provider_key, model_key,
            model_name, status, is_fallback, elapsed_ms, prompt_tokens,
            completion_tokens, total_tokens, error_code, error_message,
            request_id, correlation_id, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            current_tenant_id(),
            str(payload.get("task_key", "")),
            str(payload.get("route_key", "")),
            payload.get("policy_id"),
            payload.get("entry_id"),
            str(payload.get("provider_key", "")),
            str(payload.get("model_key", "")),
            str(payload.get("model_name", "")),
            str(payload.get("status", "")),
            1 if bool(payload.get("is_fallback", False)) else 0,
            int(payload.get("elapsed_ms", 0) or 0),
            int(payload.get("prompt_tokens", 0) or 0),
            int(payload.get("completion_tokens", 0) or 0),
            int(payload.get("total_tokens", 0) or 0),
            str(payload.get("error_code", "")),
            str(payload.get("error_message", ""))[:1000],
            str(payload.get("request_id", "")),
            str(payload.get("correlation_id", "")),
            now_text(),
        ),
    )


def list_call_logs(conn: Any, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM llm_call_logs
        WHERE tenant_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (current_tenant_id(), limit),
    ).fetchall()
    return [dict(row) for row in rows]
