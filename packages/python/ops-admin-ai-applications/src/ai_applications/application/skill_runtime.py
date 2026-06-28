from __future__ import annotations

import base64
import json
import re
import time
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path, PurePosixPath
from collections.abc import Callable
from typing import Any, Protocol

from fastapi import HTTPException

from ai_applications.application import runtime_files
from ai_assets.application import services as skill_asset_services


SANDBOX_RUNTIME_KINDS = {"sandbox", "sandbox_python", "sandbox_shell", "python", "shell"}
PROMPT_CONTEXT_RUNTIME_KINDS = {"", "prompt", "prompt_context", "context"}
LLM_TASK_RUNTIME_KINDS = {"llm_task", "llm"}
BUILTIN_RUNTIME_KINDS = {"builtin", "builtin_executor"}
BUILTIN_EXECUTOR_KEYS = {"log_zip_error_inspector", "log_zip_analysis", "log_analysis"}
DEFAULT_SKILL_RESULT_VARIABLE = "_skills"
DEFAULT_SKILL_CALL_BUDGET = 3
MAX_SKILL_CALL_BUDGET = 10
MAX_SANDBOX_WORKSPACE_FILES = 120
MAX_SANDBOX_WORKSPACE_FILE_BYTES = 5 * 1024 * 1024
LOG_ZIP_TEXT_EXTENSIONS = {
    ".err",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".out",
    ".stderr",
    ".stdout",
    ".text",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
LOG_ERROR_PATTERNS = (
    ("fatal", re.compile(r"\b(FATAL|CRITICAL)\b", re.IGNORECASE)),
    ("error", re.compile(r"\b(ERROR|ERR)\b", re.IGNORECASE)),
    ("exception", re.compile(r"\b(Exception|Traceback|Stacktrace)\b", re.IGNORECASE)),
    ("warning", re.compile(r"\b(WARN|WARNING)\b", re.IGNORECASE)),
    ("cn_error", re.compile(r"(\u9519\u8bef|\u5f02\u5e38|\u5931\u8d25|\u6545\u969c|\u544a\u8b66)")),
)
TEXT_ENCODINGS = ("utf-8-sig", "utf-16", "gb18030", "big5", "latin-1")


class SkillRuntimeError(RuntimeError):
    pass


class SkillSandboxRunner(Protocol):
    def run(self, request: dict[str, Any]) -> dict[str, Any]: ...


class SkillLLMTaskRunner(Protocol):
    def run(self, request: dict[str, Any]) -> dict[str, Any]: ...


class UnavailableSkillSandboxRunner:
    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        raise SkillRuntimeError("skill sandbox runner is not configured")


class UnavailableSkillLLMTaskRunner:
    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        raise SkillRuntimeError("skill LLM task runner is not configured")


_sandbox_runner: SkillSandboxRunner = UnavailableSkillSandboxRunner()
_sandbox_runner_resolver: Callable[[dict[str, Any]], SkillSandboxRunner] | None = None
_llm_task_runner: SkillLLMTaskRunner = UnavailableSkillLLMTaskRunner()


def configure_sandbox_runner(runner: SkillSandboxRunner | None) -> None:
    global _sandbox_runner
    _sandbox_runner = runner or UnavailableSkillSandboxRunner()


def configure_sandbox_runner_resolver(
    resolver: Callable[[dict[str, Any]], SkillSandboxRunner] | None,
) -> None:
    global _sandbox_runner_resolver
    _sandbox_runner_resolver = resolver


def resolve_sandbox_runner(request: dict[str, Any]) -> SkillSandboxRunner:
    if _sandbox_runner_resolver is not None:
        return _sandbox_runner_resolver(request)
    return _sandbox_runner


def run_sandbox_request(request: dict[str, Any]) -> dict[str, Any]:
    response = resolve_sandbox_runner(request).run(request)
    if not isinstance(response, dict):
        raise SkillRuntimeError("skill sandbox runner returned invalid result")
    status = str(response.get("status") or "success")
    if status != "success":
        raise SkillRuntimeError(str(response.get("error_message") or "skill sandbox runner failed"))
    output = response.get("output")
    return output if isinstance(output, dict) else {"result": output}


def configure_llm_task_runner(runner: SkillLLMTaskRunner | None) -> None:
    global _llm_task_runner
    _llm_task_runner = runner or UnavailableSkillLLMTaskRunner()


@dataclass(slots=True)
class SkillBinding:
    skill_key: str
    alias: str
    mode: str = "auto"
    enabled: bool = True
    inject_as: str = ""
    priority: int = 100
    allowed_app_types: set[str] = field(default_factory=set)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SkillDescriptor:
    binding: SkillBinding
    resolved: dict[str, Any]
    manifest: dict[str, Any]
    runtime_config: dict[str, Any]
    runtime_constraints: dict[str, Any]
    runtime_kind: str
    executor_key: str
    content: str
    version: str


@dataclass(slots=True)
class SkillCall:
    skill_key: str
    input: dict[str, Any] = field(default_factory=dict)
    alias: str = ""
    reason: str = ""


@dataclass(slots=True)
class SkillExecutionResult:
    skill_key: str
    alias: str
    version: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: int = 0
    error_code: str = ""
    error_message: str = ""
    run_id: str = ""

    def to_trace(self) -> dict[str, Any]:
        return {
            "skill_key": self.skill_key,
            "alias": self.alias,
            "version": self.version,
            "status": self.status,
            "summary": self.summary,
            "output": self.output,
            "evidence": self.evidence,
            "artifacts": self.artifacts,
            "elapsed_ms": self.elapsed_ms,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "run_id": self.run_id,
        }

    def to_message_content(self) -> str:
        payload = self.to_trace()
        return json.dumps(payload, ensure_ascii=False, indent=2)


@dataclass(slots=True)
class SkillRuntimePlan:
    app_key: str
    app_type: str
    tenant_id: int
    current_user: dict[str, Any] | None = None
    app_runtime_config: dict[str, Any] = field(default_factory=dict)
    toolbox: list[SkillDescriptor] = field(default_factory=list)
    required_calls: list[SkillCall] = field(default_factory=list)
    manual_calls: list[SkillCall] = field(default_factory=list)
    planned_calls: list[SkillCall] = field(default_factory=list)
    files: list[dict[str, Any]] = field(default_factory=list)

    def descriptor_for(self, skill_key_or_alias: str) -> SkillDescriptor:
        normalized = normalize_key(skill_key_or_alias)
        for descriptor in self.toolbox:
            if normalize_key(descriptor.binding.skill_key) == normalized or normalize_key(descriptor.binding.alias) == normalized:
                return descriptor
        raise SkillRuntimeError(f"skill is not bound to application: {skill_key_or_alias}")


def prepare_skill_runtime(
    app: dict[str, Any],
    payload: dict[str, Any],
    variables: dict[str, Any],
    *,
    app_type: str,
    current_user: dict[str, Any] | None = None,
) -> SkillRuntimePlan:
    tenant_id = int(app.get("tenant_id") or 0)
    toolbox = resolve_toolbox(app, tenant_id=tenant_id, app_type=app_type)
    files = resolve_runtime_file_inputs(collect_files(payload, variables), current_user=current_user)
    required_calls = [
        SkillCall(skill_key=descriptor.binding.skill_key, input={"files": files, "variables": variables}, alias=descriptor.binding.alias)
        for descriptor in toolbox
        if descriptor.binding.mode == "required"
    ]
    manual_calls = normalize_skill_calls(payload.get("skill_calls") or payload.get("skills") or [])
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    return SkillRuntimePlan(
        app_key=str(app.get("app_key") or ""),
        app_type=app_type,
        tenant_id=tenant_id,
        current_user=current_user,
        app_runtime_config=runtime_config,
        toolbox=toolbox,
        required_calls=required_calls,
        manual_calls=manual_calls,
        files=files,
    )


def execute_pre_model_skills(plan: SkillRuntimePlan) -> list[SkillExecutionResult]:
    results: list[SkillExecutionResult] = []
    for descriptor, call in execution_calls(plan):
        results.append(execute_skill_call(plan, descriptor, call))
    return results


def execution_calls(plan: SkillRuntimePlan) -> list[tuple[SkillDescriptor, SkillCall]]:
    calls: list[tuple[SkillDescriptor, SkillCall]] = []
    seen: set[str] = set()
    for call in [*plan.required_calls, *plan.manual_calls, *plan.planned_calls]:
        descriptor = plan.descriptor_for(call.alias or call.skill_key)
        key = normalize_key(descriptor.binding.skill_key)
        if not key or key in seen:
            continue
        seen.add(key)
        calls.append((descriptor, call))
    return calls


def set_planned_skill_calls(plan: SkillRuntimePlan, calls: list[SkillCall]) -> None:
    plan.planned_calls = calls


def skill_planning_enabled(app: dict[str, Any], payload: dict[str, Any], *, app_type: str) -> bool:
    if payload.get("skill_planning") is not None:
        return bool(payload.get("skill_planning"))
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    scoped = runtime_config.get("agent") if app_type == "agent" and isinstance(runtime_config.get("agent"), dict) else runtime_config
    return bool(scoped.get("skill_planning") or scoped.get("skill_planning_enabled"))


def skill_call_budget(app: dict[str, Any], payload: dict[str, Any], *, app_type: str) -> int:
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    scoped = runtime_config.get("agent") if app_type == "agent" and isinstance(runtime_config.get("agent"), dict) else runtime_config
    value = payload.get("skill_call_budget") if payload.get("skill_call_budget") is not None else scoped.get("skill_call_budget")
    return bounded_int(value, default=DEFAULT_SKILL_CALL_BUDGET, minimum=0, maximum=MAX_SKILL_CALL_BUDGET)


def planning_candidates(plan: SkillRuntimePlan) -> list[SkillDescriptor]:
    return [descriptor for descriptor in plan.toolbox if descriptor.binding.mode == "auto"]


def build_skill_planning_messages(
    app: dict[str, Any],
    variables: dict[str, Any],
    user_content: str,
    plan: SkillRuntimePlan,
    *,
    app_type: str,
) -> list[dict[str, Any]]:
    candidates = [
        {
            "skill_key": descriptor.binding.skill_key,
            "alias": descriptor.binding.alias,
            "runtime_kind": descriptor.runtime_kind,
            "name": descriptor.resolved.get("name") or descriptor.binding.skill_key,
            "description": descriptor.resolved.get("description") or descriptor.manifest.get("description") or "",
            "input_schema": descriptor.manifest.get("input_schema") or descriptor.manifest.get("inputs") or {},
        }
        for descriptor in planning_candidates(plan)
    ]
    payload = {
        "app_key": app.get("app_key"),
        "app_type": app_type,
        "user_content": user_content[:4000],
        "variables": safe_planning_value(variables),
        "files": [file_planning_metadata(item) for item in plan.files],
        "candidate_skills": candidates,
    }
    return [
        {
            "role": "system",
            "content": (
                "You are a skill planner. Select zero or more candidate skills for this run. "
                "Return only a JSON object like {\"skill_calls\":[{\"skill_key\":\"...\",\"input\":{},\"reason\":\"...\"}]}. "
                "Use only candidate skill_key or alias values. Do not invent skills."
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def parse_planned_skill_calls(text: str, plan: SkillRuntimePlan, *, budget: int) -> list[SkillCall]:
    if budget <= 0:
        return []
    payload = parse_json_object(text)
    raw_calls = payload.get("skill_calls") or payload.get("calls") or []
    calls = normalize_skill_calls(raw_calls)
    allowed = {
        normalize_key(descriptor.binding.skill_key)
        for descriptor in planning_candidates(plan)
    } | {
        normalize_key(descriptor.binding.alias)
        for descriptor in planning_candidates(plan)
    }
    result: list[SkillCall] = []
    seen: set[str] = set()
    for call in calls:
        key = normalize_key(call.alias or call.skill_key)
        if not key or key not in allowed or key in seen:
            continue
        seen.add(key)
        result.append(call)
        if len(result) >= budget:
            break
    return result


def parse_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.IGNORECASE | re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def append_skill_context_messages(
    messages: list[dict[str, Any]],
    plan: SkillRuntimePlan,
    results: list[SkillExecutionResult],
) -> list[dict[str, Any]]:
    if not plan.toolbox and not results:
        return messages
    context_messages: list[dict[str, Any]] = []
    toolbox_prompt = build_toolbox_prompt(plan)
    if toolbox_prompt:
        context_messages.append({"role": "developer", "content": toolbox_prompt})
    if results:
        context_messages.append({"role": "developer", "content": build_skill_result_prompt(results)})
    if not context_messages:
        return messages
    insert_at = 0
    for index, message in enumerate(messages):
        role = str(message.get("role") or "")
        if role not in {"system", "developer"}:
            break
        insert_at = index + 1
    return [*messages[:insert_at], *context_messages, *messages[insert_at:]]


def merge_skill_results_into_variables(
    variables: dict[str, Any],
    plan: SkillRuntimePlan,
    results: list[SkillExecutionResult],
) -> dict[str, Any]:
    merged = dict(variables)
    for result in results:
        descriptor = plan.descriptor_for(result.alias or result.skill_key)
        value = result.output
        inject_as = descriptor.binding.inject_as.strip()
        if inject_as:
            assign_path(merged, inject_as, value)
            continue
        skills = merged.setdefault(DEFAULT_SKILL_RESULT_VARIABLE, {})
        if isinstance(skills, dict):
            skills[result.alias or result.skill_key] = value
    return merged


def build_toolbox_prompt(plan: SkillRuntimePlan) -> str:
    if not plan.toolbox:
        return ""
    items: list[dict[str, Any]] = []
    for descriptor in plan.toolbox:
        items.append(
            {
                "skill_key": descriptor.binding.skill_key,
                "alias": descriptor.binding.alias,
                "mode": descriptor.binding.mode,
                "runtime_kind": descriptor.runtime_kind,
                "name": descriptor.resolved.get("name") or descriptor.binding.skill_key,
                "description": descriptor.resolved.get("description") or descriptor.manifest.get("description") or "",
                "input_schema": descriptor.manifest.get("input_schema") or descriptor.manifest.get("inputs") or {},
                "output_schema": descriptor.manifest.get("output_schema") or descriptor.manifest.get("outputs") or {},
            }
        )
    return (
        "Available Skills toolbox. Prefer already executed and injected skill results. "
        "Do not ask the user to confirm pending skill calls in solo execution mode. "
        "If a required skill has not been executed, complete the task with available context or report a clear failure reason. "
        "Script-capable skills are executed through the sandbox runner port.\n"
        f"{json.dumps(items, ensure_ascii=False, indent=2)}"
    )


def toolbox_snapshot(plan: SkillRuntimePlan) -> list[dict[str, Any]]:
    return [
        {
            "skill_key": descriptor.binding.skill_key,
            "alias": descriptor.binding.alias,
            "mode": descriptor.binding.mode,
            "runtime_kind": descriptor.runtime_kind,
            "executor_key": descriptor.executor_key,
            "version": descriptor.version,
            "name": descriptor.resolved.get("name") or descriptor.binding.skill_key,
            "description": descriptor.resolved.get("description") or descriptor.manifest.get("description") or "",
        }
        for descriptor in plan.toolbox
    ]


def skill_calls_snapshot(calls: list[SkillCall]) -> list[dict[str, Any]]:
    return [
        {
            "skill_key": call.skill_key,
            "alias": call.alias,
            "input": call.input,
            "reason": call.reason,
        }
        for call in calls
    ]


def build_skill_result_prompt(results: list[SkillExecutionResult]) -> str:
    return (
        "Executed Skill results for this run. Treat them as reliable context and do not claim unlisted tools were executed.\n"
        f"{json.dumps([result.to_trace() for result in results], ensure_ascii=False, indent=2)}"
    )


def agent_tool_messages(results: list[SkillExecutionResult]) -> list[dict[str, Any]]:
    return [
        {
            "role": "tool",
            "content": result.to_message_content(),
            "status": result.status,
            "metadata": {"skill_result": result.to_trace()},
        }
        for result in results
    ]


def skill_asset_is_referenced_in_app(app: dict[str, Any], skill_key: str) -> bool:
    normalized = normalize_key(skill_key)
    if not normalized:
        return False
    for binding in parse_skill_bindings(app):
        if normalize_key(binding.skill_key) == normalized:
            return True
    return False


def parse_skill_bindings(app: dict[str, Any]) -> list[SkillBinding]:
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    raw_items = runtime_config.get("skills")
    if raw_items is None:
        raw_items = runtime_config.get("skill_bindings")
    if not isinstance(raw_items, list):
        return []
    bindings: list[SkillBinding] = []
    for index, raw in enumerate(raw_items):
        if isinstance(raw, str):
            item = {"skill_key": raw}
        elif isinstance(raw, dict):
            item = raw
        else:
            continue
        skill_key = normalize_key(item.get("skill_key") or item.get("asset_key") or item.get("key"))
        if not skill_key:
            continue
        mode = str(item.get("mode") or "auto").strip().lower()
        if mode not in {"required", "auto", "manual", "disabled"}:
            mode = "auto"
        allowed_app_types = {
            str(value).strip()
            for value in item.get("allowed_app_types", [])
            if str(value or "").strip()
        } if isinstance(item.get("allowed_app_types"), list) else set()
        try:
            priority = int(item.get("priority") if item.get("priority") is not None else index + 100)
        except (TypeError, ValueError):
            priority = index + 100
        bindings.append(
            SkillBinding(
                skill_key=skill_key,
                alias=normalize_key(item.get("alias")) or skill_key,
                mode=mode,
                enabled=bool(item.get("enabled", True)) and mode != "disabled",
                inject_as=str(item.get("inject_as") or "").strip(),
                priority=priority,
                allowed_app_types=allowed_app_types,
                raw=dict(item),
            )
        )
    return sorted(bindings, key=lambda item: (item.priority, item.skill_key))


def resolve_toolbox(app: dict[str, Any], *, tenant_id: int, app_type: str) -> list[SkillDescriptor]:
    if tenant_id <= 0:
        return []
    toolbox: list[SkillDescriptor] = []
    for binding in parse_skill_bindings(app):
        if not binding.enabled:
            continue
        if binding.allowed_app_types and app_type not in binding.allowed_app_types:
            continue
        resolved = resolve_published_skill(binding.skill_key, tenant_id=tenant_id)
        manifest = resolved.get("manifest") if isinstance(resolved.get("manifest"), dict) else {}
        runtime_constraints = resolved.get("runtime_constraints") if isinstance(resolved.get("runtime_constraints"), dict) else {}
        runtime_config = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
        runtime_kind = normalize_runtime_kind(
            runtime_config.get("kind")
            or runtime_config.get("type")
            or runtime_constraints.get("runtime")
            or runtime_constraints.get("kind")
        )
        executor_key = normalize_key(
            runtime_config.get("executor")
            or runtime_config.get("executor_key")
            or runtime_constraints.get("executor")
            or manifest.get("executor")
        )
        toolbox.append(
            SkillDescriptor(
                binding=binding,
                resolved=resolved,
                manifest=manifest,
                runtime_config=runtime_config,
                runtime_constraints=runtime_constraints,
                runtime_kind=runtime_kind,
                executor_key=executor_key,
                content=str(resolved.get("content") or ""),
                version=str(resolved.get("resolved_version") or ""),
            )
        )
    return toolbox


def resolve_published_skill(skill_key: str, *, tenant_id: int) -> dict[str, Any]:
    try:
        return skill_asset_services.resolve_published_skill(skill_key=skill_key, tenant_id=tenant_id)
    except HTTPException as exc:
        message = exc.detail if isinstance(exc.detail, str) else "published skill asset not found"
        raise SkillRuntimeError(str(message)) from exc


def normalize_skill_calls(raw_calls: Any) -> list[SkillCall]:
    if not isinstance(raw_calls, list):
        return []
    calls: list[SkillCall] = []
    for raw in raw_calls:
        if isinstance(raw, str):
            calls.append(SkillCall(skill_key=normalize_key(raw)))
            continue
        if not isinstance(raw, dict):
            continue
        skill_key = normalize_key(raw.get("skill_key") or raw.get("key"))
        alias = normalize_key(raw.get("alias"))
        if not skill_key and not alias:
            continue
        input_payload = raw.get("input") if isinstance(raw.get("input"), dict) else {}
        calls.append(
            SkillCall(
                skill_key=skill_key,
                alias=alias,
                input=dict(input_payload),
                reason=str(raw.get("reason") or "").strip(),
            )
        )
    return calls


def materialize_toolbox_packages(workspace: Path, plan: SkillRuntimePlan) -> list[str]:
    materialized: list[str] = []
    for descriptor in plan.toolbox:
        package_data = str(descriptor.resolved.get("package_data_base64") or "")
        if not package_data:
            continue
        try:
            package_bytes = base64.b64decode(package_data)
        except ValueError:
            continue
        try:
            with zipfile.ZipFile(BytesIO(package_bytes)) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    try:
                        relative = safe_skill_package_path(info.filename)
                    except SkillRuntimeError:
                        continue
                    target = workspace / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(info))
                    materialized.append(relative.as_posix())
        except zipfile.BadZipFile:
            continue
    return materialized


def safe_skill_package_path(name: str) -> Path:
    normalized = str(name or "").replace("\\", "/").strip("/")
    path = Path(normalized)
    if not normalized or any(part in {"", ".", ".."} or ":" in part for part in path.parts):
        raise SkillRuntimeError("skill package contains unsafe path")
    return Path(*path.parts)


def collect_files(payload: dict[str, Any], variables: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    if isinstance(payload.get("files"), list):
        candidates.extend(payload["files"])
    if isinstance(variables.get("files"), list):
        candidates.extend(variables["files"])
    normalized: list[dict[str, Any]] = []
    for item in candidates:
        if isinstance(item, dict):
            normalized.append(dict(item))
    return normalized


def resolve_runtime_file_inputs(
    files: list[dict[str, Any]],
    *,
    current_user: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    normalized = [dict(item) for item in files if isinstance(item, dict)]
    if not current_user:
        return normalized
    resolved: list[dict[str, Any]] = []
    for item in normalized:
        if not runtime_files.runtime_value_needs_file_lookup(item):
            resolved.append(item)
            continue
        try:
            hydrated = runtime_files.hydrate_runtime_file_item(item, current_user=current_user)
        except HTTPException as exc:
            message = exc.detail if isinstance(exc.detail, str) else "failed to read uploaded runtime file"
            raise SkillRuntimeError(str(message)) from exc
        except RuntimeError as exc:
            raise SkillRuntimeError(str(exc)) from exc
        resolved.append(dict(hydrated) if isinstance(hydrated, dict) else item)
    return resolved


def safe_planning_value(value: Any, *, max_text: int = 2000) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in list(value.items())[:50]:
            normalized_key = str(key)
            if normalized_key in {"data_url", "base64", "content"}:
                result[normalized_key] = "[omitted]"
                continue
            result[normalized_key] = safe_planning_value(item, max_text=max_text)
        return result
    if isinstance(value, list):
        return [safe_planning_value(item, max_text=max_text) for item in value[:20]]
    if isinstance(value, str):
        return value[:max_text] + ("..." if len(value) > max_text else "")
    return value


def file_planning_metadata(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(item.get("name") or item.get("filename") or ""),
        "mime_type": str(item.get("mime_type") or item.get("content_type") or ""),
        "size": item.get("size"),
        "has_data": bool(item.get("data_url") or item.get("base64")),
        "has_text": bool(item.get("text") or item.get("content")),
    }


def execute_skill_call(
    plan: SkillRuntimePlan,
    descriptor: SkillDescriptor,
    call: SkillCall,
) -> SkillExecutionResult:
    started_at = time.perf_counter()
    run_id = f"skill_{int(started_at * 1000)}_{descriptor.binding.skill_key}"
    try:
        input_payload = build_skill_input(plan, call)
        prepared_input, workspace_files = prepare_skill_execution_input(plan, input_payload)
        output = execute_skill_by_runtime(plan, descriptor, prepared_input, workspace_files=workspace_files)
        elapsed = int((time.perf_counter() - started_at) * 1000)
        return SkillExecutionResult(
            skill_key=descriptor.binding.skill_key,
            alias=descriptor.binding.alias,
            version=descriptor.version,
            status="success",
            output=output,
            summary=str(output.get("summary") or ""),
            evidence=output.get("evidence") if isinstance(output.get("evidence"), list) else [],
            artifacts=output.get("artifacts") if isinstance(output.get("artifacts"), list) else [],
            elapsed_ms=elapsed,
            run_id=run_id,
        )
    except SkillRuntimeError as exc:
        raise
    except Exception as exc:
        raise SkillRuntimeError(str(exc)) from exc


def build_skill_input(plan: SkillRuntimePlan, call: SkillCall) -> dict[str, Any]:
    payload = dict(call.input)
    payload.setdefault("files", plan.files)
    return payload


def prepare_skill_execution_input(
    plan: SkillRuntimePlan,
    input_payload: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    prepared = dict(input_payload)
    raw_files = prepared.get("files") if isinstance(prepared.get("files"), list) else []
    resolved_files = resolve_runtime_file_inputs(raw_files, current_user=plan.current_user)
    files_with_paths, workspace_files = build_workspace_file_inputs(resolved_files)
    prepared["files"] = files_with_paths
    return prepared, workspace_files


def build_workspace_file_inputs(files: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from ai_applications.application import agent_file_tools

    normalized_files: list[dict[str, Any]] = []
    workspace_files: list[dict[str, Any]] = []
    used_paths: set[str] = set()
    for index, item in enumerate(files[:MAX_SANDBOX_WORKSPACE_FILES], start=1):
        normalized = dict(item)
        normalized_files.append(normalized)
        data = agent_file_tools.upload_bytes(normalized)
        if data is None or len(data) > MAX_SANDBOX_WORKSPACE_FILE_BYTES:
            continue
        path = unique_workspace_upload_path(
            agent_file_tools.safe_filename(normalized.get("name") or normalized.get("filename") or f"upload-{index}.bin"),
            used_paths,
        )
        workspace_files.append(
            {
                "path": path,
                "base64": base64.b64encode(data).decode("ascii"),
            }
        )
        normalized["path"] = path
    return normalized_files, workspace_files


def unique_workspace_upload_path(filename: str, used_paths: set[str]) -> str:
    candidate = f"uploads/{filename}"
    if candidate not in used_paths:
        used_paths.add(candidate)
        return candidate
    path = Path(filename)
    stem = path.stem or "upload"
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = f"uploads/{stem}-{index}{suffix}"
        if candidate not in used_paths:
            used_paths.add(candidate)
            return candidate
    raise SkillRuntimeError("too many uploaded files with the same file name")


def execute_skill_by_runtime(
    plan: SkillRuntimePlan,
    descriptor: SkillDescriptor,
    input_payload: dict[str, Any],
    *,
    workspace_files: list[dict[str, Any]],
) -> dict[str, Any]:
    runtime_kind = descriptor.runtime_kind
    if runtime_kind in SANDBOX_RUNTIME_KINDS:
        return execute_sandbox_skill(plan, descriptor, input_payload, workspace_files=workspace_files)
    if runtime_kind in LLM_TASK_RUNTIME_KINDS:
        return execute_llm_task_skill(plan, descriptor, input_payload)
    if runtime_kind in BUILTIN_RUNTIME_KINDS or descriptor.executor_key in BUILTIN_EXECUTOR_KEYS:
        return execute_builtin_skill(descriptor, input_payload)
    if runtime_kind in PROMPT_CONTEXT_RUNTIME_KINDS:
        return execute_prompt_context_skill(descriptor)
    raise SkillRuntimeError(f"unsupported skill runtime kind: {runtime_kind}")


def execute_prompt_context_skill(descriptor: SkillDescriptor) -> dict[str, Any]:
    content = descriptor.content.strip()
    return {
        "summary": "Skill supplied prompt context; no external tool was executed.",
        "content": content[:12000],
        "truncated": len(content) > 12000,
    }


def execute_builtin_skill(descriptor: SkillDescriptor, input_payload: dict[str, Any]) -> dict[str, Any]:
    executor_key = descriptor.executor_key or normalize_key(descriptor.manifest.get("name")) or descriptor.binding.skill_key
    if executor_key in BUILTIN_EXECUTOR_KEYS:
        return inspect_log_zip(input_payload)
    raise SkillRuntimeError(f"unsupported built-in skill executor: {executor_key}")


def execute_sandbox_skill(
    plan: SkillRuntimePlan,
    descriptor: SkillDescriptor,
    input_payload: dict[str, Any],
    *,
    workspace_files: list[dict[str, Any]],
) -> dict[str, Any]:
    request = {
        "tenant_id": plan.tenant_id,
        "app_key": plan.app_key,
        "skill_key": descriptor.binding.skill_key,
        "runtime_kind": descriptor.runtime_kind,
        "entrypoint": descriptor.resolved.get("entrypoint") or descriptor.manifest.get("entrypoint") or "",
        "content_sha256": descriptor.resolved.get("content_sha256") or "",
        "content": descriptor.content,
        "package_data_base64": descriptor.resolved.get("package_data_base64") or "",
        "package_sha256": descriptor.resolved.get("package_sha256") or "",
        "package_files": descriptor.resolved.get("package_files") if isinstance(descriptor.resolved.get("package_files"), list) else [],
        "input": input_payload,
        "workspace_files": workspace_files,
        "runtime_config": descriptor.runtime_config,
        "app_runtime_config": plan.app_runtime_config,
        "runtime_constraints": descriptor.runtime_constraints,
    }
    return run_sandbox_request(request)


def execute_llm_task_skill(
    plan: SkillRuntimePlan,
    descriptor: SkillDescriptor,
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    request = {
        "tenant_id": plan.tenant_id,
        "app_key": plan.app_key,
        "skill_key": descriptor.binding.skill_key,
        "runtime_kind": descriptor.runtime_kind,
        "manifest": descriptor.manifest,
        "content": descriptor.content,
        "package_data_base64": descriptor.resolved.get("package_data_base64") or "",
        "package_sha256": descriptor.resolved.get("package_sha256") or "",
        "package_files": descriptor.resolved.get("package_files") if isinstance(descriptor.resolved.get("package_files"), list) else [],
        "input": input_payload,
        "runtime_config": descriptor.runtime_config,
        "runtime_constraints": descriptor.runtime_constraints,
    }
    response = _llm_task_runner.run(request)
    if not isinstance(response, dict):
        raise SkillRuntimeError("skill LLM task runner returned invalid result")
    status = str(response.get("status") or "success")
    if status != "success":
        raise SkillRuntimeError(str(response.get("error_message") or "skill LLM task runner failed"))
    output = response.get("output")
    return output if isinstance(output, dict) else {"result": output}


def inspect_log_zip(input_payload: dict[str, Any]) -> dict[str, Any]:
    files = input_payload.get("files") if isinstance(input_payload.get("files"), list) else []
    max_entries = bounded_int(input_payload.get("max_entries"), default=200, minimum=1, maximum=1000)
    max_lines_per_file = bounded_int(input_payload.get("max_lines_per_file"), default=5000, minimum=100, maximum=50000)
    evidence_limit = bounded_int(input_payload.get("evidence_limit"), default=60, minimum=1, maximum=200)
    scanned_files = 0
    skipped_files: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for file_item in files[:20]:
        name = str(file_item.get("name") or file_item.get("filename") or "uploaded.log")
        data = file_bytes(file_item)
        if data is None:
            text = str(file_item.get("text") or file_item.get("content") or "")
            if text:
                scanned_files += 1
                scan_log_text(name, text, evidence, counts, evidence_limit=evidence_limit, max_lines=max_lines_per_file)
            continue
        if zipfile.is_zipfile(BytesIO(data)):
            with zipfile.ZipFile(BytesIO(data)) as archive:
                for info in archive.infolist()[:max_entries]:
                    if info.is_dir():
                        continue
                    entry_name = normalize_zip_entry(info.filename)
                    if not entry_name:
                        skipped_files.append({"name": info.filename, "reason": "unsafe_path"})
                        continue
                    if not is_log_text_name(entry_name):
                        skipped_files.append({"name": entry_name, "reason": "unsupported_extension"})
                        continue
                    if info.file_size > 5_000_000:
                        skipped_files.append({"name": entry_name, "reason": "too_large"})
                        continue
                    scanned_files += 1
                    text = decode_text(archive.read(info))
                    scan_log_text(entry_name, text, evidence, counts, evidence_limit=evidence_limit, max_lines=max_lines_per_file)
            continue
        if not is_log_text_name(name):
            skipped_files.append({"name": name, "reason": "unsupported_extension"})
            continue
        scanned_files += 1
        scan_log_text(name, decode_text(data), evidence, counts, evidence_limit=evidence_limit, max_lines=max_lines_per_file)

    summary = (
        f"Scanned {scanned_files} log files and found {len(evidence)} suspicious lines."
        if scanned_files
        else "No scannable log text was found."
    )
    return {
        "summary": summary,
        "scanned_files": scanned_files,
        "skipped_files": skipped_files[:100],
        "error_groups": counts,
        "evidence": evidence,
    }


def scan_log_text(
    name: str,
    text: str,
    evidence: list[dict[str, Any]],
    counts: dict[str, int],
    *,
    evidence_limit: int,
    max_lines: int,
) -> None:
    for line_number, line in enumerate(text.splitlines()[:max_lines], start=1):
        stripped = line.strip()
        if not stripped:
            continue
        for label, pattern in LOG_ERROR_PATTERNS:
            if not pattern.search(stripped):
                continue
            counts[label] = counts.get(label, 0) + 1
            if len(evidence) < evidence_limit:
                evidence.append(
                    {
                        "file": name,
                        "line": line_number,
                        "category": label,
                        "text": stripped[:1000],
                    }
                )
            break


def file_bytes(file_item: dict[str, Any]) -> bytes | None:
    data_url = str(file_item.get("data_url") or file_item.get("dataUrl") or "").strip()
    if data_url:
        marker = ";base64,"
        if marker not in data_url:
            return None
        encoded = data_url.split(marker, 1)[1]
        return base64.b64decode(encoded)
    encoded = str(file_item.get("base64") or "").strip()
    if encoded:
        return base64.b64decode(encoded)
    return None


def normalize_zip_entry(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} or ":" in part for part in path.parts):
        return ""
    return str(path)


def is_log_text_name(name: str) -> bool:
    suffix = PurePosixPath(name.lower()).suffix
    return suffix in LOG_ZIP_TEXT_EXTENSIONS


def decode_text(data: bytes) -> str:
    for encoding in TEXT_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def assign_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.split(".") if part]
    if not parts:
        return
    current = target
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[parts[-1]] = value


def normalize_runtime_kind(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_key(value: Any) -> str:
    return str(value or "").strip()
