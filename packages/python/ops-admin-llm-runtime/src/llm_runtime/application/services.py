from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from fastapi import HTTPException

from llm_runtime.domain.events import llm_runtime_settings_updated
from llm_runtime.infrastructure.persistence.bootstrap import require_llm_schema
from framework.llm_core import CommandLLMClient, LLMClient, LLMResponse, MiniMaxLLMClient, OpenAICompatibleLLMClient
from llm_runtime.application import gateway
from system.application.database import connect, resolve_database_url, resolve_db_path
from system.application.event_bus import publish_event
from system.application.tenancy import current_tenant_scope
from system.interfaces.http import current_request_id
from llm_runtime.infrastructure.persistence import repositories


def require_database() -> str | Path:
    database_url = resolve_database_url()
    if database_url:
        return database_url
    db_path = resolve_db_path()
    if not db_path.exists():
        raise HTTPException(status_code=503, detail=f"database not found: {db_path}")
    return db_path


def env_value(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def get_llm_config() -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            require_llm_config_schema(conn)
            if not table_exists(conn, "llm_configs"):
                return default_llm_config_response(source="database")
            row = active_llm_config_row(conn)
    except (sqlite3.Error, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    if not row:
        return default_llm_config_response(source="database")
    return llm_config_response_from_row(row)


def save_llm_config(payload: dict[str, Any]) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            require_llm_config_schema(conn)
            existing = active_llm_config_row(conn)
            now = datetime.now().isoformat(timespec="microseconds")
            api_key = resolve_saved_api_key(payload, existing)
            enable_think_output = bool(payload.get("enable_think_output", False))
            extra_body = payload.get("extra_body")
            if not isinstance(extra_body, dict):
                raise HTTPException(status_code=422, detail="extra_body must be an object")
            extra_body = dict(extra_body)
            extra_body["enable_think_output"] = enable_think_output
            if enable_think_output:
                extra_body["reasoning_split"] = True
            else:
                extra_body.pop("reasoning_split", None)
            tenant_id = current_tenant_id()
            values = (
                tenant_id,
                str(payload.get("provider", "minimax")).strip().lower(),
                str(payload.get("model", "")).strip(),
                str(payload.get("base_url", "")).strip(),
                api_key,
                str(payload.get("command", "")).strip(),
                float(payload.get("timeout_seconds", 120)),
                float(payload.get("temperature", 0.1)),
                json.dumps(extra_body, ensure_ascii=False),
                1 if bool(payload.get("enabled", True)) else 0,
                now,
            )
            if existing:
                conn.execute(
                    """
                    UPDATE llm_configs
                    SET provider = ?,
                        model = ?,
                        base_url = ?,
                        api_key = ?,
                        command = ?,
                        timeout_seconds = ?,
                        temperature = ?,
                        extra_body = ?,
                        is_active = ?,
                        update_time = ?
                    WHERE id = ?
                      AND tenant_id = ?
                    """,
                    (*values[1:], existing["id"], tenant_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO llm_configs (
                        tenant_id, provider, model, base_url, api_key, command,
                        timeout_seconds, temperature, extra_body, is_active,
                        create_time, update_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*values, now),
                )
            row = active_llm_config_row(conn)
    except HTTPException:
        raise
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    if not row:
        return default_llm_config_response(source="database")
    result = llm_config_response_from_row(row)
    publish_event(
        llm_runtime_settings_updated(
            str(result.get("provider", "")),
            bool(result.get("enabled", False)),
            correlation_id=current_request_id(),
        )
    )
    return result


def list_providers() -> dict[str, Any]:
    return list_resource(repositories.list_providers)


def save_provider(payload: dict[str, Any]) -> dict[str, Any]:
    return write_resource(lambda conn: repositories.upsert_provider(conn, payload))


def list_models() -> dict[str, Any]:
    return list_resource(repositories.list_models)


def save_model(payload: dict[str, Any]) -> dict[str, Any]:
    return write_resource(lambda conn: repositories.upsert_model(conn, payload))


def list_tasks() -> dict[str, Any]:
    return list_resource(repositories.list_tasks)


def register_task(payload: dict[str, Any]) -> dict[str, Any]:
    return write_resource(lambda conn: repositories.register_task(conn, payload))


def list_routing_policies() -> dict[str, Any]:
    return list_resource(repositories.list_policies)


def save_routing_policy(payload: dict[str, Any]) -> dict[str, Any]:
    return write_resource(lambda conn: repositories.upsert_routing_policy(conn, payload))


def list_call_logs(limit: int = 50) -> dict[str, Any]:
    return list_resource(lambda conn: repositories.list_call_logs(conn, limit=limit))


def list_openai_models() -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            require_llm_config_schema(conn)
            models = repositories.list_models(conn)
            policies = repositories.list_policies(conn)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    items = [
        {
            "id": item["model_key"],
            "object": "model",
            "created": 0,
            "owned_by": item.get("provider_key", ""),
            "display_name": item.get("display_name", "") or item.get("model_name", ""),
            "model_name": item.get("model_name", ""),
            "kind": "model",
        }
        for item in models
        if item.get("enabled", True)
    ]
    items.extend(
        {
            "id": item["route_key"],
            "object": "model",
            "created": 0,
            "owned_by": "llm_runtime",
            "display_name": item.get("display_name", "") or item.get("route_key", ""),
            "model_name": item.get("route_key", ""),
            "kind": "route",
        }
        for item in policies
        if item.get("enabled", True)
    )
    return {"object": "list", "data": items}


def create_openai_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return gateway.chat_completions(
            model=str(payload.get("model", "")).strip(),
            messages=payload.get("messages") or [],
            temperature=payload.get("temperature"),
            response_format=payload.get("response_format") if isinstance(payload.get("response_format"), dict) else None,
            extra_body={
                key: value
                for key, value in payload.items()
                if key not in {"model", "messages", "temperature", "response_format", "enable_think_output", "stream"}
            },
            enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
            correlation_id=current_request_id(),
        )
    except gateway.LLMRoutingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def create_openai_chat_completion_stream(payload: dict[str, Any]) -> list[str]:
    try:
        return gateway.stream_chat_completions(
            model=str(payload.get("model", "")).strip(),
            messages=payload.get("messages") or [],
            temperature=payload.get("temperature"),
            response_format=payload.get("response_format") if isinstance(payload.get("response_format"), dict) else None,
            extra_body={
                key: value
                for key, value in payload.items()
                if key not in {"model", "messages", "temperature", "response_format", "enable_think_output", "stream"}
            },
            enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
            correlation_id=current_request_id(),
        )
    except gateway.LLMRoutingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def openai_chat_completion_stream_events(response: dict[str, Any]) -> list[str]:
    return gateway.openai_chat_completion_stream_events(response)


def list_resource(loader: Any) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            require_llm_config_schema(conn)
            items = loader(conn)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    return {
        "items": items,
        "pagination": {"page": 1, "page_size": len(items), "total": len(items)},
    }


def write_resource(writer: Any) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            require_llm_config_schema(conn)
            return writer(conn)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (sqlite3.Error, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def runtime_llm_config(database_target: str | Path) -> dict[str, Any] | None:
    """Return the active model runtime configuration for this system."""
    try:
        with connect(database_target, readonly=True) as conn:
            require_llm_config_schema(conn)
            if not table_exists(conn, "llm_configs"):
                return new_runtime_config_from_database(database_target, conn)
            new_config = new_runtime_config_from_database(database_target, conn)
            row = active_llm_config_row(conn)
    except (sqlite3.Error, RuntimeError):
        return None
    if not row:
        return new_config or {}
    if not bool(row.get("is_active", True)):
        return new_config or {}
    config = llm_runtime_config_from_row(row)
    if new_config:
        config.update(new_config)
    return config


def new_runtime_config_from_database(database_target: str | Path, conn: Any) -> dict[str, Any] | None:
    if not table_exists(conn, "llm_routing_policies"):
        return None
    return {
        "routing_enabled": True,
        "database_target": str(database_target),
    }


def require_llm_config_schema(conn: Any) -> None:
    require_llm_schema(conn)


def active_llm_config_row(conn: Any) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM llm_configs
        WHERE tenant_id = ?
        ORDER BY is_active DESC, update_time DESC, id DESC
        LIMIT 1
        """,
        (current_tenant_id(),),
    ).fetchone()
    return dict(row) if row else None


def current_tenant_id() -> int:
    return int(current_tenant_scope().tenant_id)


def resolve_saved_api_key(payload: dict[str, Any], existing: dict[str, Any] | None) -> str:
    if bool(payload.get("clear_api_key", False)):
        return ""
    api_key = str(payload.get("api_key", "")).strip()
    if api_key:
        return api_key
    return str((existing or {}).get("api_key", "") or "")


def llm_runtime_config_from_row(row: dict[str, Any]) -> dict[str, Any]:
    provider = str(row.get("provider", "") or "minimax").strip().lower()
    config: dict[str, Any] = {
        "provider": provider,
    }
    command = str(row.get("command", "") or "").strip()
    if command:
        config["command"] = command
    extra_body = parse_extra_body(row.get("extra_body"))
    provider_config = {
        "api_key": str(row.get("api_key", "") or "").strip(),
        "model": str(row.get("model", "") or "").strip(),
        "base_url": str(row.get("base_url", "") or "").strip(),
        "timeout_seconds": row.get("timeout_seconds") or 120,
        "temperature": row.get("temperature") if row.get("temperature") is not None else 0.1,
        "extra_body": extra_body,
        "enable_think_output": resolve_enable_think_output(extra_body),
    }
    config[provider] = provider_config
    return config


def llm_config_response_from_row(row: dict[str, Any]) -> dict[str, Any]:
    api_key = str(row.get("api_key", "") or "")
    extra_body = parse_extra_body(row.get("extra_body"))
    return {
        "provider": str(row.get("provider", "") or "minimax"),
        "model": str(row.get("model", "") or ""),
        "base_url": str(row.get("base_url", "") or ""),
        "command": str(row.get("command", "") or ""),
        "timeout_seconds": float(row.get("timeout_seconds") or 120),
        "temperature": float(row.get("temperature") if row.get("temperature") is not None else 0.1),
        "extra_body": extra_body,
        "enable_think_output": resolve_enable_think_output(extra_body),
        "enabled": bool(row.get("is_active", True)),
        "api_key_configured": bool(api_key),
        "api_key_mask": mask_secret(api_key),
        "update_time": str(row.get("update_time", "") or ""),
        "source": "database",
    }


def default_llm_config_response(*, source: str) -> dict[str, Any]:
    return {
        "provider": "minimax",
        "model": "MiniMax-M2.7-highspeed",
        "base_url": "https://api.minimaxi.com/v1",
        "command": "",
        "timeout_seconds": 120,
        "temperature": 0.1,
        "extra_body": {},
        "enable_think_output": False,
        "enabled": False,
        "api_key_configured": False,
        "api_key_mask": "",
        "update_time": "",
        "source": source,
    }


def parse_extra_body(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_enable_think_output(extra_body: dict[str, Any]) -> bool:
    value = extra_body.get("enable_think_output", False)
    return bool(value)


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def table_exists(conn: Any, table_name: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table_name,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
    return bool(row)


def build_llm_client(
    *,
    role: str = "default",
    command: str | None = None,
    config: dict[str, Any] | None = None,
    env_prefixes: Sequence[str] = (),
) -> LLMClient | None:
    """Resolve a client from generic config plus optional caller env prefixes.

    ``env_prefixes`` lets business adapters preserve their own compatibility
    environment variables without baking those names into the runtime context.
    """
    config = config or {}
    role_config = _role_config(config, role)

    task_key = _config_str(role_config, "task_key") or _config_str(config.get("role_task_map", {}) if isinstance(config.get("role_task_map"), dict) else {}, role)
    if not task_key and "." in role:
        task_key = role
    if config.get("routing_enabled") and task_key:
        route_database_target = str(config["database_target"]) if config.get("database_target") else None
        if route_available(route_database_target, task_key):
            return RoutedLLMClient(
                task_key=task_key,
                database_target=route_database_target,
            )

    command = command or _env_by_suffix(env_prefixes, "LLM_COMMAND") or _config_str(role_config, "command") or _config_str(
        config, "command"
    )
    llm_think_output_env = _env_bool_by_suffix(env_prefixes, "LLM_ENABLE_THINK_OUTPUT")
    enable_think_output = (
        llm_think_output_env
        if llm_think_output_env is not None
        else _config_bool(role_config, config, key="enable_think_output")
    )
    if command:
        return CommandLLMClient(command, enable_think_output=enable_think_output)

    provider = (
        _env_by_suffix(env_prefixes, "LLM_PROVIDER")
        or env_value("LLM_PROVIDER")
        or _config_str(role_config, "provider")
        or _config_str(config, "provider")
        or ""
    ).lower()
    minimax_config = _provider_config(config, role_config, "minimax")
    api_key = _env_by_suffix(env_prefixes, "MINIMAX_API_KEY") or env_value("MINIMAX_API_KEY") or _config_str(
        minimax_config, "api_key"
    )
    if provider == "minimax" or api_key:
        if not api_key:
            raise RuntimeError("MiniMax LLM requires an API key")
        return MiniMaxLLMClient(
            api_key=api_key,
            model=_env_by_suffix(env_prefixes, "MINIMAX_MODEL")
            or _config_str(minimax_config, "model")
            or "MiniMax-M2.7",
            base_url=_env_by_suffix(env_prefixes, "MINIMAX_BASE_URL")
            or _config_str(minimax_config, "base_url")
            or "https://api.minimaxi.com/v1",
            timeout_seconds=float(
                _env_by_suffix(env_prefixes, "LLM_TIMEOUT_SECONDS")
                or _config_value(minimax_config, "timeout_seconds")
                or "120"
            ),
            temperature=float(
                _env_by_suffix(env_prefixes, "LLM_TEMPERATURE")
                or _config_value(minimax_config, "temperature")
                or "0.1"
            ),
            extra_body=_json_env_by_suffix(env_prefixes, "MINIMAX_EXTRA_BODY")
            or _config_dict(minimax_config, "extra_body")
            or {},
            enable_think_output=resolve_minimax_think_output(env_prefixes, minimax_config, config),
        )

    openai_client = openai_compatible_client(provider=provider, config=config, role_config=role_config, env_prefixes=env_prefixes)
    if openai_client:
        return openai_client

    return None


class RoutedLLMClient:
    def __init__(self, *, task_key: str, database_target: str | Path | None = None) -> None:
        self.task_key = task_key
        self.database_target = database_target

    def generate_response(self, prompt: str, *, enable_think_output: bool | None = None) -> LLMResponse:
        return gateway.generate(
            task_key=self.task_key,
            prompt=prompt,
            database_target_override=self.database_target,
            correlation_id=current_request_id(),
        )

    def generate(self, prompt: str, *, enable_think_output: bool | None = None) -> str:
        return self.generate_response(prompt, enable_think_output=enable_think_output).content


def route_available(database_target: str | Path | None, task_key: str) -> bool:
    if not database_target:
        return False
    try:
        with connect(database_target, readonly=True) as conn:
            if not table_exists(conn, "llm_routing_policies"):
                return False
            return repositories.resolve_route(conn, task_key) is not None
    except (sqlite3.Error, RuntimeError):
        return False


OPENAI_COMPATIBLE_PROVIDERS = {"dashscope", "siliconflow", "openai_compatible", "openai"}


def openai_compatible_client(
    *,
    provider: str,
    config: dict[str, Any],
    role_config: dict[str, Any],
    env_prefixes: Sequence[str],
) -> LLMClient | None:
    if provider not in OPENAI_COMPATIBLE_PROVIDERS:
        return None
    provider_config = _provider_config(config, role_config, provider)
    api_key = (
        _env_by_suffix(env_prefixes, f"{provider.upper()}_API_KEY")
        or env_value(f"{provider.upper()}_API_KEY")
        or _config_str(provider_config, "api_key")
    )
    if not api_key:
        raise RuntimeError(f"{provider} LLM requires an API key")
    model = (
        _env_by_suffix(env_prefixes, f"{provider.upper()}_MODEL")
        or env_value(f"{provider.upper()}_MODEL")
        or _config_str(provider_config, "model")
        or _config_str(config, "model")
    )
    if not model:
        raise RuntimeError(f"{provider} LLM requires a model")
    base_url = (
        _env_by_suffix(env_prefixes, f"{provider.upper()}_BASE_URL")
        or env_value(f"{provider.upper()}_BASE_URL")
        or _config_str(provider_config, "base_url")
    )
    if not base_url:
        raise RuntimeError(f"{provider} LLM requires a base_url")
    return OpenAICompatibleLLMClient(
        provider_name=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=float(
            _env_by_suffix(env_prefixes, "LLM_TIMEOUT_SECONDS")
            or _config_value(provider_config, "timeout_seconds")
            or "120"
        ),
        temperature=float(
            _env_by_suffix(env_prefixes, "LLM_TEMPERATURE")
            or _config_value(provider_config, "temperature")
            or "0.1"
        ),
        extra_body=_json_env_by_suffix(env_prefixes, f"{provider.upper()}_EXTRA_BODY")
        or _config_dict(provider_config, "extra_body")
        or {},
        enable_think_output=_config_bool(provider_config, config, key="enable_think_output"),
    )


def _env_by_suffix(prefixes: Sequence[str], suffix: str) -> str | None:
    for prefix in prefixes:
        value = env_value(f"{prefix}_{suffix}")
        if value:
            return value
    return None


def _json_env_by_suffix(prefixes: Sequence[str], suffix: str) -> dict[str, Any]:
    value = _env_by_suffix(prefixes, suffix)
    if not value:
        return {}
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{suffix} must be a JSON object")
    return payload


def _env_bool_by_suffix(prefixes: Sequence[str], suffix: str) -> bool | None:
    value = _env_by_suffix(prefixes, suffix)
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_minimax_think_output(
    env_prefixes: Sequence[str],
    minimax_config: dict[str, Any],
    config: dict[str, Any],
) -> bool:
    minimax_env = _env_bool_by_suffix(env_prefixes, "MINIMAX_ENABLE_THINK_OUTPUT")
    if minimax_env is not None:
        return minimax_env
    llm_env = _env_bool_by_suffix(env_prefixes, "LLM_ENABLE_THINK_OUTPUT")
    if llm_env is not None:
        return llm_env
    return _config_bool(minimax_config, config, key="enable_think_output")


def _role_config(config: dict[str, Any], role: str) -> dict[str, Any]:
    roles = config.get("roles", {})
    if not isinstance(roles, dict):
        return {}
    role_config = roles.get(role, {})
    return role_config if isinstance(role_config, dict) else {}


def _provider_config(config: dict[str, Any], role_config: dict[str, Any], provider: str) -> dict[str, Any]:
    base = config.get(provider, {})
    role_override = role_config.get(provider, {})
    result: dict[str, Any] = {}
    if isinstance(base, dict):
        result.update(base)
    if isinstance(role_override, dict):
        result.update(role_override)
    return result


def _config_value(config: dict[str, Any], key: str) -> Any:
    value = config.get(key)
    return value if value is not None else None


def _config_str(config: dict[str, Any], key: str) -> str | None:
    value = _config_value(config, key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _config_dict(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key)
    return value if isinstance(value, dict) else {}


def _config_bool(*configs: dict[str, Any], key: str) -> bool:
    for config in configs:
        if key in config:
            return bool(config.get(key))
        extra_body = config.get("extra_body")
        if isinstance(extra_body, dict) and key in extra_body:
            return bool(extra_body.get(key))
    return False
