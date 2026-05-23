from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ai_assets.application import services as prompt_asset_services
from ai_applications.application.ports import AIApplicationsRepository
from ai_runtime_core.prompt_runtime import media_content_parts
from ai_runtime_core.prompt_runtime import render_template
from ai_runtime_core.prompt_runtime import resolve_variable_value
from ai_runtime_core.prompt_runtime import variable_missing
from ai_runtime_core.workflow_runtime import WorkflowLLMRequest
from ai_runtime_core.workflow_runtime import WorkflowLLMResult
from ai_runtime_core.workflow_runtime import WorkflowRuntimeError
from ai_runtime_core.workflow_runtime import WorkflowSQLRequest
from ai_runtime_core.workflow_runtime import WorkflowSQLResult
from ai_runtime_core.workflow_runtime import execute_workflow
from llm_runtime.application import gateway
from system.application.database import connect
from system.application.sorting import sort_dict_items
from system.interfaces.http import current_request_id

from llm_runtime.application.services import require_database
from system.application.data_access import ResourceDescriptor
from system.application.data_access import resolve_data_access_filter


AI_APPLICATION_SORT_COLUMNS = {
    "id": "id",
    "app_key": "app_key",
    "name": "name",
    "app_type": "app_type",
    "status": "status",
    "create_time": "create_time",
    "update_time": "update_time",
}
TRACE_SORT_COLUMNS = {
    "id": "id",
    "trace_id": "trace_id",
    "capability_key": "capability_key",
    "app_key": "app_key",
    "status": "status",
    "duration_ms": "duration_ms",
    "create_time": "create_time",
}
AGENT_CONVERSATION_SORT_COLUMNS = {
    "id": "id",
    "title": "title",
    "last_message_time": "last_message_time",
    "create_time": "create_time",
    "update_time": "update_time",
}

repository: AIApplicationsRepository | None = None


def configure_repository(ai_applications_repository: AIApplicationsRepository) -> None:
    global repository
    repository = ai_applications_repository


def repo() -> AIApplicationsRepository:
    if repository is None:
        raise RuntimeError("ai applications repository is not configured")
    return repository


def studio_overview() -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            repo().require_ai_applications_schema(conn)
            apps = repo().list_ai_applications(conn)
            quota = repo().get_tenant_ai_quota(conn)
            traces, _ = repo().list_prompt_runtime_traces(conn, page=1, page_size=10)
    except (RuntimeError, ValueError) as exc:
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
            {"type": "single_turn_generation", "label": "\u5355\u8f6e\u5bf9\u8bdd", "enabled": True},
            {"type": "workflow", "label": "Workflow", "enabled": True},
            {"type": "agent", "label": "Agent", "enabled": True},
        ],
    }


def list_ai_applications(
    *,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    return read_list(
        lambda conn: repo().list_ai_applications(conn),
        page=page,
        page_size=page_size,
        filterer=lambda items: filter_ai_applications(items, keyword=keyword, status=status),
        sort_by=sort_by,
        sort_dir=sort_dir,
        allowed_sort=AI_APPLICATION_SORT_COLUMNS,
    )


def filter_ai_applications(items: list[dict[str, Any]], *, keyword: str | None, status: str | None) -> list[dict[str, Any]]:
    text = str(keyword or "").strip().lower()
    status_value = str(status or "").strip()
    if status_value == "all":
        status_value = ""
    return [
        item
        for item in items
        if (not status_value or str(item.get("status") or "") == status_value)
        and (
            not text
            or text in str(item.get("name") or "").lower()
            or text in str(item.get("app_key") or "").lower()
        )
    ]


def get_ai_application(app_key: str) -> dict[str, Any]:
    app = read_one(lambda conn: repo().get_ai_application(conn, app_key))
    if not app:
        raise HTTPException(status_code=404, detail="AI application not found")
    return app


def save_ai_application(payload: dict[str, Any]) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            existing = repo().get_ai_application(conn, str(payload.get("app_key") or ""))
            if not existing:
                enforce_application_quota(conn)
            normalize_application_payload(payload)
            return repo().upsert_ai_application(conn, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def publish_ai_application(app_key: str) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            app = repo().get_ai_application(conn, app_key)
            if not app:
                raise HTTPException(status_code=404, detail="AI application not found")
            validate_publishable(app)
            return repo().publish_ai_application(conn, app_key)
    except HTTPException:
        raise
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def run_draft_application(app_key: str, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    app = get_ai_application(app_key)
    return execute_application(app, payload, caller_type="studio_draft", require_published=False, current_user=current_user)


def stream_draft_application(app_key: str, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> Any:
    app = get_ai_application(app_key)
    if app.get("app_type") == "workflow":
        return stream_workflow_application(app, payload, caller_type="studio_draft", require_published=False, current_user=current_user)
    if app.get("app_type") == "agent":
        raise HTTPException(status_code=422, detail="Agent applications must run through agent conversation APIs")
    prepared = prepare_single_turn_run(app, payload, require_published=False)
    return stream_single_turn_application(prepared, caller_type="studio_draft")


def run_published_application(app_key: str, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    app = get_ai_application(app_key)
    return execute_application(app, payload, caller_type="application_api", require_published=True, current_user=current_user)


def list_agent_conversations(
    app_key: str,
    *,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    app = require_agent_application(app_key)
    return read_list(
        lambda conn: (
            repo().require_ai_agent_schema(conn)
            or repo().list_agent_conversations(conn, app["app_key"], limit=max(1, page) * max(1, page_size))
        ),
        page=page,
        page_size=page_size,
        filterer=lambda items: filter_agent_conversations(items, keyword=keyword),
        sort_by=sort_by,
        sort_dir=sort_dir,
        allowed_sort=AGENT_CONVERSATION_SORT_COLUMNS,
    )


def filter_agent_conversations(items: list[dict[str, Any]], *, keyword: str | None) -> list[dict[str, Any]]:
    text = str(keyword or "").strip().lower()
    if not text:
        return items
    return [
        item
        for item in items
        if text in str(item.get("title") or "").lower()
        or text in str(item.get("last_message_preview") or "").lower()
    ]


def create_agent_conversation(app_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    app = require_agent_application(app_key)
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            repo().require_ai_agent_schema(conn)
            return repo().create_agent_conversation(conn, app["app_key"], payload)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def list_agent_messages(
    app_key: str,
    conversation_key: str,
    *,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    app = require_agent_application(app_key)
    conversation = get_agent_conversation_or_404(app, conversation_key)
    return read_list(
        lambda conn: (
            repo().require_ai_agent_schema(conn)
            or repo().list_agent_messages(
                conn,
                app["app_key"],
                conversation["conversation_key"],
                limit=max(1, page) * max(1, page_size),
            )
        ),
        page=page,
        page_size=page_size,
    )


def send_agent_message(app_key: str, conversation_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    prepared = prepare_agent_run(app_key, conversation_key, payload)
    trace_id = f"trace_{uuid.uuid4().hex}"
    started_at = time.perf_counter()
    answer = ""
    usage: dict[str, Any] = {}
    try:
        response = gateway.chat_completions(
            model=prepared["model"],
            messages=prepared["messages"],
            temperature=prepared["temperature"],
            response_format=prepared["response_format"],
            extra_body=resolve_extra_body(prepared["app"], payload),
            enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
            correlation_id=trace_id,
        )
        answer = extract_answer(response)
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        trace = record_trace(
            trace_id=trace_id,
            app=prepared["app"],
            caller_type="ai_agent",
            caller_key=prepared["conversation"]["conversation_key"],
            model=prepared["model"],
            status="success",
            variables=prepared["variables"],
            messages=prepared["messages"],
            rendered_prompt=prepared["rendered_prompt"],
            answer=answer,
            usage=usage,
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            prompt_refs=prepared["prompt_refs"],
        )
        assistant_message = persist_agent_assistant_message(
            prepared,
            content=answer,
            status="completed",
            trace_id=trace_id,
        )
        return {
            "conversation": prepared["conversation"],
            "user_message": prepared["user_message"],
            "assistant_message": assistant_message,
            "answer": answer,
            "trace_id": trace_id,
            "usage": usage,
            "trace": trace,
        }
    except (gateway.LLMRoutingError, RuntimeError) as exc:
        trace = record_trace(
            trace_id=trace_id,
            app=prepared["app"],
            caller_type="ai_agent",
            caller_key=prepared["conversation"]["conversation_key"],
            model=prepared["model"],
            status="failed",
            variables=prepared["variables"],
            messages=prepared["messages"],
            rendered_prompt=prepared["rendered_prompt"],
            answer=answer,
            usage=usage,
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            error=exc,
            prompt_refs=prepared["prompt_refs"],
        )
        assistant_message = persist_agent_assistant_message(
            prepared,
            content=answer,
            status="failed",
            trace_id=trace_id,
            error=exc,
        )
        raise HTTPException(
            status_code=422,
            detail={"message": str(exc), "trace_id": trace.get("trace_id"), "assistant_message": assistant_message},
        ) from exc


def stream_agent_message(app_key: str, conversation_key: str, payload: dict[str, Any]) -> Any:
    prepared = prepare_agent_run(app_key, conversation_key, payload)
    trace_id = f"trace_{uuid.uuid4().hex}"
    started_at = time.perf_counter()
    assistant_message = persist_agent_assistant_message(
        prepared,
        content="",
        status="streaming",
        trace_id=trace_id,
    )

    def events() -> Any:
        answer_parts: list[str] = []
        error: Exception | None = None
        trace_recorded = False

        def emit_named(event_name: str, payload_data: dict[str, Any]) -> str:
            return gateway.sse_data(payload_data).replace("data: ", f"event: {event_name}\ndata: ", 1)

        def finish(status: str, trace_error: Exception | None) -> dict[str, Any]:
            nonlocal trace_recorded, assistant_message
            trace_recorded = True
            answer = "".join(answer_parts)
            trace = record_trace(
                trace_id=trace_id,
                app=prepared["app"],
                caller_type="ai_agent",
                caller_key=prepared["conversation"]["conversation_key"],
                model=prepared["model"],
                status=status,
                variables=prepared["variables"],
                messages=prepared["messages"],
                rendered_prompt=prepared["rendered_prompt"],
                answer=answer,
                usage={},
                elapsed_ms=int((time.perf_counter() - started_at) * 1000),
                error=trace_error,
                prompt_refs=prepared["prompt_refs"],
            )
            assistant_message = update_agent_assistant_message(
                assistant_message["message_key"],
                content=answer,
                status="completed" if status == "success" else "failed",
                trace_id=trace_id,
                error=trace_error,
            )
            return trace

        yield emit_named(
            "meta",
            {
                "trace_id": trace_id,
                "model": prepared["model"],
                "conversation_key": prepared["conversation"]["conversation_key"],
                "user_message_key": prepared["user_message"]["message_key"],
                "assistant_message_key": assistant_message["message_key"],
                "object": "ai_application.agent.run.start",
            },
        )
        try:
            for event in gateway.stream_chat_completions(
                model=prepared["model"],
                messages=prepared["messages"],
                temperature=prepared["temperature"],
                response_format=prepared["response_format"],
                extra_body=resolve_extra_body(prepared["app"], payload),
                enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
                correlation_id=trace_id,
            ):
                event_type, event_data = parse_sse_event(event)
                if event_type == "error":
                    error = RuntimeError(event_data.get("message") or "LLM stream failed")
                    yield event
                    continue
                if event.strip() == "data: [DONE]":
                    trace = finish("failed" if error else "success", error)
                    yield emit_named("trace", {"trace_id": trace_id, "trace": trace, "object": "ai_application.agent.run.trace"})
                    yield emit_named(
                        "final",
                        {
                            "trace_id": trace_id,
                            "assistant_message": assistant_message,
                            "object": "ai_application.agent.message.final",
                        },
                    )
                    yield event
                    break
                answer_parts.append(gateway.stream_event_content(event))
                yield event
            if not trace_recorded:
                trace = finish("failed" if error else "success", error)
                yield emit_named("trace", {"trace_id": trace_id, "trace": trace, "object": "ai_application.agent.run.trace"})
                yield emit_named(
                    "final",
                    {
                        "trace_id": trace_id,
                        "assistant_message": assistant_message,
                        "object": "ai_application.agent.message.final",
                    },
                )
                yield "data: [DONE]\n\n"
        except (gateway.LLMRoutingError, RuntimeError) as exc:
            trace = finish("failed", exc)
            yield gateway.sse_error(str(exc))
            yield emit_named("trace", {"trace_id": trace_id, "trace": trace, "object": "ai_application.agent.run.trace"})
            yield emit_named(
                "final",
                {
                    "trace_id": trace_id,
                    "assistant_message": assistant_message,
                    "object": "ai_application.agent.message.final",
                },
            )
            yield "data: [DONE]\n\n"

    return events()


def list_prompt_runtime_traces(
    *, page: int = 1, page_size: int = 20, sort_by: str | None = None, sort_dir: str | None = None
) -> dict[str, Any]:
    return read_trace_page(
        lambda conn, safe_page, safe_page_size: repo().list_prompt_runtime_traces(
            conn,
            page=safe_page,
            page_size=safe_page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            allowed_sort=TRACE_SORT_COLUMNS,
        ),
        page=page,
        page_size=page_size,
    )


def list_ai_application_run_logs(
    app_key: str, *, page: int = 1, page_size: int = 20, sort_by: str | None = None, sort_dir: str | None = None
) -> dict[str, Any]:
    app = get_ai_application(app_key)
    return read_trace_page(
        lambda conn, safe_page, safe_page_size: repo().list_ai_application_run_logs(
            conn,
            app["app_key"],
            page=safe_page,
            page_size=safe_page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            allowed_sort=TRACE_SORT_COLUMNS,
        ),
        page=page,
        page_size=page_size,
    )


def list_ai_capability_run_logs(
    capability_key: str, *, page: int = 1, page_size: int = 20, sort_by: str | None = None, sort_dir: str | None = None
) -> dict[str, Any]:
    return read_trace_page(
        lambda conn, safe_page, safe_page_size: repo().list_ai_capability_run_logs(
            conn,
            capability_key,
            page=safe_page,
            page_size=safe_page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            allowed_sort=TRACE_SORT_COLUMNS,
        ),
        page=page,
        page_size=page_size,
    )


def list_platform_ai_capability_run_logs(
    capability_key: str, *, page: int = 1, page_size: int = 20, sort_by: str | None = None, sort_dir: str | None = None
) -> dict[str, Any]:
    return read_trace_page(
        lambda conn, safe_page, safe_page_size: repo().list_platform_ai_capability_run_logs(
            conn,
            capability_key,
            page=safe_page,
            page_size=safe_page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            allowed_sort=TRACE_SORT_COLUMNS,
        ),
        page=page,
        page_size=page_size,
    )


def prompt_asset_is_referenced(*, tenant_id: int, prompt_key: str) -> bool:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            repo().require_ai_applications_schema(conn)
            return repo().prompt_asset_is_referenced_by_ai_application(
                conn,
                tenant_id=tenant_id,
                prompt_key=prompt_key,
            )
    except RuntimeError as exc:
        if "ai_applications storage is not initialized" in str(exc):
            return False
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    except (sqlite3.Error, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


prompt_asset_services.register_prompt_asset_reference_checker(
    lambda tenant_id, prompt_key: prompt_asset_is_referenced(tenant_id=tenant_id, prompt_key=prompt_key)
)


def get_prompt_runtime_trace(trace_id: str) -> dict[str, Any]:
    trace = read_trace_one(lambda conn: repo().get_prompt_runtime_trace(conn, trace_id))
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


def get_tenant_ai_quota() -> dict[str, Any]:
    quota = read_one(repo().get_tenant_ai_quota)
    assert quota is not None
    return quota


def get_admin_tenant_ai_quota(tenant_id: int) -> dict[str, Any]:
    quota = read_one(lambda conn: repo().get_tenant_ai_quota(conn, tenant_id=tenant_id))
    assert quota is not None
    return quota


def save_tenant_ai_quota(tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            return repo().upsert_tenant_ai_quota(conn, tenant_id, payload)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def execute_single_turn_application(
    app: dict[str, Any],
    payload: dict[str, Any],
    *,
    caller_type: str,
    require_published: bool,
    caller_key: str | None = None,
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
            caller_key=caller_key,
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
            caller_key=caller_key,
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
            caller_key=caller_key,
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


def execute_application(
    app: dict[str, Any],
    payload: dict[str, Any],
    *,
    caller_type: str,
    require_published: bool,
    caller_key: str | None = None,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    app_type = str(app.get("app_type") or "single_turn_generation")
    if app_type == "workflow":
        return execute_workflow_application(
            app,
            payload,
            caller_type=caller_type,
            caller_key=caller_key,
            require_published=require_published,
            current_user=current_user,
        )
    if app_type == "agent":
        raise HTTPException(status_code=422, detail="Agent applications must run through agent conversation APIs")
    return execute_single_turn_application(
        app,
        payload,
        caller_type=caller_type,
        caller_key=caller_key,
        require_published=require_published,
    )


def execute_workflow_application(
    app: dict[str, Any],
    payload: dict[str, Any],
    *,
    caller_type: str,
    require_published: bool,
    caller_key: str | None = None,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if require_published and app.get("status") != "published":
        raise HTTPException(status_code=409, detail="AI application is not published")
    variables = extract_run_variables(payload)
    definition = workflow_definition_from_app(app)
    validate_workflow_variables(definition, variables)
    trace_id = f"trace_{uuid.uuid4().hex}"
    started_at = time.perf_counter()
    answer = ""
    usage: dict[str, Any] = {}
    rendered_messages: list[dict[str, Any]] = []
    rendered_prompt = ""
    model = resolve_workflow_default_model(app, payload, definition)

    def llm_executor(request: WorkflowLLMRequest) -> WorkflowLLMResult:
        nonlocal rendered_messages, rendered_prompt, model
        rendered_messages.append(
            {
                "role": "workflow_node",
                "node_id": request.node_id,
                "model": request.model,
                "messages": request.messages,
            }
        )
        rendered_prompt = gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(request.messages))
        model = request.model
        response = gateway.chat_completions(
            model=request.model,
            messages=request.messages,
            temperature=request.temperature,
            response_format=request.response_format,
            extra_body={**resolve_extra_body(app, payload), **request.extra_body},
            enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
            correlation_id=trace_id,
        )
        response_usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        return WorkflowLLMResult(answer=extract_answer(response), usage=response_usage, model=str(response.get("model") or request.model))

    def sql_executor(request: WorkflowSQLRequest) -> WorkflowSQLResult:
        return execute_workflow_sql_query(app, request, current_user=current_user)

    try:
        workflow_result = execute_workflow(definition, variables, llm_executor=llm_executor, sql_executor=sql_executor)
        answer = workflow_result.answer
        usage = workflow_result.usage
        elapsed = int((time.perf_counter() - started_at) * 1000)
        trace = record_trace(
            trace_id=trace_id,
            app=app,
            caller_type=caller_type,
            caller_key=caller_key,
            model=model,
            status="success",
            variables=variables,
            messages=workflow_trace_messages(rendered_messages, workflow_result.trace),
            rendered_prompt=rendered_prompt,
            answer=answer,
            usage=usage,
            elapsed_ms=elapsed,
        )
        return {"answer": answer, "trace_id": trace_id, "usage": usage, "trace": trace}
    except (WorkflowRuntimeError, gateway.LLMRoutingError, RuntimeError) as exc:
        trace = record_trace(
            trace_id=trace_id,
            app=app,
            caller_type=caller_type,
            caller_key=caller_key,
            model=model,
            status="failed",
            variables=variables,
            messages=workflow_trace_messages(rendered_messages, {}),
            rendered_prompt=rendered_prompt,
            answer=answer,
            usage=usage,
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            error=exc,
        )
        raise HTTPException(status_code=422, detail={"message": str(exc), "trace_id": trace.get("trace_id")}) from exc


def stream_workflow_application(
    app: dict[str, Any],
    payload: dict[str, Any],
    *,
    caller_type: str,
    require_published: bool,
    current_user: dict[str, Any] | None = None,
) -> Any:
    def events() -> Any:
        try:
            result = execute_workflow_application(
                app,
                payload,
                caller_type=caller_type,
                require_published=require_published,
                current_user=current_user,
            )
            trace_id = str(result.get("trace_id") or "")
            yield gateway.sse_data({"trace_id": trace_id, "object": "ai_application.workflow.start"}).replace(
                "data: ", "event: meta\ndata: ", 1
            )
            answer = str(result.get("answer") or "")
            if answer:
                yield gateway.sse_data({"choices": [{"delta": {"content": answer}}]})
            yield gateway.sse_data({"trace_id": trace_id, "trace": result.get("trace"), "object": "ai_application.run.trace"}).replace(
                "data: ", "event: trace\ndata: ", 1
            )
            yield "data: [DONE]\n\n"
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            yield gateway.sse_error(str(detail.get("message") or exc.detail))
            yield "data: [DONE]\n\n"

    return events()


def execute_workflow_sql_query(
    app: dict[str, Any],
    request: WorkflowSQLRequest,
    *,
    current_user: dict[str, Any] | None,
) -> WorkflowSQLResult:
    if current_user is None:
        current_user = workflow_sql_system_user(app)
    descriptor = workflow_sql_resource_descriptor(request)
    predicate = resolve_data_access_filter(current_user=current_user, resource=descriptor, action="read")
    scope_sql, scope_params = predicate.to_sql(descriptor, alias="workflow_sql_source")
    if not scope_sql:
        raise WorkflowRuntimeError("SQL node data access filter is required")
    limit = max(1, min(1000, int(request.max_rows or 100)))
    guarded_sql = f"SELECT * FROM ({request.sql}) AS workflow_sql_source WHERE {scope_sql} LIMIT ?"
    params = [*request.params, *scope_params, limit + 1]
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            cursor = conn.execute(guarded_sql, tuple(params))
            rows = cursor.fetchall()
    except (RuntimeError, ValueError) as exc:
        raise WorkflowRuntimeError(f"SQL node query failed: {exc}") from exc
    normalized_rows = [normalize_sql_row(row) for row in rows[:limit]]
    columns = list(normalized_rows[0].keys()) if normalized_rows else sql_cursor_columns(cursor)
    return WorkflowSQLResult(
        rows=normalized_rows,
        columns=columns,
        row_count=len(normalized_rows),
        truncated=len(rows) > limit,
    )


def workflow_sql_resource_descriptor(request: WorkflowSQLRequest) -> ResourceDescriptor:
    config = request.data_access if isinstance(request.data_access, dict) else {}
    return ResourceDescriptor(
        resource_key=str(config.get("resource_key") or "ai_applications.workflow_sql"),
        tenant_column=str(config.get("tenant_column") or "tenant_id"),
        creator_column=str(config.get("creator_column") or "creator_id"),
        owner_user_column=str(config.get("owner_user_column") or "owner_user_id"),
        owner_department_column=str(config.get("owner_department_column") or "owner_department_id"),
        requires_data_scope=bool(config.get("requires_data_scope", False)),
    )


def workflow_sql_system_user(app: dict[str, Any]) -> dict[str, Any]:
    tenant_id = int(app.get("tenant_id") or 0)
    if tenant_id <= 0:
        raise WorkflowRuntimeError("SQL node requires current user or tenant_id")
    return {
        "id": 0,
        "username": "system",
        "tenant_id": tenant_id,
        "current_tenant": {"id": tenant_id},
    }


def normalize_sql_row(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    keys = getattr(row, "keys", None)
    if callable(keys):
        return {str(key): row[key] for key in keys()}
    if hasattr(row, "_asdict"):
        return dict(row._asdict())
    return {}


def sql_cursor_columns(cursor: Any) -> list[str]:
    description = getattr(cursor, "description", None) or []
    return [str(item[0]) for item in description if item]


def prepare_single_turn_run(app: dict[str, Any], payload: dict[str, Any], *, require_published: bool) -> dict[str, Any]:
    if app.get("app_type") != "single_turn_generation":
        raise HTTPException(status_code=422, detail="Only single_turn_generation is supported in milestone 1")
    if require_published and app.get("status") != "published":
        raise HTTPException(status_code=409, detail="AI application is not published")

    app_for_run, prompt_refs = resolve_prompt_runtime_app(app)
    variables = extract_run_variables(payload)
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


def stream_single_turn_application(prepared: dict[str, Any], *, caller_type: str, caller_key: str | None = None) -> Any:
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
                caller_key=caller_key,
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


def require_agent_application(app_key: str) -> dict[str, Any]:
    app = get_ai_application(app_key)
    if app.get("app_type") != "agent":
        raise HTTPException(status_code=422, detail="Only Agent applications support agent conversations")
    return app


def get_agent_conversation_or_404(app: dict[str, Any], conversation_key: str) -> dict[str, Any]:
    conversation = read_one(
        lambda conn: repo().require_ai_agent_schema(conn)
        or repo().get_agent_conversation(conn, app["app_key"], conversation_key)
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Agent conversation not found")
    return conversation


def prepare_agent_run(app_key: str, conversation_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    app = require_agent_application(app_key)
    conversation = get_agent_conversation_or_404(app, conversation_key)
    content = str(payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="content is required")

    app_for_run, prompt_refs = resolve_prompt_runtime_app(app)
    variables = extract_run_variables(payload)
    validate_variables(app_for_run, variables)

    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            repo().require_ai_agent_schema(conn)
            history = repo().list_recent_agent_messages(
                conn,
                app_for_run["app_key"],
                conversation["conversation_key"],
                limit=agent_history_limit(app_for_run),
            )
            user_message = repo().insert_agent_message(
                conn,
                {
                    "app_key": app_for_run["app_key"],
                    "conversation_key": conversation["conversation_key"],
                    "role": "user",
                    "content": content,
                    "status": "completed",
                    "metadata": {"variables": variables},
                },
            )
            conversation = repo().get_agent_conversation(conn, app_for_run["app_key"], conversation["conversation_key"]) or conversation
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc

    messages = build_agent_messages(app_for_run, variables, history, content)
    rendered_prompt = gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages))
    return {
        "app": app_for_run,
        "conversation": conversation,
        "user_message": user_message,
        "variables": variables,
        "messages": messages,
        "rendered_prompt": rendered_prompt,
        "model": resolve_model(app_for_run, payload),
        "temperature": resolve_temperature(app_for_run, payload),
        "response_format": resolve_response_format(app_for_run, payload),
        "prompt_refs": prompt_refs,
    }


def build_agent_messages(
    app: dict[str, Any],
    variables: dict[str, Any],
    history: list[dict[str, Any]],
    user_content: str,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for role, field in (("system", "system_prompt"), ("developer", "developer_prompt")):
        content = render_template(str(app.get(field) or ""), variables)
        if content.strip():
            messages.append({"role": role, "content": content})
    for item in history:
        role = str(item.get("role") or "")
        if role not in {"user", "assistant"}:
            continue
        content = str(item.get("content") or "")
        if content.strip():
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": render_message_content("user", user_content, variables)})
    return messages


def agent_history_limit(app: dict[str, Any]) -> int:
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    agent_config = runtime_config.get("agent") if isinstance(runtime_config.get("agent"), dict) else {}
    try:
        return max(1, min(100, int(agent_config.get("history_limit") or 20)))
    except (TypeError, ValueError):
        return 20


def persist_agent_assistant_message(
    prepared: dict[str, Any],
    *,
    content: str,
    status: str,
    trace_id: str,
    error: Exception | None = None,
) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            repo().require_ai_agent_schema(conn)
            return repo().insert_agent_message(
                conn,
                {
                    "app_key": prepared["app"]["app_key"],
                    "conversation_key": prepared["conversation"]["conversation_key"],
                    "role": "assistant",
                    "content": content,
                    "status": status,
                    "trace_id": trace_id,
                    "error_code": error.__class__.__name__ if error else "",
                    "error_message": str(error) if error else "",
                },
            )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def update_agent_assistant_message(
    message_key: str,
    *,
    content: str,
    status: str,
    trace_id: str,
    error: Exception | None = None,
) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            repo().require_ai_agent_schema(conn)
            return repo().update_agent_message(
                conn,
                message_key,
                {
                    "content": content,
                    "status": status,
                    "trace_id": trace_id,
                    "error_code": error.__class__.__name__ if error else "",
                    "error_message": str(error) if error else "",
                },
            )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def enforce_application_quota(conn: Any) -> None:
    quota = repo().get_tenant_ai_quota(conn)
    if not quota.get("enabled", True):
        raise ValueError("AI Studio is disabled for this tenant")
    usage = quota.get("usage") if isinstance(quota.get("usage"), dict) else {}
    if int(usage.get("applications") or 0) >= int(quota.get("max_applications") or 0):
        raise ValueError("tenant AI application quota exceeded")


def normalize_application_payload(payload: dict[str, Any]) -> None:
    payload["app_type"] = payload.get("app_type") or "single_turn_generation"
    if payload["app_type"] not in {"single_turn_generation", "workflow", "agent"}:
        raise ValueError("app_type must be single_turn_generation, workflow, or agent")
    payload.setdefault("variables_schema", {})
    payload.setdefault("model_preferences", {})
    payload.setdefault("trace_policy", {"enabled": True})


def validate_publishable(app: dict[str, Any]) -> None:
    if app.get("app_type") == "workflow":
        workflow_definition_from_app(app)
        return
    if app.get("app_type") == "agent":
        resolve_model(app, {})
        return
    if not str(app.get("user_prompt_template") or "").strip():
        raise HTTPException(status_code=422, detail="user_prompt_template is required before publish")
    resolve_model(app, {})


def extract_run_variables(payload: dict[str, Any]) -> dict[str, Any]:
    variables = payload.get("variables")
    if variables is None:
        variables = {key: value for key, value in payload.items() if key not in {"model", "temperature", "response_format"}}
    if not isinstance(variables, dict):
        raise HTTPException(status_code=422, detail="variables must be an object")
    return variables


def workflow_definition_from_app(app: dict[str, Any]) -> dict[str, Any]:
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    workflow = runtime_config.get("workflow") if isinstance(runtime_config.get("workflow"), dict) else {}
    if not workflow:
        raise HTTPException(status_code=422, detail="workflow runtime_config.workflow is required")
    return workflow


def validate_workflow_variables(definition: dict[str, Any], variables: dict[str, Any]) -> None:
    required = workflow_start_required_variables(definition)
    missing = [name for name in required if variable_missing(resolve_variable_value(variables, name))]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required variables: {', '.join(missing)}")


def workflow_start_required_variables(definition: dict[str, Any]) -> list[str]:
    nodes = definition.get("nodes") if isinstance(definition.get("nodes"), list) else []
    for node in nodes:
        if not isinstance(node, dict) or str(node.get("type") or "").strip() != "start":
            continue
        data = node.get("data") if isinstance(node.get("data"), dict) else {}
        variables = data.get("variables") if isinstance(data.get("variables"), list) else []
        required: list[str] = []
        for item in variables:
            if not isinstance(item, dict) or item.get("required") is False:
                continue
            key = str(item.get("key") or item.get("name") or "").strip()
            if key:
                required.append(key)
        return required
    return []


def resolve_workflow_default_model(app: dict[str, Any], payload: dict[str, Any], definition: dict[str, Any]) -> str:
    if payload.get("model"):
        return str(payload["model"]).strip()
    preferences = app.get("model_preferences") if isinstance(app.get("model_preferences"), dict) else {}
    model = str(preferences.get("model") or preferences.get("route_key") or "").strip()
    if model:
        return model
    nodes = definition.get("nodes") if isinstance(definition.get("nodes"), list) else []
    has_llm_node = False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if str(node.get("type") or "").strip().lower() not in {"llm", "model"}:
            continue
        has_llm_node = True
        data = node.get("data") if isinstance(node.get("data"), dict) else {}
        node_model = str(data.get("model") or data.get("route_key") or "").strip()
        if node_model:
            return node_model
    if not has_llm_node:
        return ""
    raise HTTPException(status_code=422, detail="workflow LLM node model is required")


def workflow_trace_messages(rendered_messages: list[dict[str, Any]], workflow_trace: dict[str, Any]) -> list[dict[str, Any]]:
    result = [dict(item) for item in rendered_messages]
    if workflow_trace:
        result.append({"role": "workflow_trace", "content": workflow_trace})
    return result


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
    caller_key: str | None = None,
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
        "caller_key": caller_key or app.get("app_key"),
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
            repo().require_ai_applications_schema(conn)
            repo().require_prompt_runtime_trace_detail_schema(conn)
            return repo().record_prompt_runtime_trace(conn, payload)
    except (RuntimeError, ValueError) as exc:
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


def read_list(
    loader: Any,
    *,
    page: int = 1,
    page_size: int = 20,
    filterer: Any | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    allowed_sort: dict[str, str] | None = None,
) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            repo().require_ai_applications_schema(conn)
            items = loader(conn)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    if filterer is not None:
        items = filterer(items)
    if allowed_sort is not None:
        items = sort_dict_items(items, sort_by, sort_dir, allowed=allowed_sort)
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, int(page_size or 20))
    total = len(items)
    start = (safe_page - 1) * safe_page_size
    return {"items": items[start:start + safe_page_size], "pagination": {"page": safe_page, "page_size": safe_page_size, "total": total}}


def read_trace_page(loader: Any, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    database_target = require_database()
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, min(100, int(page_size or 20)))
    try:
        with connect(database_target, readonly=True) as conn:
            repo().require_ai_applications_schema(conn)
            repo().require_prompt_runtime_trace_detail_schema(conn)
            items, total = loader(conn, safe_page, safe_page_size)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    return {"items": items, "pagination": {"page": safe_page, "page_size": safe_page_size, "total": total}}


def read_one(loader: Any) -> dict[str, Any] | None:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            repo().require_ai_applications_schema(conn)
            return loader(conn)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def read_trace_one(loader: Any) -> dict[str, Any] | None:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            repo().require_ai_applications_schema(conn)
            repo().require_prompt_runtime_trace_detail_schema(conn)
            return loader(conn)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


