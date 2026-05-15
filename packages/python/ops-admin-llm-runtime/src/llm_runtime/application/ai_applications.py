from __future__ import annotations

import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ai_assets.application import services as prompt_asset_services
from llm_runtime.application import gateway
from llm_runtime.infrastructure.persistence import repositories
from llm_runtime.infrastructure.persistence.bootstrap import require_llm_schema
from system.application.database import connect
from system.interfaces.http import current_request_id

from .services import require_database


VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
MEDIA_VARIABLE_TYPES = {"image", "file", "audio", "video"}


def studio_overview() -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            require_llm_schema(conn)
            apps = repositories.list_ai_applications(conn)
            quota = repositories.get_tenant_ai_quota(conn)
            traces = repositories.list_prompt_runtime_traces(conn, limit=10)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    return {
        "stats": {
            "applications": len(apps),
            "published_applications": sum(1 for item in apps if item.get("status") == "published"),
            "recent_runs": len(traces),
        },
        "quota": quota,
        "applications": apps[:8],
        "recent_traces": traces,
        "app_types": [
            {"type": "single_turn_generation", "label": "单轮生成", "enabled": True},
            {"type": "chat", "label": "多轮对话", "enabled": False},
            {"type": "workflow", "label": "Workflow", "enabled": False},
            {"type": "agent", "label": "Agent", "enabled": False},
        ],
    }


def list_ai_applications() -> dict[str, Any]:
    return read_list(lambda conn: repositories.list_ai_applications(conn))


def get_ai_application(app_key: str) -> dict[str, Any]:
    app = read_one(lambda conn: repositories.get_ai_application(conn, app_key))
    if not app:
        raise HTTPException(status_code=404, detail="AI application not found")
    return app


def save_ai_application(payload: dict[str, Any]) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            require_llm_schema(conn)
            existing = repositories.get_ai_application(conn, str(payload.get("app_key") or ""))
            if not existing:
                enforce_application_quota(conn)
            normalize_single_turn_payload(payload)
            return repositories.upsert_ai_application(conn, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (sqlite3.Error, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def publish_ai_application(app_key: str) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            require_llm_schema(conn)
            app = repositories.get_ai_application(conn, app_key)
            if not app:
                raise HTTPException(status_code=404, detail="AI application not found")
            validate_publishable(app)
            return repositories.publish_ai_application(conn, app_key)
    except HTTPException:
        raise
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def run_draft_application(app_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    app = get_ai_application(app_key)
    return execute_single_turn_application(app, payload, caller_type="studio_draft", require_published=False)


def stream_draft_application(app_key: str, payload: dict[str, Any]) -> Any:
    app = get_ai_application(app_key)
    prepared = prepare_single_turn_run(app, payload, require_published=False)
    return stream_single_turn_application(prepared, caller_type="studio_draft")


def run_published_application(app_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    app = get_ai_application(app_key)
    return execute_single_turn_application(app, payload, caller_type="application_api", require_published=True)


def list_prompt_runtime_traces(limit: int = 50) -> dict[str, Any]:
    return read_list(lambda conn: repositories.list_prompt_runtime_traces(conn, limit=limit))


def list_ai_application_run_logs(app_key: str, limit: int = 50) -> dict[str, Any]:
    app = get_ai_application(app_key)
    return read_list(lambda conn: repositories.list_ai_application_run_logs(conn, app["app_key"], limit=limit))


def get_prompt_runtime_trace(trace_id: str) -> dict[str, Any]:
    trace = read_one(lambda conn: repositories.get_prompt_runtime_trace(conn, trace_id))
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


def get_tenant_ai_quota() -> dict[str, Any]:
    quota = read_one(repositories.get_tenant_ai_quota)
    assert quota is not None
    return quota


def get_admin_tenant_ai_quota(tenant_id: int) -> dict[str, Any]:
    quota = read_one(lambda conn: repositories.get_tenant_ai_quota(conn, tenant_id=tenant_id))
    assert quota is not None
    return quota


def save_tenant_ai_quota(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            require_llm_schema(conn)
            return repositories.upsert_tenant_ai_quota(conn, tenant_id, payload)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def execute_single_turn_application(
    app: dict[str, Any],
    payload: dict[str, Any],
    *,
    caller_type: str,
    require_published: bool,
) -> dict[str, Any]:
    if app.get("app_type") != "single_turn_generation":
        raise HTTPException(status_code=422, detail="Only single_turn_generation is supported in milestone 1")
    if require_published and app.get("status") != "published":
        raise HTTPException(status_code=409, detail="AI application is not published")

    prepared = prepare_single_turn_run(app, payload, require_published=require_published)
    app_for_run = prepared["app"]
    variables = prepared["variables"]
    messages = prepared["messages"]
    rendered_prompt = prepared["rendered_prompt"]
    model = prepared["model"]
    temperature = prepared["temperature"]
    response_format = prepared["response_format"]
    prompt_refs = prepared["prompt_refs"]

    trace_id = f"trace_{uuid.uuid4().hex}"
    started_at = time.perf_counter()
    answer = ""
    usage: dict[str, Any] = {}

    try:
        response = gateway.chat_completions(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format=response_format,
            extra_body=resolve_extra_body(app_for_run, payload),
            enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
            correlation_id=trace_id,
        )
        answer = extract_answer(response)
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        trace = record_trace(
            trace_id=trace_id,
            app=app_for_run,
            caller_type=caller_type,
            model=model,
            status="success",
            variables=variables,
            messages=messages,
            rendered_prompt=rendered_prompt,
            answer=answer,
            usage=usage,
            elapsed_ms=elapsed_ms,
            prompt_refs=prompt_refs,
        )
        return {"answer": answer, "trace_id": trace_id, "usage": usage, "trace": trace}
    except gateway.LLMRoutingError as exc:
        trace = record_trace(
            trace_id=trace_id,
            app=app_for_run,
            caller_type=caller_type,
            model=model,
            status="failed",
            variables=variables,
            messages=messages,
            rendered_prompt=rendered_prompt,
            answer=answer,
            usage=usage,
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            error=exc,
            prompt_refs=prompt_refs,
        )
        raise HTTPException(status_code=422, detail={"message": str(exc), "trace_id": trace.get("trace_id")}) from exc
    except RuntimeError as exc:
        trace = record_trace(
            trace_id=trace_id,
            app=app_for_run,
            caller_type=caller_type,
            model=model,
            status="failed",
            variables=variables,
            messages=messages,
            rendered_prompt=rendered_prompt,
            answer=answer,
            usage=usage,
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            error=exc,
            prompt_refs=prompt_refs,
        )
        raise HTTPException(status_code=502, detail={"message": str(exc), "trace_id": trace.get("trace_id")}) from exc


def prepare_single_turn_run(app: dict[str, Any], payload: dict[str, Any], *, require_published: bool) -> dict[str, Any]:
    if app.get("app_type") != "single_turn_generation":
        raise HTTPException(status_code=422, detail="Only single_turn_generation is supported in milestone 1")
    if require_published and app.get("status") != "published":
        raise HTTPException(status_code=409, detail="AI application is not published")

    app_for_run, prompt_refs = resolve_prompt_runtime_app(app)
    variables = payload.get("variables")
    if variables is None:
        variables = {key: value for key, value in payload.items() if key not in {"model", "temperature", "response_format"}}
    if not isinstance(variables, dict):
        raise HTTPException(status_code=422, detail="variables must be an object")
    validate_variables(app_for_run, variables)

    messages = render_messages(app_for_run, variables)
    rendered_prompt = gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages))
    model = resolve_model(app_for_run, payload)
    return {
        "app": app_for_run,
        "payload": payload,
        "variables": variables,
        "messages": messages,
        "rendered_prompt": rendered_prompt,
        "model": model,
        "temperature": resolve_temperature(app_for_run, payload),
        "response_format": resolve_response_format(app_for_run, payload),
        "prompt_refs": prompt_refs,
    }


def stream_single_turn_application(prepared: dict[str, Any], *, caller_type: str) -> Any:
    app = prepared["app"]
    payload = prepared["payload"]
    variables = prepared["variables"]
    messages = prepared["messages"]
    rendered_prompt = prepared["rendered_prompt"]
    model = prepared["model"]
    temperature = prepared["temperature"]
    response_format = prepared["response_format"]
    prompt_refs = prepared["prompt_refs"]
    trace_id = f"trace_{uuid.uuid4().hex}"
    started_at = time.perf_counter()

    def events() -> Any:
        answer_parts: list[str] = []
        error: Exception | None = None
        trace_recorded = False

        def finish_trace(status: str, trace_error: Exception | None) -> dict[str, Any]:
            nonlocal trace_recorded
            trace_recorded = True
            return record_trace(
                trace_id=trace_id,
                app=app,
                caller_type=caller_type,
                model=model,
                status=status,
                variables=variables,
                messages=messages,
                rendered_prompt=rendered_prompt,
                answer="".join(answer_parts),
                usage={},
                elapsed_ms=int((time.perf_counter() - started_at) * 1000),
                error=trace_error,
                prompt_refs=prompt_refs,
            )

        def trace_event(trace: dict[str, Any]) -> str:
            return gateway.sse_data({"trace_id": trace_id, "trace": trace, "object": "ai_application.run.trace"}).replace(
                "data: ", "event: trace\ndata: ", 1
            )

        yield gateway.sse_data({"trace_id": trace_id, "model": model, "object": "ai_application.run.start"}).replace(
            "data: ", "event: meta\ndata: ", 1
        )
        try:
            for event in gateway.stream_chat_completions(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                extra_body=resolve_extra_body(app, payload),
                enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
                correlation_id=trace_id,
            ):
                event_type, event_data = parse_sse_event(event)
                if event_type == "error":
                    error = RuntimeError(event_data.get("message") or "LLM stream failed")
                    yield event
                    continue
                if event.strip() == "data: [DONE]":
                    trace = finish_trace("failed" if error else "success", error)
                    yield trace_event(trace)
                    yield event
                    break
                answer_parts.append(gateway.stream_event_content(event))
                yield event
            if not trace_recorded:
                trace = finish_trace("failed" if error else "success", error)
                yield trace_event(trace)
                yield "data: [DONE]\n\n"
        except gateway.LLMRoutingError as exc:
            trace = finish_trace("failed", exc)
            yield gateway.sse_error(str(exc))
            yield trace_event(trace)
            yield "data: [DONE]\n\n"
        except RuntimeError as exc:
            trace = finish_trace("failed", exc)
            yield gateway.sse_error(str(exc))
            yield trace_event(trace)
            yield "data: [DONE]\n\n"

    return events()


def enforce_application_quota(conn: Any) -> None:
    quota = repositories.get_tenant_ai_quota(conn)
    if not quota.get("enabled", True):
        raise ValueError("AI Studio is disabled for this tenant")
    usage = quota.get("usage") if isinstance(quota.get("usage"), dict) else {}
    if int(usage.get("applications") or 0) >= int(quota.get("max_applications") or 0):
        raise ValueError("tenant AI application quota exceeded")


def normalize_single_turn_payload(payload: dict[str, Any]) -> None:
    payload["app_type"] = payload.get("app_type") or "single_turn_generation"
    if payload["app_type"] != "single_turn_generation":
        raise ValueError("Only single_turn_generation is supported in milestone 1")
    payload.setdefault("variables_schema", {})
    payload.setdefault("model_preferences", {})
    payload.setdefault("trace_policy", {"enabled": True})


def validate_publishable(app: dict[str, Any]) -> None:
    if not str(app.get("user_prompt_template") or "").strip():
        raise HTTPException(status_code=422, detail="user_prompt_template is required before publish")
    resolve_model(app, {})


def validate_variables(app: dict[str, Any], variables: dict[str, Any]) -> None:
    schema = app.get("variables_schema") if isinstance(app.get("variables_schema"), dict) else {}
    required = schema.get("required", []) if isinstance(schema.get("required"), list) else []
    missing = [name for name in required if variable_missing(resolve_variable_value(variables, str(name)))]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required variables: {', '.join(map(str, missing))}")


def resolve_prompt_runtime_app(app: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    source = str(runtime_config.get("system_prompt_source") or "inline").strip()
    if source != "asset":
        return app, []
    prompt_key = str(runtime_config.get("system_prompt_asset_key") or "").strip()
    if not prompt_key:
        raise HTTPException(status_code=422, detail="system_prompt_asset_key is required when system prompt source is asset")
    tenant_id = int(app.get("tenant_id") or 0)
    if tenant_id <= 0:
        raise HTTPException(status_code=422, detail="tenant_id is required to resolve prompt asset")
    try:
        resolved = prompt_asset_services.resolve_published_prompt(prompt_key=prompt_key, tenant_id=tenant_id)
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"prompt asset resolver error: {exc}") from exc

    content = str(resolved.get("system_prompt") or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="published prompt asset content is empty")
    resolved_app = dict(app)
    resolved_app["system_prompt"] = content
    prompt_ref = {
        "type": "system_prompt",
        "source": "prompt_asset",
        "asset_key": resolved.get("asset_key") or prompt_key,
        "name": resolved.get("name") or "",
        "version": resolved.get("resolved_version") or "",
        "published_time": resolved.get("published_time"),
        "content": content,
    }
    return resolved_app, [prompt_ref]


def render_messages(app: dict[str, Any], variables: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for role, field in (
        ("system", "system_prompt"),
        ("developer", "developer_prompt"),
        ("user", "user_prompt_template"),
    ):
        content = render_template(str(app.get(field) or ""), variables)
        if content.strip():
            messages.append({"role": role, "content": render_message_content(role, content, variables)})
    if not messages:
        raise HTTPException(status_code=422, detail="Prompt content is required")
    return messages


def render_message_content(role: str, text: str, variables: dict[str, Any]) -> str | list[dict[str, Any]]:
    if role != "user":
        return text
    media_parts = media_content_parts(variables)
    if not media_parts:
        return text
    return [{"type": "text", "text": text}, *media_parts]


def render_template(template: str, variables: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return variable_text(resolve_variable_value(variables, name))

    return VARIABLE_PATTERN.sub(replace, template)


def resolve_variable_value(variables: dict[str, Any], name: str) -> Any:
    if name in variables:
        return variables.get(name)
    current: Any = variables
    for part in name.split("."):
        if not isinstance(current, dict) or part not in current:
            return ""
        current = current.get(part)
    return current


def variable_missing(value: Any) -> bool:
    return value in (None, "")


def variable_text(value: Any) -> str:
    if is_media_variable(value):
        media_type = str(value.get("type") or "file")
        name = str(value.get("name") or "未命名附件")
        mime_type = str(value.get("mime_type") or "")
        size = int(value.get("size") or 0)
        if value.get("text"):
            return str(value["text"])
        return f"[已上传{media_type}：{name}，{mime_type}，{size} bytes]"
    return str(value or "")


def media_content_parts(variables: dict[str, Any]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for key, value in variables.items():
        if is_media_variable(value):
            part = media_content_part(str(key), value)
            if part:
                parts.append(part)
    return parts


def media_content_part(key: str, value: dict[str, Any]) -> dict[str, Any] | None:
    media_type = str(value.get("type") or "file").strip().lower()
    data_url = str(value.get("data_url") or "").strip()
    name = str(value.get("name") or key)
    mime_type = str(value.get("mime_type") or "")
    text = str(value.get("text") or "")
    if text:
        return {"type": "text", "text": f"\n\n附件 {name} 内容：\n{text}"}
    if not data_url:
        return {"type": "text", "text": variable_text(value)}
    if media_type == "image":
        return {"type": "image_url", "image_url": {"url": data_url}}
    if media_type == "audio":
        return {
            "type": "input_audio",
            "input_audio": {
                "data": data_url_payload(data_url),
                "format": media_format(name, mime_type, "mp3"),
            },
        }
    if media_type == "video":
        return {"type": "video_url", "video_url": {"url": data_url}}
    if media_type == "file":
        return {"type": "file", "file": {"filename": name, "file_data": data_url}}
    return None


def is_media_variable(value: Any) -> bool:
    return isinstance(value, dict) and str(value.get("type") or "").strip().lower() in MEDIA_VARIABLE_TYPES


def data_url_payload(data_url: str) -> str:
    return data_url.split(",", 1)[1] if "," in data_url else data_url


def media_format(name: str, mime_type: str, fallback: str) -> str:
    if "/" in mime_type:
        return mime_type.rsplit("/", 1)[1].split(";", 1)[0] or fallback
    if "." in name:
        return name.rsplit(".", 1)[1].lower() or fallback
    return fallback


def resolve_model(app: dict[str, Any], payload: dict[str, Any]) -> str:
    if payload.get("model"):
        return str(payload["model"]).strip()
    preferences = app.get("model_preferences") if isinstance(app.get("model_preferences"), dict) else {}
    model = str(preferences.get("model") or preferences.get("route_key") or "").strip()
    if not model:
        raise HTTPException(status_code=422, detail="model_preferences.model or model_preferences.route_key is required")
    return model


def resolve_temperature(app: dict[str, Any], payload: dict[str, Any]) -> float | None:
    if payload.get("temperature") is not None:
        return float(payload["temperature"])
    preferences = app.get("model_preferences") if isinstance(app.get("model_preferences"), dict) else {}
    return float(preferences["temperature"]) if preferences.get("temperature") is not None else None


def resolve_response_format(app: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(payload.get("response_format"), dict):
        return payload["response_format"]
    output_schema = app.get("output_schema") if isinstance(app.get("output_schema"), dict) else {}
    if output_schema.get("type") == "json_object":
        return {"type": "json_object"}
    return None


def resolve_extra_body(app: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    extra_body = runtime_config.get("extra_body") if isinstance(runtime_config.get("extra_body"), dict) else {}
    result = dict(extra_body)
    request_extra_body = payload.get("extra_body")
    if isinstance(request_extra_body, dict):
        result.update(request_extra_body)
    return result


def extract_answer(response: dict[str, Any]) -> str:
    choices = response.get("choices") if isinstance(response.get("choices"), list) else []
    if not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    return str(message.get("content") or "") if isinstance(message, dict) else ""


def record_trace(
    *,
    trace_id: str,
    app: dict[str, Any],
    caller_type: str,
    model: str,
    status: str,
    variables: dict[str, Any],
    messages: list[dict[str, Any]],
    rendered_prompt: str,
    answer: str,
    usage: dict[str, Any],
    elapsed_ms: int,
    error: Exception | None = None,
    prompt_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    database_target = require_database()
    payload = {
        "trace_id": trace_id,
        "caller_type": caller_type,
        "caller_key": app.get("app_key"),
        "app_key": app.get("app_key"),
        "app_version": str(app.get("lock_version") or ""),
        "route_key": model,
        "model_key": model,
        "status": status,
        "input_variables": variables,
        "rendered_messages": trace_messages(messages, prompt_refs or []),
        "rendered_prompt": rendered_prompt,
        "answer": answer,
        "usage": usage,
        "elapsed_ms": elapsed_ms,
        "error_code": error.__class__.__name__ if error else "",
        "error_message": str(error) if error else "",
        "request_id": current_request_id(),
        "correlation_id": trace_id,
    }
    try:
        with connect(database_target, readonly=False) as conn:
            require_llm_schema(conn)
            return repositories.record_prompt_runtime_trace(conn, payload)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        if error:
            return {"trace_id": trace_id, "trace_error": str(exc)}
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def trace_messages(messages: list[dict[str, Any]], prompt_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not prompt_refs:
        return messages
    result = [dict(item) for item in messages]
    for prompt_ref in prompt_refs:
        if prompt_ref.get("type") != "system_prompt":
            continue
        for message in result:
            if message.get("role") != "system":
                continue
            message["prompt_source"] = prompt_ref.get("source")
            message["prompt_asset_key"] = prompt_ref.get("asset_key")
            message["prompt_asset_name"] = prompt_ref.get("name")
            message["prompt_version"] = prompt_ref.get("version")
            message["prompt_published_time"] = prompt_ref.get("published_time")
            break
    return result


def parse_sse_event(event: str) -> tuple[str, dict[str, Any]]:
    event_type = "message"
    data = ""
    for line in event.splitlines():
        if line.startswith("event: "):
            event_type = line.removeprefix("event: ").strip() or "message"
        elif line.startswith("data: "):
            data = line.removeprefix("data: ").strip()
    if not data or data == "[DONE]":
        return event_type, {}
    try:
        payload = gateway.json.loads(data)
    except Exception:
        return event_type, {}
    return event_type, payload if isinstance(payload, dict) else {}


def read_list(loader: Any) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            require_llm_schema(conn)
            items = loader(conn)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    return {"items": items, "pagination": {"page": 1, "page_size": len(items), "total": len(items)}}


def read_one(loader: Any) -> dict[str, Any] | None:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            require_llm_schema(conn)
            return loader(conn)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
