from __future__ import annotations

import copy
import base64
import io
import json
import zipfile
import time
import uuid
from typing import Any

from fastapi import HTTPException

from ai_assets.application import services as prompt_asset_services
from ai_applications.application import agent_file_tools
from ai_applications.application import agent_tools
from ai_applications.application import skill_runtime
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
from ai_runtime_core.workflow_runtime import iter_workflow_events
from ai_runtime_core.workflow_runtime import normalize_workflow_definition
from llm_runtime.application import gateway
from system.application.database import connect
from system.application.database import database_backend
from system.application.sorting import sort_dict_items
from system.interfaces.http import current_request_id

from llm_runtime.application.services import require_database
from system.application.data_access import ResourceDescriptor
from system.application.data_access import current_user_id_or_none
from system.application.data_access import current_user_primary_department_id
from system.application.data_access import resolve_data_access_filter
from system.application.sql_data_access import SQLDataAccessInjectionError
from system.application.sql_data_access import SQLDataAccessInjectionRequest
from system.application.sql_data_access import inject_data_access_into_select


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
WORKFLOW_EXPORT_KIND = "ops_admin.ai_application.workflow"
WORKFLOW_EXPORT_SCHEMA_VERSION = 1
AI_APPLICATION_RESOURCE = ResourceDescriptor(
    resource_key="ai.application",
    owner_user_column="creator_id",
    owner_department_column="owner_department_id",
)
AGENT_STREAM_MAX_ANSWER_CHARS = 200_000
AGENT_TOOL_CALL_MARKER_LIMIT = 3
AGENT_UNSUPPORTED_NATIVE_TOOL_NAMES = (
    "bash",
    "cmd",
    "execute_command",
    "powershell",
    "run_command",
    "run_shell",
    "shell",
    "shell_exec",
    "sh",
    "terminal",
)
AGENT_TOOL_CALL_MARKERS = ("<tool_call", "</tool_call", "<tool_result", "</tool_result", "minimax[>|")
AGENT_TOOL_PROTOCOL_FRAGMENTS = ("<tool_", "</tool_", "|<tool_", "minimax[>")
AGENT_UNHANDLED_TOOL_CALL_MESSAGE = (
    "模型输出了未被当前流式阶段接管的原生工具协议，本次运行已停止，避免继续循环。"
    "Agent 工具需要通过平台 tool_calls JSON 协议执行，当前支持文件工作区、shell.run 和 python.run；"
    "脚本能力会通过已配置的 sandbox runner 运行。"
)
AGENT_STREAM_LENGTH_BOUNDARY_MESSAGE = "模型输出超过 Agent 单次流式回答上限，本次运行已停止，避免长时间占用会话。"
SOLO_CONFIRMATION_BOUNDARY_MESSAGE = (
    "Solo 模式不支持用户确认式工具调用；模型应自行评估风险，风险可控则自动执行，"
    "高风险则中断任务并说明原因。"
)
SOLO_CONFIRMATION_MARKERS = (
    "请确认",
    "请您确认",
    "待执行操作",
    "是否需要我",
    "是否执行",
    "需要我直接执行",
    "please confirm",
    "awaiting confirmation",
    "should i execute",
    "do you want me to run",
)

repository: AIApplicationsRepository | None = None


def configure_repository(ai_applications_repository: AIApplicationsRepository) -> None:
    global repository
    repository = ai_applications_repository


class GatewaySkillLLMTaskRunner:
    def __init__(self, *, model: str, temperature: float | None, extra_body: dict[str, Any] | None = None) -> None:
        self.model = model
        self.temperature = temperature
        self.extra_body = dict(extra_body or {})

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        messages = build_llm_task_skill_messages(request)
        response = gateway.chat_completions(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            extra_body=self.extra_body,
            correlation_id=f"skill_llm_{uuid.uuid4().hex}",
        )
        answer = extract_answer(response)
        output = {
            "summary": "Skill executed as an LLM task.",
            "answer": answer,
            "artifacts": llm_task_artifacts(answer, request),
        }
        return {"status": "success", "output": output}


class AgentExecutionBoundaryError(RuntimeError):
    pass


def repo() -> AIApplicationsRepository:
    if repository is None:
        raise RuntimeError("ai applications repository is not configured")
    return repository


def studio_overview(current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            repo().require_ai_applications_schema(conn)
            data_scope = ai_application_data_scope(current_user, action="read")
            apps = repo().list_ai_applications(conn, data_scope=data_scope)
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
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data_scope = ai_application_data_scope(current_user, action="read")
    return read_list(
        lambda conn: repo().list_ai_applications(conn, data_scope=data_scope),
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


def ai_application_data_scope(current_user: dict[str, Any] | None, *, action: str) -> Any:
    if current_user is None:
        return None
    return resolve_data_access_filter(current_user=current_user, resource=AI_APPLICATION_RESOURCE, action=action)


def ensure_ai_application_access(
    app: dict[str, Any],
    *,
    current_user: dict[str, Any] | None,
    action: str,
) -> None:
    if current_user is None:
        return
    predicate = ai_application_data_scope(current_user, action=action)
    if predicate is None or predicate.allows_record(app, AI_APPLICATION_RESOURCE):
        return
    raise HTTPException(status_code=404, detail="AI application not found")


def actor_payload(current_user: dict[str, Any] | None) -> dict[str, Any]:
    if current_user is None:
        return {}
    return {
        "actor": str(current_user.get("nickname") or current_user.get("name") or current_user.get("username") or "").strip(),
        "actor_id": current_user_id_or_none(current_user),
        "owner_department_id": current_user_primary_department_id(current_user),
    }


def get_ai_application(app_key: str, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    data_scope = ai_application_data_scope(current_user, action="read")
    app = read_one(lambda conn: repo().get_ai_application(conn, app_key, data_scope=data_scope))
    if not app:
        raise HTTPException(status_code=404, detail="AI application not found")
    return app


def save_ai_application(payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            existing = repo().get_ai_application(conn, str(payload.get("app_key") or ""))
            if not existing:
                enforce_application_quota(conn)
            else:
                ensure_ai_application_access(existing, current_user=current_user, action="write")
            normalize_application_payload(payload)
            payload.update(actor_payload(current_user))
            return repo().upsert_ai_application(conn, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def publish_ai_application(app_key: str, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            app = repo().get_ai_application(conn, app_key)
            if not app:
                raise HTTPException(status_code=404, detail="AI application not found")
            ensure_ai_application_access(app, current_user=current_user, action="write")
            validate_publishable(app)
            return repo().publish_ai_application(conn, app_key)
    except HTTPException:
        raise
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def export_ai_application_workflow(app_key: str, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    app = require_workflow_application(app_key, current_user=current_user)
    workflow = copy.deepcopy(workflow_definition_from_app(app))
    validate_workflow_definition_payload(workflow)
    return {
        "kind": WORKFLOW_EXPORT_KIND,
        "schema_version": WORKFLOW_EXPORT_SCHEMA_VERSION,
        "source_app": {
            "app_key": app.get("app_key"),
            "name": app.get("name"),
        },
        "workflow": workflow,
    }


def import_ai_application_workflow(app_key: str, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    workflow = workflow_definition_from_import_payload(payload)
    validate_workflow_definition_payload(workflow)
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            app = repo().get_ai_application(conn, app_key)
            if not app:
                raise HTTPException(status_code=404, detail="AI application not found")
            ensure_ai_application_access(app, current_user=current_user, action="write")
            if app.get("app_type") != "workflow":
                raise HTTPException(status_code=422, detail="Only workflow applications support workflow import")
            updated = dict(app)
            runtime_config = dict(app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {})
            runtime_config["workflow"] = workflow
            updated["runtime_config"] = runtime_config
            normalize_application_payload(updated)
            updated.update(actor_payload(current_user))
            imported = repo().upsert_ai_application(conn, updated)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    return {"application": imported, "workflow": workflow}


def run_draft_application(app_key: str, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    app = get_ai_application(app_key, current_user=current_user)
    return execute_application(app, payload, caller_type="studio_draft", require_published=False, current_user=current_user)


def stream_draft_application(app_key: str, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> Any:
    app = get_ai_application(app_key, current_user=current_user)
    if app.get("app_type") == "workflow":
        return stream_workflow_application(app, payload, caller_type="studio_draft", require_published=False, current_user=current_user)
    if app.get("app_type") == "agent":
        raise HTTPException(status_code=422, detail="Agent applications must run through agent conversation APIs")
    try:
        prepared = prepare_single_turn_run(app, payload, require_published=False)
    except skill_runtime.SkillRuntimeError as exc:
        raise skill_http_error(exc) from exc
    return stream_single_turn_application(prepared, caller_type="studio_draft")


def run_published_application(app_key: str, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    app = get_ai_application(app_key, current_user=current_user)
    return execute_application(app, payload, caller_type="application_api", require_published=True, current_user=current_user)


def list_agent_conversations(
    app_key: str,
    *,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    app = require_agent_application(app_key, current_user=current_user)
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


def create_agent_conversation(app_key: str, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    app = require_agent_application(app_key, current_user=current_user)
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            repo().require_ai_agent_schema(conn)
            return repo().create_agent_conversation(conn, app["app_key"], payload)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def skill_http_error(exc: skill_runtime.SkillRuntimeError) -> HTTPException:
    return HTTPException(status_code=422, detail={"message": str(exc), "code": "SKILL_RUNTIME_ERROR"})


def list_agent_messages(
    app_key: str,
    conversation_key: str,
    *,
    page: int = 1,
    page_size: int = 50,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    app = require_agent_application(app_key, current_user=current_user)
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


def send_agent_message(
    app_key: str,
    conversation_key: str,
    payload: dict[str, Any],
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        prepared = prepare_agent_run(app_key, conversation_key, payload, current_user=current_user)
    except skill_runtime.SkillRuntimeError as exc:
        raise skill_http_error(exc) from exc
    trace_id = f"trace_{uuid.uuid4().hex}"
    started_at = time.perf_counter()
    answer = ""
    usage: dict[str, Any] = {}
    try:
        agent_run = run_agent_model_with_file_tools(prepared, payload, trace_id=trace_id)
        answer = agent_run["answer"]
        usage = agent_run["usage"]
        run_error = agent_run.get("error") if isinstance(agent_run.get("error"), Exception) else None
        run_status = str(agent_run.get("status") or "success")
        trace = record_trace(
            trace_id=trace_id,
            app=prepared["app"],
            caller_type="ai_agent",
            caller_key=prepared["conversation"]["conversation_key"],
            model=prepared["model"],
            status=run_status,
            variables=prepared["variables"],
            messages=agent_run["messages"],
            rendered_prompt=agent_run["rendered_prompt"],
            answer=answer,
            usage=usage,
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            error=run_error,
            prompt_refs=prepared["prompt_refs"],
        )
        assistant_message = persist_agent_assistant_message(
            prepared,
            content=answer,
            status="completed" if run_status == "success" else "failed",
            trace_id=trace_id,
            error=run_error,
        )
        return {
            "conversation": prepared["conversation"],
            "user_message": prepared["user_message"],
            "tool_messages": [*prepared.get("tool_messages", []), *agent_run.get("agent_tool_messages", [])],
            "skill_plan": {
                "skills": skill_runtime.toolbox_snapshot(prepared["skill_plan"]),
                "planned_calls": skill_runtime.skill_calls_snapshot(prepared["skill_plan"].planned_calls),
            },
            "agent_file_workspace": agent_tools.snapshot(prepared.get("file_workspace")),
            "agent_tool_results": agent_run.get("agent_tool_results", []),
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


def stream_agent_message(
    app_key: str,
    conversation_key: str,
    payload: dict[str, Any],
    current_user: dict[str, Any] | None = None,
) -> Any:
    try:
        prepared = prepare_agent_run(app_key, conversation_key, payload, current_user=current_user)
    except skill_runtime.SkillRuntimeError as exc:
        raise skill_http_error(exc) from exc
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
        stream_tool_marker_count = 0
        stream_recent_text = ""
        streamed_tool_rounds = 0
        stream_messages = prepared["messages"]
        stream_rendered_prompt = prepared["rendered_prompt"]
        stream_tool_results: list[dict[str, Any]] = []
        stream_tool_messages: list[dict[str, Any]] = []

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
                messages=stream_messages,
                rendered_prompt=stream_rendered_prompt,
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
        skill_plan = prepared.get("skill_plan")
        if skill_plan:
            yield emit_named(
                "skill_plan",
                {
                    "trace_id": trace_id,
                    "skills": skill_runtime.toolbox_snapshot(skill_plan),
                    "planned_calls": skill_runtime.skill_calls_snapshot(skill_plan.planned_calls),
                    "object": "ai_application.skill.plan",
                },
            )
        for result in prepared.get("skill_results", []):
            yield emit_named(
                "skill_result",
                {
                    "trace_id": trace_id,
                    "skill": result.to_trace(),
                    "object": "ai_application.skill.result",
                },
            )
        try:
            if agent_file_tool_stream_preflight_required(prepared, payload):
                preflight = run_agent_file_tool_preflight(prepared, payload, trace_id=trace_id)
                stream_tool_results = preflight.get("agent_tool_results", [])
                stream_tool_messages = preflight.get("agent_tool_messages", [])
                if stream_tool_results:
                    stream_messages = preflight["messages"]
                    stream_rendered_prompt = preflight["rendered_prompt"]
                    yield emit_named(
                        "agent_tool_result",
                        {
                            "trace_id": trace_id,
                            "results": stream_tool_results,
                            "tool_messages": stream_tool_messages,
                            "object": "ai_application.agent.tools.result",
                        },
                    )
                if preflight.get("boundary_answer"):
                    boundary_answer = str(preflight["boundary_answer"])
                    boundary_error = preflight.get("boundary_error")
                    if not isinstance(boundary_error, Exception):
                        boundary_error = agent_execution_boundary_error(boundary_answer)
                    answer_parts.append(boundary_answer)
                    yield agent_boundary_stream_event(boundary_answer)
                    trace = finish("failed", boundary_error)
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
                    return
            continue_stream = True
            while continue_stream:
                continue_stream = False
                protocol_buffer = ""
                for event in gateway.stream_chat_completions(
                    model=prepared["model"],
                    messages=stream_messages,
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
                    content_delta = gateway.stream_event_content(event)
                    visible_delta = stream_event_visible_text(event)
                    if not visible_delta:
                        answer_parts.append(content_delta)
                        yield event
                        continue
                    protocol_start = raw_agent_tool_protocol_start(visible_delta)
                    protocol_fragment = visible_delta if protocol_buffer else ""
                    safe_visible_delta = "" if protocol_buffer else visible_delta
                    if protocol_start >= 0 and not protocol_buffer:
                        safe_visible_delta = visible_delta[:protocol_start]
                        protocol_fragment = visible_delta[protocol_start:]
                    safe_content_delta = content_delta
                    if protocol_fragment:
                        if protocol_start >= 0 and content_delta and visible_delta == content_delta:
                            safe_content_delta = content_delta[:protocol_start]
                        elif protocol_buffer or protocol_start >= 0:
                            safe_content_delta = ""
                    if safe_visible_delta:
                        stream_tool_marker_count += raw_agent_tool_marker_count(safe_visible_delta)
                        stream_recent_text = (stream_recent_text + safe_visible_delta)[-8000:]
                        recent_tool_marker_count = raw_agent_tool_marker_count(stream_recent_text)
                        if len("".join(answer_parts)) + len(safe_visible_delta) > AGENT_STREAM_MAX_ANSWER_CHARS:
                            boundary_error = agent_execution_boundary_error(AGENT_STREAM_LENGTH_BOUNDARY_MESSAGE)
                            answer_parts.append(AGENT_STREAM_LENGTH_BOUNDARY_MESSAGE)
                            yield agent_boundary_stream_event(AGENT_STREAM_LENGTH_BOUNDARY_MESSAGE)
                            trace = finish("failed", boundary_error)
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
                            return
                        if solo_confirmation_requested(stream_recent_text):
                            boundary_error = agent_execution_boundary_error(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                            answer_parts.append(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                            yield agent_boundary_stream_event(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                            trace = finish("failed", boundary_error)
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
                            return
                        answer_parts.append(safe_content_delta)
                        if protocol_fragment:
                            yield agent_stream_delta_event(safe_visible_delta)
                        else:
                            yield event
                    if not protocol_fragment:
                        continue
                    protocol_buffer += protocol_fragment
                    protocol_status = streamed_tool_protocol_status(protocol_buffer)
                    if protocol_status == "pending":
                        continue
                    if protocol_status == "confirmation":
                        boundary_error = agent_execution_boundary_error(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                        answer_parts.append(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                        yield agent_boundary_stream_event(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                        trace = finish("failed", boundary_error)
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
                        return
                    if protocol_status == "request":
                        streamed_tool_rounds += 1
                        if streamed_tool_rounds > 2:
                            boundary_error = agent_execution_boundary_error()
                            answer_parts.append(AGENT_UNHANDLED_TOOL_CALL_MESSAGE)
                            yield agent_boundary_stream_event(AGENT_UNHANDLED_TOOL_CALL_MESSAGE)
                            trace = finish("failed", boundary_error)
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
                            return
                        executed = execute_agent_tool_request(prepared, stream_messages, protocol_buffer, trace_id=trace_id)
                        new_results = executed.get("agent_tool_results", [])
                        new_messages = executed.get("agent_tool_messages", [])
                        if new_results:
                            stream_tool_results.extend(new_results)
                            stream_tool_messages.extend(new_messages)
                            yield emit_named(
                                "agent_tool_result",
                                {
                                    "trace_id": trace_id,
                                    "results": new_results,
                                    "tool_messages": new_messages,
                                    "object": "ai_application.agent.tools.result",
                                },
                            )
                        if executed.get("boundary_answer"):
                            boundary_answer = str(executed["boundary_answer"])
                            boundary_error = executed.get("boundary_error")
                            if not isinstance(boundary_error, Exception):
                                boundary_error = agent_execution_boundary_error(boundary_answer)
                            answer_parts.append(boundary_answer)
                            yield agent_boundary_stream_event(boundary_answer)
                            trace = finish("failed", boundary_error)
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
                            return
                        stream_messages = executed["messages"]
                        stream_rendered_prompt = executed["rendered_prompt"]
                        stream_tool_marker_count = 0
                        stream_recent_text = ""
                        continue_stream = True
                        break
                    boundary_error = agent_execution_boundary_error()
                    answer_parts.append(AGENT_UNHANDLED_TOOL_CALL_MESSAGE)
                    yield agent_boundary_stream_event(AGENT_UNHANDLED_TOOL_CALL_MESSAGE)
                    trace = finish("failed", boundary_error)
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
                    return
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
    app_key: str,
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    app = get_ai_application(app_key, current_user=current_user)
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
        if "ai applications repository is not configured" in str(exc) or "ai_applications storage is not initialized" in str(exc):
            return False
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


def skill_asset_is_referenced(*, tenant_id: int, skill_key: str) -> bool:
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            repo().require_ai_applications_schema(conn)
            return repo().skill_asset_is_referenced_by_ai_application(
                conn,
                tenant_id=tenant_id,
                skill_key=skill_key,
            )
    except RuntimeError as exc:
        if "ai applications repository is not configured" in str(exc) or "ai_applications storage is not initialized" in str(exc):
            return False
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


prompt_asset_services.register_prompt_asset_reference_checker(
    lambda tenant_id, prompt_key: prompt_asset_is_referenced(tenant_id=tenant_id, prompt_key=prompt_key)
)
prompt_asset_services.register_skill_asset_reference_checker(
    lambda tenant_id, skill_key: skill_asset_is_referenced(tenant_id=tenant_id, skill_key=skill_key)
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

    try:
        prepared = prepare_single_turn_run(app, payload, require_published=require_published)
    except skill_runtime.SkillRuntimeError as exc:
        raise skill_http_error(exc) from exc
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
        single_turn_run = run_single_turn_model_with_tools(prepared, payload, trace_id=trace_id)
        answer = single_turn_run["answer"]
        usage = single_turn_run["usage"]
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        run_error = single_turn_run.get("error") if isinstance(single_turn_run.get("error"), Exception) else None
        run_status = str(single_turn_run.get("status") or "success")
        trace = record_trace(
            trace_id=trace_id,
            app=app_for_run,
            caller_type=caller_type,
            caller_key=caller_key,
            model=model,
            status=run_status,
            variables=variables,
            messages=single_turn_run["messages"],
            rendered_prompt=single_turn_run["rendered_prompt"],
            answer=answer,
            usage=usage,
            elapsed_ms=elapsed_ms,
            error=run_error,
            prompt_refs=prompt_refs,
        )
        return {
            "answer": answer,
            "trace_id": trace_id,
            "usage": usage,
            "trace": trace,
            "agent_tool_results": single_turn_run.get("agent_tool_results", []),
        }
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
        workflow_result = execute_workflow(
            definition,
            variables,
            llm_executor=llm_executor,
            sql_executor=sql_executor,
        )
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
    caller_key: str | None = None,
    current_user: dict[str, Any] | None = None,
) -> Any:
    def events() -> Any:
        trace_id = f"trace_{uuid.uuid4().hex}"
        started_at = time.perf_counter()
        variables: dict[str, Any] = {}
        rendered_messages: list[dict[str, Any]] = []
        rendered_prompt = ""
        model = ""
        answer = ""
        usage: dict[str, Any] = {}
        trace_nodes: list[dict[str, Any]] = []

        def trace_event(trace: dict[str, Any]) -> str:
            return workflow_stream_event(
                "trace",
                {"trace_id": trace_id, "trace": trace, "object": "ai_application.run.trace"},
            )

        def node_event(event_name: str, node: dict[str, Any]) -> str:
            return workflow_stream_event(
                "workflow_node",
                {
                    "trace_id": trace_id,
                    "event": event_name,
                    "node": node,
                    "object": "ai_application.workflow.node",
                },
            )

        try:
            if require_published and app.get("status") != "published":
                raise HTTPException(status_code=409, detail="AI application is not published")
            variables = extract_run_variables(payload)
            definition = workflow_definition_from_app(app)
            validate_workflow_variables(definition, variables)
            model = resolve_workflow_default_model(app, payload, definition)
            yield workflow_stream_event(
                "meta",
                {"trace_id": trace_id, "model": model, "object": "ai_application.workflow.start"},
            )

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
                rendered_prompt = gateway.prompt_from_messages(
                    prompt=None,
                    messages=gateway.messages_as_text_messages(request.messages),
                )
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

            workflow_result = None
            for workflow_event in iter_workflow_events(
                definition,
                variables,
                llm_executor=llm_executor,
                sql_executor=sql_executor,
            ):
                event_name = str(workflow_event.get("event") or "")
                node = workflow_event.get("node")
                if isinstance(node, dict):
                    upsert_latest_workflow_trace_node(trace_nodes, node)
                    yield node_event(event_name, node)
                    continue
                if event_name == "workflow.completed":
                    workflow_result = workflow_event.get("result")
            if workflow_result is None:
                raise WorkflowRuntimeError("workflow did not complete")
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
            if answer:
                yield workflow_stream_event(None, {"choices": [{"delta": {"content": answer}}]})
            yield trace_event(trace)
            yield "data: [DONE]\n\n"
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            yield gateway.sse_error(str(detail.get("message") or exc.detail))
            yield "data: [DONE]\n\n"
        except (WorkflowRuntimeError, gateway.LLMRoutingError, RuntimeError) as exc:
            trace = record_trace(
                trace_id=trace_id,
                app=app,
                caller_type=caller_type,
                caller_key=caller_key,
                model=model,
                status="failed",
                variables=variables,
                messages=workflow_trace_messages(rendered_messages, {"workflow": {"nodes": trace_nodes}} if trace_nodes else {}),
                rendered_prompt=rendered_prompt,
                answer=answer,
                usage=usage,
                elapsed_ms=int((time.perf_counter() - started_at) * 1000),
                error=exc,
            )
            yield gateway.sse_error(str(exc))
            yield trace_event(trace)
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
    limit = max(1, min(1000, int(request.max_rows or 100)))
    config = request.data_access if isinstance(request.data_access, dict) else {}
    try:
        guarded_sql, guarded_params = inject_data_access_into_select(
            SQLDataAccessInjectionRequest(
                sql=request.sql,
                params=tuple(request.params),
                resource=descriptor,
                predicate=predicate,
                dialect=str(config.get("dialect") or config.get("sql_dialect") or database_backend()),
                source_table=str(config.get("source_table") or ""),
                source_alias=str(config.get("source_alias") or ""),
            )
        )
    except SQLDataAccessInjectionError as exc:
        raise WorkflowRuntimeError(f"SQL 节点数据权限注入失败：{exc}") from exc
    guarded_sql = f"SELECT * FROM ({guarded_sql}) AS workflow_sql_source LIMIT ?"
    params = [*guarded_params, limit + 1]
    database_target = require_database()
    try:
        with connect(database_target, readonly=True) as conn:
            cursor = conn.execute(guarded_sql, tuple(params))
            rows = cursor.fetchall()
    except Exception as exc:
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
    has_tenant_column = "tenant_column" in config
    tenant_column = str(config.get("tenant_column")) if has_tenant_column and config.get("tenant_column") is not None else "tenant_id"
    tenant_column = tenant_column.strip()
    return ResourceDescriptor(
        resource_key=str(config.get("resource_key") or "ai_applications.workflow_sql"),
        access_mode=str(config.get("access_mode") or "owner_columns"),
        tenant_column=tenant_column,
        resource_id_column=str(config.get("resource_id_column") or "id").strip(),
        creator_column=str(config.get("creator_column") or "creator_id"),
        owner_user_column=str(config.get("owner_user_column") or "owner_user_id"),
        owner_department_column=str(config.get("owner_department_column") or "owner_department_id"),
        relation_table=str(config.get("relation_table") or "").strip(),
        relation_resource_id_column=str(config.get("relation_resource_id_column") or "").strip(),
        relation_user_column=str(config.get("relation_user_column") or "").strip(),
        relation_department_column=str(config.get("relation_department_column") or "").strip(),
        relation_tenant_column=str(config.get("relation_tenant_column") or "tenant_id").strip(),
        relation_deleted_column=str(config.get("relation_deleted_column") or "deleted").strip(),
        relation_resource_key_column=str(config.get("relation_resource_key_column") or "").strip(),
        relation_resource_key_value=str(config.get("relation_resource_key_value") or "").strip(),
        relation_subject_type_column=str(config.get("relation_subject_type_column") or "").strip(),
        relation_subject_type_user_value=str(config.get("relation_subject_type_user_value") or "").strip(),
        relation_subject_type_department_value=str(config.get("relation_subject_type_department_value") or "").strip(),
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
        "is_tenant_admin": True,
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
    model = resolve_model(app_for_run, payload)
    temperature = resolve_temperature(app_for_run, payload)
    configure_skill_llm_task_runner(app_for_run, payload, model=model, temperature=temperature)
    skill_plan = skill_runtime.prepare_skill_runtime(
        app_for_run,
        payload,
        variables,
        app_type="single_turn_generation",
    )
    planning_content = render_template(str(app_for_run.get("user_prompt_template") or ""), variables)
    plan_agent_skills_if_enabled(
        app_for_run,
        payload,
        variables,
        planning_content,
        skill_plan,
        model=model,
        temperature=temperature,
        app_type="single_turn_generation",
    )
    skill_results = skill_runtime.execute_pre_model_skills(skill_plan)
    variables = skill_runtime.merge_skill_results_into_variables(variables, skill_plan, skill_results)
    validate_variables(app_for_run, variables)
    collected_files = skill_runtime.collect_files(payload, variables)
    if single_turn_tools_requested(app_for_run, payload, collected_files):
        try:
            file_workspace = agent_file_tools.prepare_workspace(
                app_for_run,
                {"conversation_key": f"single_turn_{uuid.uuid4().hex}"},
                payload,
                collected_files,
                skill_plan=skill_plan,
            )
        except agent_file_tools.AgentFileToolError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    else:
        file_workspace = {"enabled": False}

    messages = render_messages(app_for_run, variables)
    messages = skill_runtime.append_skill_context_messages(messages, skill_plan, skill_results)
    messages = append_developer_context_message(messages, agent_tools.build_prompt(file_workspace))
    rendered_prompt = gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages))
    return {
        "app": app_for_run,
        "payload": payload,
        "variables": variables,
        "messages": messages,
        "rendered_prompt": rendered_prompt,
        "model": model,
        "temperature": temperature,
        "response_format": resolve_response_format(app_for_run, payload),
        "prompt_refs": prompt_refs,
        "skill_plan": skill_plan,
        "skill_results": skill_results,
        "file_workspace": file_workspace,
    }


def single_turn_tools_requested(app: dict[str, Any], payload: dict[str, Any], files: list[dict[str, Any]]) -> bool:
    for key in ("file_tools_enabled", "agent_tools_enabled", "tool_preflight", "agent_tool_preflight", "file_tool_preflight"):
        request_value = agent_file_tools.optional_bool(payload.get(key))
        if request_value is not None:
            return request_value
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    agent_tool_config = runtime_config.get("agent_tools") if isinstance(runtime_config.get("agent_tools"), dict) else {}
    for key in ("enabled", "preflight"):
        config_value = agent_file_tools.optional_bool(agent_tool_config.get(key))
        if config_value is not None:
            return config_value
    file_tool_config = runtime_config.get("file_tools") if isinstance(runtime_config.get("file_tools"), dict) else {}
    config_value = agent_file_tools.optional_bool(file_tool_config.get("enabled"))
    if config_value is not None:
        return config_value
    return bool(files)


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
    skill_plan = prepared.get("skill_plan")
    skill_results = prepared.get("skill_results") if isinstance(prepared.get("skill_results"), list) else []
    trace_id = f"trace_{uuid.uuid4().hex}"
    started_at = time.perf_counter()

    def events() -> Any:
        answer_parts: list[str] = []
        error: Exception | None = None
        trace_recorded = False
        stream_tool_marker_count = 0
        stream_recent_text = ""
        stream_messages = messages
        stream_rendered_prompt = rendered_prompt

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
                messages=stream_messages,
                rendered_prompt=stream_rendered_prompt,
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
        if skill_plan:
            yield gateway.sse_data(
                {
                    "trace_id": trace_id,
                    "skills": skill_runtime.toolbox_snapshot(skill_plan),
                    "planned_calls": skill_runtime.skill_calls_snapshot(skill_plan.planned_calls),
                    "object": "ai_application.skill.plan",
                }
            ).replace("data: ", "event: skill_plan\ndata: ", 1)
        for result in skill_results:
            yield gateway.sse_data(
                {
                    "trace_id": trace_id,
                    "skill": result.to_trace(),
                    "object": "ai_application.skill.result",
                }
            ).replace("data: ", "event: skill_result\ndata: ", 1)
        try:
            if single_turn_tool_stream_preflight_required(prepared, payload):
                preflight = run_single_turn_tool_preflight(prepared, payload, trace_id=trace_id)
                stream_tool_results = preflight.get("agent_tool_results", [])
                if stream_tool_results:
                    stream_messages = preflight["messages"]
                    stream_rendered_prompt = preflight["rendered_prompt"]
                    yield gateway.sse_data(
                        {
                            "trace_id": trace_id,
                            "results": stream_tool_results,
                            "object": "ai_application.agent.tools.result",
                        }
                    ).replace("data: ", "event: agent_tool_result\ndata: ", 1)
                if preflight.get("boundary_answer"):
                    boundary_answer = str(preflight["boundary_answer"])
                    boundary_error = preflight.get("error")
                    if not isinstance(boundary_error, Exception):
                        boundary_error = agent_execution_boundary_error(boundary_answer)
                    answer_parts.append(boundary_answer)
                    yield tool_call_blocked_event(trace_id, boundary_answer)
                    trace = finish_trace("failed", boundary_error)
                    yield trace_event(trace)
                    yield "data: [DONE]\n\n"
                    return
            continue_stream = True
            streamed_tool_rounds = 0
            while continue_stream:
                continue_stream = False
                protocol_buffer = ""
                for event in gateway.stream_chat_completions(
                    model=model,
                    messages=stream_messages,
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
                    content_delta = gateway.stream_event_content(event)
                    visible_delta = stream_event_visible_text(event)
                    if not visible_delta:
                        answer_parts.append(content_delta)
                        yield event
                        continue
                    protocol_start = raw_agent_tool_protocol_start(visible_delta)
                    protocol_fragment = visible_delta if protocol_buffer else ""
                    safe_visible_delta = "" if protocol_buffer else visible_delta
                    if protocol_start >= 0 and not protocol_buffer:
                        safe_visible_delta = visible_delta[:protocol_start]
                        protocol_fragment = visible_delta[protocol_start:]
                    safe_content_delta = content_delta
                    if protocol_fragment:
                        if protocol_start >= 0 and content_delta and visible_delta == content_delta:
                            safe_content_delta = content_delta[:protocol_start]
                        elif protocol_buffer or protocol_start >= 0:
                            safe_content_delta = ""
                    if safe_visible_delta:
                        stream_tool_marker_count += raw_agent_tool_marker_count(safe_visible_delta)
                        stream_recent_text = (stream_recent_text + safe_visible_delta)[-8000:]
                        recent_tool_marker_count = raw_agent_tool_marker_count(stream_recent_text)
                        if len("".join(answer_parts)) + len(safe_visible_delta) > AGENT_STREAM_MAX_ANSWER_CHARS:
                            boundary_error = agent_execution_boundary_error(AGENT_STREAM_LENGTH_BOUNDARY_MESSAGE)
                            answer_parts.append(AGENT_STREAM_LENGTH_BOUNDARY_MESSAGE)
                            yield tool_call_blocked_event(trace_id, AGENT_STREAM_LENGTH_BOUNDARY_MESSAGE)
                            trace = finish_trace("failed", boundary_error)
                            yield trace_event(trace)
                            yield "data: [DONE]\n\n"
                            return
                        if solo_confirmation_requested(stream_recent_text):
                            boundary_error = agent_execution_boundary_error(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                            answer_parts.append(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                            yield tool_call_blocked_event(trace_id, SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                            trace = finish_trace("failed", boundary_error)
                            yield trace_event(trace)
                            yield "data: [DONE]\n\n"
                            return
                        answer_parts.append(safe_content_delta)
                        if protocol_fragment:
                            yield agent_stream_delta_event(safe_visible_delta)
                        else:
                            yield event
                    if not protocol_fragment:
                        continue
                    protocol_buffer += protocol_fragment
                    protocol_status = streamed_tool_protocol_status(protocol_buffer)
                    if protocol_status == "pending":
                        continue
                    if protocol_status == "confirmation":
                        boundary_error = agent_execution_boundary_error(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                        answer_parts.append(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                        yield tool_call_blocked_event(trace_id, SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
                        trace = finish_trace("failed", boundary_error)
                        yield trace_event(trace)
                        yield "data: [DONE]\n\n"
                        return
                    if protocol_status == "request":
                        streamed_tool_rounds += 1
                        if streamed_tool_rounds > 2:
                            boundary_error = agent_execution_boundary_error()
                            answer_parts.append(AGENT_UNHANDLED_TOOL_CALL_MESSAGE)
                            yield tool_call_blocked_event(trace_id)
                            trace = finish_trace("failed", boundary_error)
                            yield trace_event(trace)
                            yield "data: [DONE]\n\n"
                            return
                        executed = execute_single_turn_stream_tool_request(prepared, stream_messages, protocol_buffer)
                        new_results = executed.get("agent_tool_results", [])
                        if new_results:
                            yield gateway.sse_data(
                                {
                                    "trace_id": trace_id,
                                    "results": new_results,
                                    "object": "ai_application.agent.tools.result",
                                }
                            ).replace("data: ", "event: agent_tool_result\ndata: ", 1)
                        if executed.get("boundary_answer"):
                            boundary_answer = str(executed["boundary_answer"])
                            boundary_error = executed.get("error")
                            if not isinstance(boundary_error, Exception):
                                boundary_error = agent_execution_boundary_error(boundary_answer)
                            answer_parts.append(boundary_answer)
                            yield tool_call_blocked_event(trace_id, boundary_answer)
                            trace = finish_trace("failed", boundary_error)
                            yield trace_event(trace)
                            yield "data: [DONE]\n\n"
                            return
                        stream_messages = executed["messages"]
                        stream_rendered_prompt = executed["rendered_prompt"]
                        stream_tool_marker_count = 0
                        stream_recent_text = ""
                        continue_stream = True
                        break
                    boundary_error = agent_execution_boundary_error()
                    answer_parts.append(AGENT_UNHANDLED_TOOL_CALL_MESSAGE)
                    yield tool_call_blocked_event(trace_id)
                    trace = finish_trace("failed", boundary_error)
                    yield trace_event(trace)
                    yield "data: [DONE]\n\n"
                    return
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


def run_single_turn_model_with_tools(prepared: dict[str, Any], payload: dict[str, Any], *, trace_id: str) -> dict[str, Any]:
    response = gateway.chat_completions(
        model=prepared["model"],
        messages=prepared["messages"],
        temperature=prepared["temperature"],
        response_format=prepared["response_format"],
        extra_body=resolve_extra_body(prepared["app"], payload),
        enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
        correlation_id=trace_id,
    )
    first_answer = extract_answer(response)
    first_usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    request = agent_tools.parse_tool_request(first_answer)
    workspace = prepared.get("file_workspace")
    if not workspace or not workspace.get("enabled") or not request.get("tool_calls"):
        answer = agent_tools.protocol_final_answer(first_answer) or first_answer
        if solo_confirmation_requested(answer):
            return single_turn_failed_model_run(prepared, message=SOLO_CONFIRMATION_BOUNDARY_MESSAGE, usage=first_usage)
        return {
            "answer": answer,
            "usage": first_usage,
            "messages": prepared["messages"],
            "rendered_prompt": prepared["rendered_prompt"],
            "agent_tool_results": [],
            "status": "success",
        }

    tool_results = agent_tools.execute_tool_calls(
        workspace,
        request["tool_calls"],
        run_context=single_turn_tool_run_context(prepared),
    )
    if agent_tools.contains_high_risk_result(tool_results):
        return single_turn_failed_model_run(
            prepared,
            message=agent_tools.high_risk_failure_message(tool_results),
            usage=first_usage,
            tool_results=tool_results,
        )
    follow_up_messages = agent_tools.build_follow_up_messages(prepared["messages"], first_answer, tool_results)
    follow_up_response = gateway.chat_completions(
        model=prepared["model"],
        messages=follow_up_messages,
        temperature=prepared["temperature"],
        response_format=prepared["response_format"],
        extra_body=resolve_extra_body(prepared["app"], payload),
        enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
        correlation_id=f"{trace_id}_final",
    )
    final_answer = extract_answer(follow_up_response)
    follow_up_usage = follow_up_response.get("usage") if isinstance(follow_up_response.get("usage"), dict) else {}
    usage = agent_tools.merge_usage(first_usage, follow_up_usage)
    if raw_agent_tool_marker_count(final_answer) > 0 or raw_agent_unsupported_tool_detected(final_answer) or agent_tools.parse_tool_request(final_answer).get("tool_calls"):
        return single_turn_failed_model_run(
            prepared,
            message=AGENT_UNHANDLED_TOOL_CALL_MESSAGE,
            usage=usage,
            messages=follow_up_messages,
            tool_results=tool_results,
        )
    if solo_confirmation_requested(final_answer):
        return single_turn_failed_model_run(
            prepared,
            message=SOLO_CONFIRMATION_BOUNDARY_MESSAGE,
            usage=usage,
            messages=follow_up_messages,
            tool_results=tool_results,
        )
    return {
        "answer": final_answer,
        "usage": usage,
        "messages": follow_up_messages,
        "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(follow_up_messages)),
        "agent_tool_results": tool_results,
        "status": "success",
    }


def single_turn_failed_model_run(
    prepared: dict[str, Any],
    *,
    message: str,
    usage: dict[str, Any],
    messages: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    run_messages = messages or prepared["messages"]
    rendered_prompt = (
        prepared["rendered_prompt"]
        if run_messages is prepared["messages"]
        else gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(run_messages))
    )
    return {
        "answer": message,
        "usage": usage,
        "messages": run_messages,
        "rendered_prompt": rendered_prompt,
        "agent_tool_results": tool_results or [],
        "status": "failed",
        "error": agent_execution_boundary_error(message),
    }


def single_turn_tool_stream_preflight_required(prepared: dict[str, Any], payload: dict[str, Any]) -> bool:
    workspace = prepared.get("file_workspace")
    if not workspace or not workspace.get("enabled"):
        return False
    request_value = agent_file_tools.optional_bool(payload.get("tool_preflight"))
    if request_value is not None:
        return request_value
    request_value = agent_file_tools.optional_bool(payload.get("agent_tool_preflight"))
    if request_value is not None:
        return request_value
    runtime_config = prepared.get("app", {}).get("runtime_config") if isinstance(prepared.get("app"), dict) else {}
    if not isinstance(runtime_config, dict):
        runtime_config = {}
    tool_config = runtime_config.get("agent_tools") if isinstance(runtime_config.get("agent_tools"), dict) else {}
    config_value = agent_file_tools.optional_bool(tool_config.get("preflight"))
    if config_value is not None:
        return config_value
    return bool(workspace.get("uploads"))


def run_single_turn_tool_preflight(prepared: dict[str, Any], payload: dict[str, Any], *, trace_id: str) -> dict[str, Any]:
    response = gateway.chat_completions(
        model=prepared["model"],
        messages=[
            *prepared["messages"],
            {
                "role": "user",
                "content": (
                    "If tools are needed to complete the user's single-turn task, return tool_calls JSON now. "
                    "Use file tools, shell.run, or python.run only. "
                    "Otherwise return {\"tool_calls\":[]}."
                ),
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
        extra_body=resolve_extra_body(prepared["app"], payload),
        enable_think_output=False,
        correlation_id=f"{trace_id}_tools",
    )
    preflight_answer = extract_answer(response)
    request = agent_tools.parse_tool_request(preflight_answer)
    if solo_confirmation_requested(preflight_answer):
        boundary_error = agent_execution_boundary_error(SOLO_CONFIRMATION_BOUNDARY_MESSAGE)
        return {
            "messages": prepared["messages"],
            "rendered_prompt": prepared["rendered_prompt"],
            "agent_tool_results": [],
            "status": "failed",
            "error": boundary_error,
            "boundary_answer": SOLO_CONFIRMATION_BOUNDARY_MESSAGE,
        }
    if raw_agent_tool_marker_count(preflight_answer) > 0 and not request.get("tool_calls"):
        boundary_error = agent_execution_boundary_error()
        return {
            "messages": prepared["messages"],
            "rendered_prompt": prepared["rendered_prompt"],
            "agent_tool_results": [agent_execution_boundary_result(answer=preflight_answer)],
            "status": "failed",
            "error": boundary_error,
            "boundary_answer": AGENT_UNHANDLED_TOOL_CALL_MESSAGE,
        }
    if not request.get("tool_calls"):
        return {"messages": prepared["messages"], "rendered_prompt": prepared["rendered_prompt"], "agent_tool_results": []}
    tool_results = agent_tools.execute_tool_calls(
        prepared["file_workspace"],
        request["tool_calls"],
        run_context=single_turn_tool_run_context(prepared),
    )
    if agent_tools.contains_high_risk_result(tool_results):
        boundary_answer = agent_tools.high_risk_failure_message(tool_results)
        return {
            "messages": prepared["messages"],
            "rendered_prompt": prepared["rendered_prompt"],
            "agent_tool_results": tool_results,
            "status": "failed",
            "error": agent_execution_boundary_error(boundary_answer),
            "boundary_answer": boundary_answer,
        }
    messages = agent_tools.build_follow_up_messages(prepared["messages"], preflight_answer, tool_results)
    return {
        "messages": messages,
        "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages)),
        "agent_tool_results": tool_results,
    }


def execute_single_turn_stream_tool_request(
    prepared: dict[str, Any],
    messages: list[dict[str, Any]],
    request_text: str,
) -> dict[str, Any]:
    request = agent_tools.parse_tool_request(request_text)
    if not request.get("tool_calls"):
        return {
            "messages": messages,
            "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages)),
            "agent_tool_results": [agent_execution_boundary_result(answer=request_text)],
            "status": "failed",
            "error": agent_execution_boundary_error(),
            "boundary_answer": AGENT_UNHANDLED_TOOL_CALL_MESSAGE,
        }
    workspace = prepared.get("file_workspace")
    if not workspace or not workspace.get("enabled"):
        return {
            "messages": messages,
            "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages)),
            "agent_tool_results": [agent_execution_boundary_result(answer=request_text)],
            "status": "failed",
            "error": agent_execution_boundary_error(),
            "boundary_answer": AGENT_UNHANDLED_TOOL_CALL_MESSAGE,
        }
    tool_results = agent_tools.execute_tool_calls(
        workspace,
        request["tool_calls"],
        run_context=single_turn_tool_run_context(prepared),
    )
    if agent_tools.contains_high_risk_result(tool_results):
        boundary_answer = agent_tools.high_risk_failure_message(tool_results)
        return {
            "messages": messages,
            "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages)),
            "agent_tool_results": tool_results,
            "status": "failed",
            "error": agent_execution_boundary_error(boundary_answer),
            "boundary_answer": boundary_answer,
        }
    follow_up_messages = agent_tools.build_follow_up_messages(messages, request_text, tool_results)
    return {
        "messages": follow_up_messages,
        "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(follow_up_messages)),
        "agent_tool_results": tool_results,
    }


def single_turn_tool_run_context(prepared: dict[str, Any]) -> dict[str, Any]:
    app = prepared.get("app") if isinstance(prepared.get("app"), dict) else {}
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    return {
        "tenant_id": int(app.get("tenant_id") or 0),
        "app_key": str(app.get("app_key") or ""),
        "conversation_key": "single_turn",
        "runtime_config": runtime_config,
    }


def require_agent_application(app_key: str, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    app = get_ai_application(app_key, current_user=current_user)
    if app.get("app_type") != "agent":
        raise HTTPException(status_code=422, detail="Only Agent applications support agent conversations")
    return app


def require_workflow_application(app_key: str, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    app = get_ai_application(app_key, current_user=current_user)
    if app.get("app_type") != "workflow":
        raise HTTPException(status_code=422, detail="Only workflow applications support workflow export/import")
    return app


def workflow_definition_from_import_payload(payload: dict[str, Any]) -> dict[str, Any]:
    candidate = payload.get("workflow") if isinstance(payload.get("workflow"), dict) else payload
    if not isinstance(candidate, dict):
        raise HTTPException(status_code=422, detail="workflow import payload must be an object")
    if not isinstance(candidate.get("nodes"), list) or not isinstance(candidate.get("edges"), list):
        raise HTTPException(status_code=422, detail="workflow import payload requires nodes and edges")
    return copy.deepcopy(candidate)


def validate_workflow_definition_payload(workflow: dict[str, Any]) -> None:
    try:
        normalized = normalize_workflow_definition(workflow)
    except WorkflowRuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    reject_workflow_skill_nodes(normalized)


def reject_workflow_skill_nodes(workflow: dict[str, Any]) -> None:
    nodes = workflow.get("nodes") if isinstance(workflow.get("nodes"), list) else []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type") or "").strip().lower()
        if node_type in {"skill", "tool"}:
            raise HTTPException(status_code=422, detail="workflow applications do not support Skill nodes")


def get_agent_conversation_or_404(app: dict[str, Any], conversation_key: str) -> dict[str, Any]:
    conversation = read_one(
        lambda conn: repo().require_ai_agent_schema(conn)
        or repo().get_agent_conversation(conn, app["app_key"], conversation_key)
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Agent conversation not found")
    return conversation


def prepare_agent_run(
    app_key: str,
    conversation_key: str,
    payload: dict[str, Any],
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    app = require_agent_application(app_key, current_user=current_user)
    conversation = get_agent_conversation_or_404(app, conversation_key)
    content = str(payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="content is required")

    app_for_run, prompt_refs = resolve_prompt_runtime_app(app)
    variables = extract_run_variables(payload)
    model = resolve_model(app_for_run, payload)
    temperature = resolve_temperature(app_for_run, payload)
    configure_skill_llm_task_runner(app_for_run, payload, model=model, temperature=temperature)
    skill_plan = skill_runtime.prepare_skill_runtime(app_for_run, payload, variables, app_type="agent")
    plan_agent_skills_if_enabled(
        app_for_run,
        payload,
        variables,
        content,
        skill_plan,
        model=model,
        temperature=temperature,
    )
    skill_results = skill_runtime.execute_pre_model_skills(skill_plan)
    variables = skill_runtime.merge_skill_results_into_variables(variables, skill_plan, skill_results)
    validate_variables(app_for_run, variables)
    try:
        file_workspace = agent_file_tools.prepare_workspace(
            app_for_run,
            conversation,
            payload,
            skill_runtime.collect_files(payload, variables),
            skill_plan=skill_plan,
        )
    except agent_file_tools.AgentFileToolError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    database_target = require_database()
    tool_messages: list[dict[str, Any]] = []
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
            for tool_payload in skill_runtime.agent_tool_messages(skill_results):
                tool_messages.append(
                    repo().insert_agent_message(
                        conn,
                        {
                            "app_key": app_for_run["app_key"],
                            "conversation_key": conversation["conversation_key"],
                            "role": "tool",
                            "content": tool_payload["content"],
                            "status": tool_payload["status"],
                            "metadata": tool_payload["metadata"],
                        },
                    )
                )
            conversation = repo().get_agent_conversation(conn, app_for_run["app_key"], conversation["conversation_key"]) or conversation
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc

    messages = build_agent_messages(
        app_for_run,
        variables,
        [*history, *tool_messages],
        content,
        skill_plan=skill_plan,
        skill_results=skill_results,
        file_workspace=file_workspace,
    )
    rendered_prompt = gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages))
    return {
        "app": app_for_run,
        "conversation": conversation,
        "user_message": user_message,
        "tool_messages": tool_messages,
        "variables": variables,
        "messages": messages,
        "rendered_prompt": rendered_prompt,
        "model": model,
        "temperature": temperature,
        "response_format": resolve_response_format(app_for_run, payload),
        "prompt_refs": prompt_refs,
        "skill_plan": skill_plan,
        "skill_results": skill_results,
        "file_workspace": file_workspace,
    }


def build_agent_messages(
    app: dict[str, Any],
    variables: dict[str, Any],
    history: list[dict[str, Any]],
    user_content: str,
    *,
    skill_plan: skill_runtime.SkillRuntimePlan | None = None,
    skill_results: list[skill_runtime.SkillExecutionResult] | None = None,
    file_workspace: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for role, field in (("system", "system_prompt"), ("developer", "developer_prompt")):
        content = render_template(str(app.get(field) or ""), variables)
        if content.strip():
            messages.append({"role": role, "content": content})
    if skill_plan is not None:
        messages = skill_runtime.append_skill_context_messages(messages, skill_plan, skill_results or [])
    file_tool_prompt = agent_tools.build_prompt(file_workspace)
    if file_tool_prompt:
        messages.append({"role": "developer", "content": file_tool_prompt})
    for item in history:
        role = str(item.get("role") or "")
        if role not in {"user", "assistant", "tool"}:
            continue
        content = str(item.get("content") or "")
        if content.strip():
            message_role = "user" if role == "tool" else role
            prefix = "Tool result:\n" if role == "tool" else ""
            messages.append({"role": message_role, "content": f"{prefix}{content}"})
    messages.append({"role": "user", "content": render_message_content("user", user_content, variables)})
    return messages


def raw_agent_tool_marker_count(text: str) -> int:
    lowered = str(text or "").lower()
    return sum(lowered.count(marker) for marker in AGENT_TOOL_CALL_MARKERS)


def raw_agent_tool_protocol_fragment_detected(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(fragment in lowered for fragment in AGENT_TOOL_PROTOCOL_FRAGMENTS)


def raw_agent_tool_protocol_start(text: str) -> int:
    lowered = str(text or "").lower()
    positions = [lowered.find(fragment) for fragment in AGENT_TOOL_PROTOCOL_FRAGMENTS]
    valid = [position for position in positions if position >= 0]
    return min(valid) if valid else -1


def raw_agent_unsupported_tool_detected(text: str) -> bool:
    compact = "".join(str(text or "").lower().split())
    return any(f'"name":"{tool_name}"' in compact or f'"tool":"{tool_name}"' in compact for tool_name in AGENT_UNSUPPORTED_NATIVE_TOOL_NAMES)


def sanitize_agent_protocol_preview(text: str, *, limit: int = 2000) -> str:
    content = str(text or "")
    if not content:
        return ""
    start = raw_agent_tool_protocol_start(content)
    if start < 0:
        return content[:limit]
    prefix = content[:start].strip()
    redacted = "[native tool protocol redacted]"
    if prefix:
        return f"{prefix} {redacted}"[:limit]
    return redacted[:limit]


def solo_confirmation_requested(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker.lower() in lowered for marker in SOLO_CONFIRMATION_MARKERS)


def agent_execution_boundary_error(message: str = AGENT_UNHANDLED_TOOL_CALL_MESSAGE) -> AgentExecutionBoundaryError:
    return AgentExecutionBoundaryError(message)


def streamed_tool_protocol_status(text: str) -> str:
    if agent_tools.parse_tool_request(text).get("tool_calls"):
        return "request"
    if solo_confirmation_requested(text):
        return "confirmation"
    lowered = str(text or "").lower()
    if raw_agent_unsupported_tool_detected(text):
        return "unsupported"
    if "</tool_call>" in lowered or "</tool_result>" in lowered:
        return "unsupported"
    if raw_agent_tool_marker_count(text) >= AGENT_TOOL_CALL_MARKER_LIMIT:
        return "unsupported"
    if len(text) > 24_000:
        return "unsupported"
    return "pending"


def agent_execution_boundary_result(
    *,
    answer: str,
    message: str = AGENT_UNHANDLED_TOOL_CALL_MESSAGE,
    tool_name: str = "unsupported_native_tool",
    index: int = 1,
) -> dict[str, Any]:
    return {
        "index": index,
        "tool": tool_name,
        "status": "failed",
        "arguments": {},
        "error_code": "UNSUPPORTED_AGENT_TOOL",
        "error_message": message,
        "output": {"raw_preview": sanitize_agent_protocol_preview(answer)},
        "elapsed_ms": 0,
    }


def agent_boundary_run(
    prepared: dict[str, Any],
    *,
    answer: str,
    trace_id: str,
    message: str = AGENT_UNHANDLED_TOOL_CALL_MESSAGE,
) -> dict[str, Any]:
    result = agent_execution_boundary_result(answer=answer, message=message)
    tool_messages = persist_agent_file_tool_messages(prepared, [result], trace_id=trace_id)
    error = agent_execution_boundary_error(message)
    return {
        "answer": message,
        "usage": {},
        "messages": prepared["messages"],
        "rendered_prompt": prepared["rendered_prompt"],
        "agent_tool_results": [result],
        "agent_tool_messages": tool_messages,
        "status": "failed",
        "error": error,
    }


def agent_boundary_stream_event(message: str) -> str:
    return gateway.sse_data(
        {
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {"content": message}, "finish_reason": None}],
        }
    )


def agent_stream_delta_event(content: str) -> str:
    return gateway.sse_data(
        {
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
        }
    )


def tool_call_blocked_event(trace_id: str, message: str = AGENT_UNHANDLED_TOOL_CALL_MESSAGE) -> str:
    return gateway.sse_data(
        {
            "trace_id": trace_id,
            "status": "blocked",
            "message": message,
            "object": "ai_application.tool_call.blocked",
        }
    ).replace("data: ", "event: tool_call_blocked\ndata: ", 1)


def run_agent_model_with_file_tools(
    prepared: dict[str, Any],
    payload: dict[str, Any],
    *,
    trace_id: str,
) -> dict[str, Any]:
    response = gateway.chat_completions(
        model=prepared["model"],
        messages=prepared["messages"],
        temperature=prepared["temperature"],
        response_format=prepared["response_format"],
        extra_body=resolve_extra_body(prepared["app"], payload),
        enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
        correlation_id=trace_id,
    )
    first_answer = extract_answer(response)
    first_usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    request = agent_tools.parse_tool_request(first_answer)
    if raw_agent_tool_marker_count(first_answer) > 0 and not request.get("tool_calls"):
        boundary = agent_boundary_run(prepared, answer=first_answer, trace_id=trace_id)
        boundary["usage"] = first_usage
        return boundary
    if not prepared.get("file_workspace", {}).get("enabled") or not request.get("tool_calls"):
        if raw_agent_tool_marker_count(first_answer) > 0:
            boundary = agent_boundary_run(prepared, answer=first_answer, trace_id=trace_id)
            boundary["usage"] = first_usage
            return boundary
        answer = agent_tools.protocol_final_answer(first_answer) or first_answer
        if solo_confirmation_requested(answer):
            return agent_failed_model_run(
                prepared,
                message=SOLO_CONFIRMATION_BOUNDARY_MESSAGE,
                usage=first_usage,
            )
        return {
            "answer": answer,
            "usage": first_usage,
            "messages": prepared["messages"],
            "rendered_prompt": prepared["rendered_prompt"],
            "agent_tool_results": [],
            "agent_tool_messages": [],
            "status": "success",
        }

    tool_results = agent_tools.execute_tool_calls(
        prepared["file_workspace"],
        request["tool_calls"],
        run_context=agent_tool_run_context(prepared),
    )
    tool_messages = persist_agent_file_tool_messages(prepared, tool_results, trace_id=trace_id)
    if agent_tools.contains_high_risk_result(tool_results):
        return agent_failed_model_run(
            prepared,
            message=agent_tools.high_risk_failure_message(tool_results),
            usage=first_usage,
            tool_results=tool_results,
            tool_messages=tool_messages,
        )
    follow_up_messages = agent_tools.build_follow_up_messages(prepared["messages"], first_answer, tool_results)
    follow_up_response = gateway.chat_completions(
        model=prepared["model"],
        messages=follow_up_messages,
        temperature=prepared["temperature"],
        response_format=prepared["response_format"],
        extra_body=resolve_extra_body(prepared["app"], payload),
        enable_think_output=payload.get("enable_think_output") if "enable_think_output" in payload else None,
        correlation_id=f"{trace_id}_final",
    )
    final_answer = extract_answer(follow_up_response)
    follow_up_usage = follow_up_response.get("usage") if isinstance(follow_up_response.get("usage"), dict) else {}
    if raw_agent_tool_marker_count(final_answer) > 0 or raw_agent_unsupported_tool_detected(final_answer) or agent_tools.parse_tool_request(final_answer).get("tool_calls"):
        return {
            "answer": AGENT_UNHANDLED_TOOL_CALL_MESSAGE,
            "usage": agent_tools.merge_usage(first_usage, follow_up_usage),
            "messages": follow_up_messages,
            "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(follow_up_messages)),
            "agent_tool_results": tool_results,
            "agent_tool_messages": tool_messages,
            "status": "failed",
            "error": agent_execution_boundary_error(),
        }
    if solo_confirmation_requested(final_answer):
        return agent_failed_model_run(
            prepared,
            message=SOLO_CONFIRMATION_BOUNDARY_MESSAGE,
            usage=agent_tools.merge_usage(first_usage, follow_up_usage),
            messages=follow_up_messages,
            tool_results=tool_results,
            tool_messages=tool_messages,
        )
    return {
        "answer": final_answer,
        "usage": agent_tools.merge_usage(first_usage, follow_up_usage),
        "messages": follow_up_messages,
        "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(follow_up_messages)),
        "agent_tool_results": tool_results,
        "agent_tool_messages": tool_messages,
        "status": "success",
    }


def agent_failed_model_run(
    prepared: dict[str, Any],
    *,
    message: str,
    usage: dict[str, Any],
    messages: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    tool_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    run_messages = messages or prepared["messages"]
    rendered_prompt = (
        prepared["rendered_prompt"]
        if run_messages is prepared["messages"]
        else gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(run_messages))
    )
    return {
        "answer": message,
        "usage": usage,
        "messages": run_messages,
        "rendered_prompt": rendered_prompt,
        "agent_tool_results": tool_results or [],
        "agent_tool_messages": tool_messages or [],
        "status": "failed",
        "error": agent_execution_boundary_error(message),
    }


def agent_file_tool_stream_preflight_required(prepared: dict[str, Any], payload: dict[str, Any]) -> bool:
    return agent_tools.stream_preflight_required(prepared.get("file_workspace"), payload)


def execute_agent_tool_request(
    prepared: dict[str, Any],
    messages: list[dict[str, Any]],
    request_text: str,
    *,
    trace_id: str,
) -> dict[str, Any]:
    request = agent_tools.parse_tool_request(request_text)
    if not request.get("tool_calls"):
        boundary = agent_boundary_run(prepared, answer=request_text, trace_id=trace_id)
        return {
            "messages": boundary["messages"],
            "rendered_prompt": boundary["rendered_prompt"],
            "agent_tool_results": boundary["agent_tool_results"],
            "agent_tool_messages": boundary["agent_tool_messages"],
            "boundary_answer": boundary["answer"],
            "boundary_error": boundary["error"],
        }
    workspace = prepared.get("file_workspace")
    if not workspace or not workspace.get("enabled"):
        boundary = agent_boundary_run(prepared, answer=request_text, trace_id=trace_id)
        return {
            "messages": boundary["messages"],
            "rendered_prompt": boundary["rendered_prompt"],
            "agent_tool_results": boundary["agent_tool_results"],
            "agent_tool_messages": boundary["agent_tool_messages"],
            "boundary_answer": boundary["answer"],
            "boundary_error": boundary["error"],
        }
    tool_results = agent_tools.execute_tool_calls(
        workspace,
        request["tool_calls"],
        run_context=agent_tool_run_context(prepared),
    )
    tool_messages = persist_agent_file_tool_messages(prepared, tool_results, trace_id=trace_id)
    if agent_tools.contains_high_risk_result(tool_results):
        boundary_answer = agent_tools.high_risk_failure_message(tool_results)
        return {
            "messages": messages,
            "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages)),
            "agent_tool_results": tool_results,
            "agent_tool_messages": tool_messages,
            "boundary_answer": boundary_answer,
            "boundary_error": agent_execution_boundary_error(boundary_answer),
        }
    follow_up_messages = agent_tools.build_follow_up_messages(messages, request_text, tool_results)
    return {
        "messages": follow_up_messages,
        "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(follow_up_messages)),
        "agent_tool_results": tool_results,
        "agent_tool_messages": tool_messages,
    }


def run_agent_file_tool_preflight(
    prepared: dict[str, Any],
    payload: dict[str, Any],
    *,
    trace_id: str,
) -> dict[str, Any]:
    response = gateway.chat_completions(
        model=prepared["model"],
        messages=[
            *prepared["messages"],
            {
                "role": "user",
                "content": (
                    "If Agent tools are needed, return tool_calls JSON now. "
                    "Use file tools, shell.run, or python.run only. "
                    "Otherwise return {\"tool_calls\":[]}."
                ),
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
        extra_body=resolve_extra_body(prepared["app"], payload),
        enable_think_output=False,
        correlation_id=f"{trace_id}_file_tools",
    )
    preflight_answer = extract_answer(response)
    request = agent_tools.parse_tool_request(preflight_answer)
    if solo_confirmation_requested(preflight_answer):
        return {
            "messages": prepared["messages"],
            "rendered_prompt": prepared["rendered_prompt"],
            "agent_tool_results": [],
            "agent_tool_messages": [],
            "boundary_answer": SOLO_CONFIRMATION_BOUNDARY_MESSAGE,
            "boundary_error": agent_execution_boundary_error(SOLO_CONFIRMATION_BOUNDARY_MESSAGE),
        }
    if raw_agent_tool_marker_count(preflight_answer) > 0 and not request.get("tool_calls"):
        boundary = agent_boundary_run(prepared, answer=preflight_answer, trace_id=trace_id)
        return {
            "messages": boundary["messages"],
            "rendered_prompt": boundary["rendered_prompt"],
            "agent_tool_results": boundary["agent_tool_results"],
            "agent_tool_messages": boundary["agent_tool_messages"],
            "boundary_answer": boundary["answer"],
            "boundary_error": boundary["error"],
        }
    if not request.get("tool_calls"):
        if raw_agent_tool_marker_count(preflight_answer) > 0:
            boundary = agent_boundary_run(prepared, answer=preflight_answer, trace_id=trace_id)
            return {
                "messages": boundary["messages"],
                "rendered_prompt": boundary["rendered_prompt"],
                "agent_tool_results": boundary["agent_tool_results"],
                "agent_tool_messages": boundary["agent_tool_messages"],
                "boundary_answer": boundary["answer"],
                "boundary_error": boundary["error"],
            }
        return {
            "messages": prepared["messages"],
            "rendered_prompt": prepared["rendered_prompt"],
            "agent_tool_results": [],
            "agent_tool_messages": [],
        }
    tool_results = agent_tools.execute_tool_calls(
        prepared["file_workspace"],
        request["tool_calls"],
        run_context=agent_tool_run_context(prepared),
    )
    tool_messages = persist_agent_file_tool_messages(prepared, tool_results, trace_id=trace_id)
    if agent_tools.contains_high_risk_result(tool_results):
        boundary_answer = agent_tools.high_risk_failure_message(tool_results)
        return {
            "messages": prepared["messages"],
            "rendered_prompt": prepared["rendered_prompt"],
            "agent_tool_results": tool_results,
            "agent_tool_messages": tool_messages,
            "boundary_answer": boundary_answer,
            "boundary_error": agent_execution_boundary_error(boundary_answer),
        }
    messages = agent_tools.build_follow_up_messages(prepared["messages"], preflight_answer, tool_results)
    return {
        "messages": messages,
        "rendered_prompt": gateway.prompt_from_messages(prompt=None, messages=gateway.messages_as_text_messages(messages)),
        "agent_tool_results": tool_results,
        "agent_tool_messages": tool_messages,
    }


def agent_tool_run_context(prepared: dict[str, Any]) -> dict[str, Any]:
    app = prepared.get("app") if isinstance(prepared.get("app"), dict) else {}
    conversation = prepared.get("conversation") if isinstance(prepared.get("conversation"), dict) else {}
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    return {
        "tenant_id": int(app.get("tenant_id") or 0),
        "app_key": str(app.get("app_key") or ""),
        "conversation_key": str(conversation.get("conversation_key") or ""),
        "runtime_config": runtime_config,
    }


def persist_agent_file_tool_messages(prepared: dict[str, Any], tool_results: list[dict[str, Any]], *, trace_id: str) -> list[dict[str, Any]]:
    if not tool_results:
        return []
    status = "failed" if any(result.get("status") != "success" for result in tool_results) else "completed"
    content = "Agent tool results:\n" + json_dump(tool_results)
    database_target = require_database()
    try:
        with connect(database_target, readonly=False) as conn:
            repo().require_ai_applications_schema(conn)
            repo().require_ai_agent_schema(conn)
            return [
                repo().insert_agent_message(
                    conn,
                    {
                        "app_key": prepared["app"]["app_key"],
                        "conversation_key": prepared["conversation"]["conversation_key"],
                        "role": "tool",
                        "content": content,
                        "status": status,
                        "trace_id": trace_id,
                        "metadata": {"agent_tool_results": tool_results, "agent_file_tool_results": tool_results},
                    },
                )
            ]
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc


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
    if payload["app_type"] == "workflow":
        validate_workflow_definition_payload(workflow_definition_from_app(payload))


def validate_publishable(app: dict[str, Any]) -> None:
    if app.get("app_type") == "workflow":
        validate_workflow_definition_payload(workflow_definition_from_app(app))
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
        runtime_keys = {
            "model",
            "temperature",
            "response_format",
            "extra_body",
            "enable_think_output",
            "files",
            "skill_calls",
            "skill_planning",
            "skill_call_budget",
            "skills",
        }
        variables = {key: value for key, value in payload.items() if key not in runtime_keys}
    if not isinstance(variables, dict):
        raise HTTPException(status_code=422, detail="variables must be an object")
    return variables


def workflow_definition_from_app(app: dict[str, Any]) -> dict[str, Any]:
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    workflow = runtime_config.get("workflow") if isinstance(runtime_config.get("workflow"), dict) else {}
    if not workflow:
        raise HTTPException(status_code=422, detail="workflow runtime_config.workflow is required")
    reject_workflow_skill_nodes(workflow)
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


def upsert_latest_workflow_trace_node(trace_nodes: list[dict[str, Any]], node: dict[str, Any]) -> None:
    node_id = str(node.get("node_id") or "")
    if not node_id:
        return
    for index, existing in enumerate(trace_nodes):
        if str(existing.get("node_id") or "") == node_id:
            trace_nodes[index] = dict(node)
            return
    trace_nodes.append(dict(node))


def workflow_stream_event(event_name: str | None, payload: dict[str, Any]) -> str:
    event_prefix = f"event: {event_name}\n" if event_name else ""
    data = gateway.json.dumps(payload, ensure_ascii=False, default=str)
    return f"{event_prefix}data: {data}\n\n"


def plan_agent_skills_if_enabled(
    app: dict[str, Any],
    payload: dict[str, Any],
    variables: dict[str, Any],
    user_content: str,
    skill_plan: skill_runtime.SkillRuntimePlan,
    *,
    model: str,
    temperature: float | None,
    app_type: str = "agent",
) -> None:
    if not skill_runtime.skill_planning_enabled(app, payload, app_type=app_type):
        return
    if not skill_runtime.planning_candidates(skill_plan):
        return
    budget = skill_runtime.skill_call_budget(app, payload, app_type=app_type)
    if budget <= 0:
        return
    response = gateway.chat_completions(
        model=model,
        messages=skill_runtime.build_skill_planning_messages(app, variables, user_content, skill_plan, app_type=app_type),
        temperature=0 if temperature is None else min(float(temperature), 0.2),
        response_format={"type": "json_object"},
        extra_body=resolve_extra_body(app, payload),
        enable_think_output=False,
        correlation_id=f"skill_plan_{uuid.uuid4().hex}",
    )
    planned = skill_runtime.parse_planned_skill_calls(extract_answer(response), skill_plan, budget=budget)
    skill_runtime.set_planned_skill_calls(skill_plan, planned)


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


def append_developer_context_message(messages: list[dict[str, Any]], content: str) -> list[dict[str, Any]]:
    if not str(content or "").strip():
        return messages
    insert_at = 0
    for index, message in enumerate(messages):
        role = str(message.get("role") or "")
        if role not in {"system", "developer"}:
            break
        insert_at = index + 1
    return [*messages[:insert_at], {"role": "developer", "content": content}, *messages[insert_at:]]


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


def configure_skill_llm_task_runner(app: dict[str, Any], payload: dict[str, Any], *, model: str, temperature: float | None) -> None:
    skill_runtime.configure_llm_task_runner(
        GatewaySkillLLMTaskRunner(
            model=model,
            temperature=temperature,
            extra_body=resolve_extra_body(app, payload),
        )
    )


def build_llm_task_skill_messages(request: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = request.get("manifest") if isinstance(request.get("manifest"), dict) else {}
    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    references = collect_skill_reference_text(request, runtime)
    payload = {
        "skill_key": request.get("skill_key"),
        "input": request.get("input") if isinstance(request.get("input"), dict) else {},
        "manifest": manifest,
    }
    developer_parts = [
        "You are executing the following uploaded Skill as an LLM task.",
        "Follow the Skill instructions exactly and return the requested deliverable.",
        "If you create an HTML deliverable, return the complete HTML document.",
        str(request.get("content") or "").strip(),
    ]
    if references:
        developer_parts.append("Skill package references:\n" + references)
    return [
        {"role": "developer", "content": "\n\n".join(part for part in developer_parts if part)},
        {"role": "user", "content": json_dump(payload)},
    ]


def collect_skill_reference_text(request: dict[str, Any], runtime: dict[str, Any]) -> str:
    reference_paths = [str(item).replace("\\", "/").lstrip("/") for item in runtime.get("references", []) if str(item or "").strip()]
    if not reference_paths:
        return ""
    package_data = str(request.get("package_data_base64") or "")
    if not package_data:
        return ""
    try:
        package_bytes = base64.b64decode(package_data)
    except ValueError:
        return ""
    chunks: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
            names = {name.replace("\\", "/").lstrip("/"): name for name in archive.namelist()}
            for path in reference_paths[:20]:
                raw_name = names.get(path)
                if not raw_name:
                    continue
                data = archive.read(raw_name)
                if len(data) > 100_000:
                    data = data[:100_000]
                chunks.append(f"--- {path} ---\n{data.decode('utf-8-sig', errors='replace')}")
    except (RuntimeError, zipfile.BadZipFile):
        return ""
    return "\n\n".join(chunks)


def llm_task_artifacts(answer: str, request: dict[str, Any]) -> list[dict[str, Any]]:
    if not answer.strip():
        return []
    output_schema = request.get("manifest", {}).get("outputs") if isinstance(request.get("manifest"), dict) else {}
    artifact_type = "text/html" if "<html" in answer.lower() or "<!doctype html" in answer.lower() else "text/plain"
    if isinstance(output_schema, dict):
        raw_artifacts = output_schema.get("artifacts")
        if isinstance(raw_artifacts, list) and raw_artifacts and isinstance(raw_artifacts[0], dict):
            artifact_type = str(raw_artifacts[0].get("type") or artifact_type)
    extension = "html" if artifact_type == "text/html" else "txt"
    return [
        {
            "name": f"{request.get('skill_key') or 'skill'}-result.{extension}",
            "type": artifact_type,
            "content": answer,
        }
    ]


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


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


def stream_event_visible_text(event: str) -> str:
    event_type, payload = parse_sse_event(event)
    if event_type == "error" or not payload:
        return ""
    choices = payload.get("choices") if isinstance(payload.get("choices"), list) else []
    first = choices[0] if choices and isinstance(choices[0], dict) else {}
    delta = first.get("delta") if isinstance(first.get("delta"), dict) else {}
    parts = [
        delta.get("content"),
        delta.get("reasoning_content"),
        delta.get("reasoning"),
        delta.get("think"),
        delta.get("thinking"),
    ]
    return "".join(str(part or "") for part in parts)


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


