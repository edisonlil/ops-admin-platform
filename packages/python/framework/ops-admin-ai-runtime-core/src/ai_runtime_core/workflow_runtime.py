from __future__ import annotations

import copy
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from ai_runtime_core.prompt_runtime import media_content_parts
from ai_runtime_core.prompt_runtime import render_template
from ai_runtime_core.prompt_runtime import resolve_variable_value


WorkflowDefinition = dict[str, Any]
WorkflowContext = dict[str, Any]


@dataclass(slots=True)
class WorkflowLLMRequest:
    node_id: str
    model: str
    messages: list[dict[str, Any]]
    temperature: float | None = None
    response_format: dict[str, Any] | None = None
    extra_body: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowLLMResult:
    answer: str
    usage: dict[str, Any] = field(default_factory=dict)
    model: str = ""


@dataclass(slots=True)
class WorkflowSQLRequest:
    node_id: str
    sql: str
    params: list[Any] = field(default_factory=list)
    output_key: str = ""
    result_shape: str = "rows"
    max_rows: int = 100
    data_access: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowSQLResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False


@dataclass(slots=True)
class WorkflowRunResult:
    answer: str
    context: WorkflowContext
    trace: dict[str, Any]
    usage: dict[str, Any]


LLMExecutor = Callable[[WorkflowLLMRequest], WorkflowLLMResult]
SQLExecutor = Callable[[WorkflowSQLRequest], WorkflowSQLResult]


class WorkflowRuntimeError(RuntimeError):
    pass


def execute_workflow(
    definition: WorkflowDefinition,
    variables: dict[str, Any],
    *,
    llm_executor: LLMExecutor,
    sql_executor: SQLExecutor | None = None,
    max_steps: int = 50,
) -> WorkflowRunResult:
    normalized = normalize_workflow_definition(definition)
    nodes = {node["id"]: node for node in normalized["nodes"]}
    outgoing = outgoing_edges(normalized["edges"])
    current_id = start_node_id(normalized)
    context: WorkflowContext = {
        "variables": dict(variables),
        "nodes": {},
        "last": {},
    }
    trace_nodes: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}
    answer = ""

    for _ in range(max_steps):
        node = nodes.get(current_id)
        if not node:
            raise WorkflowRuntimeError(f"workflow node not found: {current_id}")
        node_type = str(node.get("type") or "").strip()
        started_at = time.perf_counter()
        trace_node: dict[str, Any] = {
            "node_id": current_id,
            "node_type": node_type,
            "status": "success",
        }
        try:
            if node_type == "start":
                output = {"variables": snapshot_value(context["variables"])}
            elif node_type == "llm":
                result = execute_llm_node(node, context, llm_executor)
                output = {"answer": result.answer, "usage": result.usage, "model": result.model}
                answer = result.answer
                merge_usage(usage, result.usage)
            elif node_type in {"sql", "sql_query"}:
                output = execute_sql_query_node(node, context, sql_executor)
            elif node_type in {"condition", "if_else"}:
                matched = evaluate_condition_node(node, context)
                output = {"matched": matched}
                trace_node["branch"] = "true" if matched else "false"
            elif node_type == "end":
                output = execute_end_node(node, context, answer)
                answer = str(output.get("answer") or answer)
                trace_node["output"] = snapshot_value(output)
                trace_node["elapsed_ms"] = elapsed_ms(started_at)
                trace_nodes.append(trace_node)
                break
            else:
                raise WorkflowRuntimeError(f"unsupported workflow node type: {node_type}")
            context["nodes"][current_id] = output
            context["last"] = output
            trace_node["output"] = snapshot_value(output)
            trace_node["elapsed_ms"] = elapsed_ms(started_at)
            trace_nodes.append(trace_node)
            next_id = next_node_id(current_id, outgoing, trace_node.get("branch"))
            if not next_id:
                break
            current_id = next_id
        except Exception as exc:
            trace_node["status"] = "failed"
            trace_node["error"] = str(exc)
            trace_node["elapsed_ms"] = elapsed_ms(started_at)
            trace_nodes.append(trace_node)
            raise
    else:
        raise WorkflowRuntimeError("workflow exceeded max steps")

    return WorkflowRunResult(
        answer=answer,
        context=context,
        usage=usage,
        trace={
            "workflow": {
                "nodes": trace_nodes,
                "final_node_id": current_id,
            }
        },
    )


def snapshot_value(value: Any) -> Any:
    return copy.deepcopy(value)


def normalize_workflow_definition(definition: WorkflowDefinition) -> WorkflowDefinition:
    nodes = definition.get("nodes") if isinstance(definition.get("nodes"), list) else []
    edges = definition.get("edges") if isinstance(definition.get("edges"), list) else []
    normalized_nodes = [normalize_node(item) for item in nodes if isinstance(item, dict)]
    normalized_edges = [normalize_edge(item) for item in edges if isinstance(item, dict)]
    if not normalized_nodes:
        raise WorkflowRuntimeError("workflow requires at least one node")
    if not any(node["type"] == "start" for node in normalized_nodes):
        raise WorkflowRuntimeError("workflow requires a start node")
    return {"nodes": normalized_nodes, "edges": normalized_edges}


def normalize_node(node: dict[str, Any]) -> dict[str, Any]:
    node_id = str(node.get("id") or "").strip()
    node_type = str(node.get("type") or node.get("node_type") or "").strip()
    if not node_id:
        raise WorkflowRuntimeError("workflow node id is required")
    if not node_type:
        raise WorkflowRuntimeError(f"workflow node type is required: {node_id}")
    data = node.get("data") if isinstance(node.get("data"), dict) else {}
    return {"id": node_id, "type": node_type, "data": data}


def normalize_edge(edge: dict[str, Any]) -> dict[str, Any]:
    source = str(edge.get("source") or "").strip()
    target = str(edge.get("target") or "").strip()
    if not source or not target:
        raise WorkflowRuntimeError("workflow edge source and target are required")
    return {
        "id": str(edge.get("id") or f"{source}-{target}"),
        "source": source,
        "target": target,
        "source_handle": str(edge.get("sourceHandle") or edge.get("source_handle") or "").strip(),
    }


def start_node_id(definition: WorkflowDefinition) -> str:
    for node in definition["nodes"]:
        if node["type"] == "start":
            return str(node["id"])
    raise WorkflowRuntimeError("workflow requires a start node")


def outgoing_edges(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        result.setdefault(str(edge["source"]), []).append(edge)
    return result


def next_node_id(current_id: str, outgoing: dict[str, list[dict[str, Any]]], branch: Any = None) -> str:
    edges = outgoing.get(current_id) or []
    if branch in {"true", "false"}:
        for edge in edges:
            if edge.get("source_handle") == branch:
                return str(edge["target"])
    return str(edges[0]["target"]) if edges else ""


def execute_llm_node(node: dict[str, Any], context: WorkflowContext, llm_executor: LLMExecutor) -> WorkflowLLMResult:
    data = node["data"]
    model = str(data.get("model") or data.get("route_key") or "").strip()
    if not model:
        raise WorkflowRuntimeError(f"LLM node model is required: {node['id']}")
    variables = workflow_template_context(context)
    messages = render_llm_messages(data, variables)
    if not messages:
        raise WorkflowRuntimeError(f"LLM node prompt is required: {node['id']}")
    result = llm_executor(
        WorkflowLLMRequest(
            node_id=node["id"],
            model=model,
            messages=messages,
            temperature=float(data["temperature"]) if data.get("temperature") is not None else None,
            response_format=data.get("response_format") if isinstance(data.get("response_format"), dict) else None,
            extra_body=data.get("extra_body") if isinstance(data.get("extra_body"), dict) else {},
        )
    )
    output_key = str(data.get("output_key") or "").strip()
    if output_key:
        assign_path(context["variables"], output_key, result.answer)
    return result


def execute_sql_query_node(
    node: dict[str, Any],
    context: WorkflowContext,
    sql_executor: SQLExecutor | None,
) -> dict[str, Any]:
    if sql_executor is None:
        raise WorkflowRuntimeError(f"SQL executor is required for node: {node['id']}")
    data = node["data"]
    variables = workflow_template_context(context)
    sql = render_template(str(data.get("sql") or data.get("query") or ""), variables).strip()
    if not sql:
        raise WorkflowRuntimeError(f"SQL query is required: {node['id']}")
    ensure_readonly_sql(sql)
    params = render_sql_params(data.get("params"), variables)
    output_key = str(data.get("output_key") or "").strip()
    if not output_key:
        raise WorkflowRuntimeError(f"SQL node output_key is required: {node['id']}")
    result_shape = str(data.get("result_shape") or "rows").strip().lower()
    if result_shape not in {"rows", "first", "scalar"}:
        raise WorkflowRuntimeError(f"unsupported SQL result_shape: {result_shape}")
    max_rows = bounded_max_rows(data.get("max_rows"))
    result = sql_executor(
        WorkflowSQLRequest(
            node_id=node["id"],
            sql=sql,
            params=params,
            output_key=output_key,
            result_shape=result_shape,
            max_rows=max_rows,
            data_access=data.get("data_access") if isinstance(data.get("data_access"), dict) else {},
        )
    )
    output = sql_output_payload(result, result_shape)
    assign_path(context["variables"], output_key, output)
    return output


def render_sql_params(value: Any, variables: dict[str, Any]) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        rendered = render_template(value, variables).strip()
        if not rendered:
            return []
        try:
            value = json.loads(rendered)
        except json.JSONDecodeError:
            return [rendered]
    if isinstance(value, list):
        return [resolve_sql_param(item, variables) for item in value]
    if isinstance(value, dict):
        return [resolve_sql_param(value[key], variables) for key in sorted(value)]
    raise WorkflowRuntimeError("SQL params must be an array, object, JSON string, or empty")


def resolve_sql_param(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{{") and stripped.endswith("}}"):
            return resolve_variable_value(variables, stripped[2:-2].strip())
        return render_template(value, variables)
    return value


def ensure_readonly_sql(sql: str) -> None:
    compact = strip_sql_comments(sql).strip()
    if not compact:
        raise WorkflowRuntimeError("SQL query is required")
    statements = [item.strip() for item in compact.split(";") if item.strip()]
    if len(statements) > 1 or (compact.endswith(";") and len(statements) != 1):
        raise WorkflowRuntimeError("SQL node only supports a single read-only statement")
    first_token = first_sql_token(compact)
    if first_token not in {"select", "with"}:
        raise WorkflowRuntimeError("SQL node only supports SELECT queries")
    dangerous = re.search(
        r"\b(insert|update|delete|drop|alter|truncate|create|replace|merge|call|execute|grant|revoke)\b",
        compact,
        flags=re.IGNORECASE,
    )
    if dangerous:
        raise WorkflowRuntimeError(f"SQL node rejected non-read-only keyword: {dangerous.group(1).upper()}")


def strip_sql_comments(sql: str) -> str:
    without_line_comments = re.sub(r"--.*?(?=\r?\n|$)", " ", sql)
    return re.sub(r"/\*.*?\*/", " ", without_line_comments, flags=re.DOTALL)


def first_sql_token(sql: str) -> str:
    match = re.match(r"\s*([a-zA-Z_]+)", sql)
    return match.group(1).lower() if match else ""


def bounded_max_rows(value: Any) -> int:
    try:
        parsed = int(value or 100)
    except (TypeError, ValueError):
        parsed = 100
    return max(1, min(1000, parsed))


def sql_output_payload(result: WorkflowSQLResult, result_shape: str) -> dict[str, Any]:
    rows = snapshot_value(result.rows)
    first = rows[0] if rows else None
    scalar = first.get(result.columns[0]) if isinstance(first, dict) and result.columns else None
    return {
        "rows": rows,
        "first": first,
        "scalar": scalar,
        "columns": list(result.columns),
        "row_count": int(result.row_count),
        "result_shape": result_shape,
        "truncated": bool(result.truncated),
    }


def render_llm_messages(data: dict[str, Any], variables: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for role, field_name in (
        ("system", "system_prompt"),
        ("developer", "developer_prompt"),
        ("user", "user_prompt_template"),
    ):
        content = render_template(str(data.get(field_name) or ""), variables)
        if not content.strip():
            continue
        messages.append({"role": role, "content": render_user_content(content, variables) if role == "user" else content})
    return messages


def render_user_content(text: str, variables: dict[str, Any]) -> str | list[dict[str, Any]]:
    media_parts = media_content_parts(variables)
    return [{"type": "text", "text": text}, *media_parts] if media_parts else text


def evaluate_condition_node(node: dict[str, Any], context: WorkflowContext) -> bool:
    data = node["data"]
    conditions = data.get("conditions") if isinstance(data.get("conditions"), list) else []
    if not conditions:
        conditions = [{"left": data.get("left"), "operator": data.get("operator") or "exists", "right": data.get("right")}]
    mode = str(data.get("mode") or "all").strip().lower()
    results = [evaluate_condition(item, context) for item in conditions if isinstance(item, dict)]
    return any(results) if mode == "any" else all(results)


def evaluate_condition(condition: dict[str, Any], context: WorkflowContext) -> bool:
    left = resolve_workflow_value(condition.get("left"), context)
    right = resolve_workflow_value(condition.get("right"), context)
    operator = str(condition.get("operator") or "exists").strip()
    if operator == "exists":
        return left not in (None, "")
    if operator == "empty":
        return left in (None, "")
    if operator == "equals":
        return str(left) == str(right)
    if operator == "not_equals":
        return str(left) != str(right)
    if operator == "contains":
        return str(right) in str(left)
    if operator == "not_contains":
        return str(right) not in str(left)
    if operator in {"gt", "gte", "lt", "lte"}:
        left_number = float(left or 0)
        right_number = float(right or 0)
        return {
            "gt": left_number > right_number,
            "gte": left_number >= right_number,
            "lt": left_number < right_number,
            "lte": left_number <= right_number,
        }[operator]
    raise WorkflowRuntimeError(f"unsupported condition operator: {operator}")


def execute_end_node(node: dict[str, Any], context: WorkflowContext, answer: str) -> dict[str, Any]:
    data = node["data"]
    output = data.get("output")
    if output is None:
        output = data.get("output_template")
    if output is None:
        return {"answer": answer}
    resolved = resolve_workflow_value(output, context)
    return {"answer": str(resolved or "")}


def resolve_workflow_value(value: Any, context: WorkflowContext) -> Any:
    if not isinstance(value, str):
        return value
    variables = workflow_template_context(context)
    stripped = value.strip()
    if stripped.startswith("{{") and stripped.endswith("}}"):
        return resolve_variable_value(variables, stripped[2:-2].strip())
    return render_template(value, variables)


def workflow_template_context(context: WorkflowContext) -> dict[str, Any]:
    variables = context.get("variables") if isinstance(context.get("variables"), dict) else {}
    nodes = context.get("nodes") if isinstance(context.get("nodes"), dict) else {}
    last = context.get("last") if isinstance(context.get("last"), dict) else {}
    return {**variables, "variables": variables, "nodes": nodes, "last": last}


def assign_path(target: dict[str, Any], key: str, value: Any) -> None:
    parts = key.split(".")
    current = target
    for part in parts[:-1]:
        nested = current.get(part)
        if not isinstance(nested, dict):
            nested = {}
            current[part] = nested
        current = nested
    current[parts[-1]] = value


def merge_usage(target: dict[str, Any], usage: dict[str, Any]) -> None:
    for key, value in usage.items():
        if isinstance(value, (int, float)):
            target[key] = target.get(key, 0) + value


def elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)
