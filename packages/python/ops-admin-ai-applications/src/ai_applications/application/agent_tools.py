from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Any

from ai_applications.application import agent_file_tools
from ai_applications.application import skill_runtime


SHELL_TOOL_NAMES = {
    "bash",
    "sh",
    "shell",
    "shell.run",
    "cmd",
    "powershell",
    "run_command",
    "run_shell",
    "shell_exec",
    "execute_command",
    "terminal",
}
PYTHON_TOOL_NAMES = {"python", "python.run", "python_exec", "run_python"}
SUPPORTED_TOOL_NAMES = agent_file_tools.TOOL_NAMES | SHELL_TOOL_NAMES | PYTHON_TOOL_NAMES
MAX_TOOL_CALLS = agent_file_tools.MAX_CALLS
MAX_COMMAND_CHARS = 20_000
MAX_INLINE_WORKSPACE_FILES = 120
MAX_INLINE_WORKSPACE_FILE_BYTES = agent_file_tools.MAX_UPLOAD_BYTES
HIGH_RISK_PATTERNS = (
    r"\brm\s+(-[a-z]*[rf][a-z]*|-[a-z]*[fr][a-z]*)\s+(?:/|/\*|\*|\.|\./\*|\../\*|~)(?:\s|$|[;&|])",
    r"\b(del|erase)\s+(/s|/q|/f)",
    r"\b(format|mkfs|fdisk|parted|shutdown|reboot|halt|poweroff)\b",
    r"\bdd\s+.*\bof=/dev/",
    r"\bchmod\s+-R\s+777\s+/",
    r"\bchown\s+-R\s+[^;&|]+\s+/",
    r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:",
)
HIGH_RISK_PYTHON_PATTERNS = (
    r"shutil\.rmtree\s*\(\s*['\"](/|~|\.)",
    r"os\.remove\s*\(\s*['\"](/|~)",
    r"os\.system\s*\(\s*['\"][^'\"]*(rm\s+(-[a-z]*[rf][a-z]*|-[a-z]*[fr][a-z]*)|mkfs|format|shutdown|reboot)",
    r"subprocess\.[a-z_]+\s*\([^)]*(rm\s+(-[a-z]*[rf][a-z]*|-[a-z]*[fr][a-z]*)|mkfs|format|shutdown|reboot)",
)


class AgentToolError(ValueError):
    pass


class AgentToolRiskError(AgentToolError):
    pass


def build_prompt(workspace: dict[str, Any] | None) -> str:
    file_prompt = agent_file_tools.build_prompt(workspace)
    if not workspace or not workspace.get("enabled"):
        return file_prompt
    payload = {
        "workspace": workspace.get("display_path") or "/workspace",
        "tool_protocol": {
            "shape": {"tool_calls": [{"tool": "tool_name", "arguments": {}}]},
            "rules": [
                "Return JSON only when a tool is required.",
                "Use paths relative to the workspace.",
                "Do not emit XML/HTML style tool tags.",
                "After tool results are supplied, answer normally.",
                "Do not ask the user to confirm a tool call in solo execution mode.",
                "If an action is high-risk, do not call the tool; answer with a clear failure reason.",
            ],
        },
        "tools": {
            "shell.run": {
                "aliases": ["bash", "sh", "shell", "run_command"],
                "arguments": {"command": "ls -la uploads", "timeout_seconds": 30},
            },
            "python.run": {
                "aliases": ["python"],
                "arguments": {"code": "print('hello')", "timeout_seconds": 30},
            },
        },
    }
    return (
        f"{file_prompt}\n\n"
        "Agent execution tools are available through the same JSON tool_calls protocol. "
        "Use shell.run for shell commands and python.run for Python scripts when needed. "
        "Solo execution has no user confirmation step: evaluate risk yourself, call tools automatically when risk is acceptable, "
        "and stop with a failure reason when the requested action is high-risk. "
        "Bound sandbox skill packages are materialized into the workspace; python.run may import modules such as scripts.* from relative paths.\n"
        f"{json_dump(payload)}"
    )


def parse_tool_request(answer: str) -> dict[str, Any]:
    payload = parse_protocol_payload(answer)
    if not isinstance(payload, dict):
        return {}
    raw_calls = payload.get("tool_calls")
    if raw_calls is None:
        raw_calls = payload.get("tools") or payload.get("calls")
    if raw_calls is None and (payload.get("tool") or payload.get("name")):
        raw_calls = [payload]
    if not isinstance(raw_calls, list):
        return {}
    calls: list[dict[str, Any]] = []
    for raw in raw_calls[:MAX_TOOL_CALLS]:
        normalized = normalize_tool_call(raw)
        if normalized:
            calls.append(normalized)
    return {"tool_calls": calls}


def parse_protocol_payload(text: str) -> Any:
    raw = str(text or "").strip()
    if not raw:
        return None
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.IGNORECASE | re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    tool_match = re.search(r"<tool_call>\s*(.*?)\s*</tool_call>", raw, re.IGNORECASE | re.DOTALL)
    if tool_match:
        raw = tool_match.group(1).strip()
    raw = raw.strip("| \n\r\t")
    try:
        return json.loads(raw)
    except ValueError:
        pass
    first = raw.find("{")
    last = raw.rfind("}")
    if first >= 0 and last > first:
        try:
            return json.loads(raw[first : last + 1])
        except ValueError:
            return None
    return None


def normalize_tool_call(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    tool = normalize_tool_name(raw.get("tool") or raw.get("name"))
    if not tool:
        return None
    arguments = raw.get("arguments") if isinstance(raw.get("arguments"), dict) else raw.get("input")
    if not isinstance(arguments, dict):
        arguments = {}
    return {"tool": tool, "arguments": normalize_tool_arguments(tool, arguments)}


def normalize_tool_name(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in agent_file_tools.TOOL_NAMES:
        return raw
    if raw in SHELL_TOOL_NAMES:
        return "shell.run"
    if raw in PYTHON_TOOL_NAMES:
        return "python.run"
    return ""


def normalize_tool_arguments(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool == "shell.run":
        command = arguments.get("command")
        if command is None:
            command = arguments.get("cmd") or arguments.get("script") or arguments.get("input")
        result = dict(arguments)
        result["command"] = str(command or "")
        return result
    if tool == "python.run":
        code = arguments.get("code")
        if code is None:
            code = arguments.get("script") or arguments.get("command") or arguments.get("input")
        result = dict(arguments)
        result["code"] = str(code or "")
        return result
    return dict(arguments)


def protocol_final_answer(answer: str) -> str:
    return agent_file_tools.protocol_final_answer(answer)


def stream_preflight_required(workspace: dict[str, Any] | None, payload: dict[str, Any]) -> bool:
    return agent_file_tools.stream_preflight_required(workspace, payload)


def execute_tool_calls(workspace: dict[str, Any], calls: list[dict[str, Any]], *, run_context: dict[str, Any]) -> list[dict[str, Any]]:
    workspace_path = workspace.get("path")
    if not isinstance(workspace_path, Path):
        return []
    results: list[dict[str, Any]] = []
    for index, call in enumerate(calls[:MAX_TOOL_CALLS], start=1):
        started_at = time.perf_counter()
        tool = str(call.get("tool") or "").strip().lower()
        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        risk = assess_tool_risk(tool, arguments)
        try:
            if risk["level"] == "high":
                raise AgentToolRiskError(risk["reason"])
            if tool in agent_file_tools.TOOL_NAMES:
                output = agent_file_tool_output(workspace_path, tool, arguments)
            elif tool == "shell.run":
                output = run_shell_tool(workspace_path, arguments, run_context=run_context)
            elif tool == "python.run":
                output = run_python_tool(workspace_path, arguments, run_context=run_context)
            else:
                raise AgentToolError(f"unsupported agent tool: {tool}")
            results.append(
                {
                    "index": index,
                    "tool": tool,
                    "status": "success",
                    "risk": risk,
                    "arguments": safe_tool_arguments(arguments),
                    "output": output,
                    "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "index": index,
                    "tool": tool,
                    "status": "failed",
                    "risk": risk,
                    "arguments": safe_tool_arguments(arguments),
                    "error_code": exc.__class__.__name__,
                    "error_message": str(exc),
                    "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                }
            )
    return results


def assess_tool_risk(tool: str, arguments: dict[str, Any]) -> dict[str, str]:
    if tool == "shell.run":
        command = str(arguments.get("command") or arguments.get("cmd") or arguments.get("script") or "")
        return assess_script_risk(command, patterns=HIGH_RISK_PATTERNS)
    if tool == "python.run":
        code = str(arguments.get("code") or arguments.get("script") or arguments.get("command") or "")
        return assess_script_risk(code, patterns=HIGH_RISK_PYTHON_PATTERNS)
    return {"level": "low", "reason": "bounded workspace tool"}


def assess_script_risk(script: str, *, patterns: tuple[str, ...]) -> dict[str, str]:
    text = str(script or "").strip()
    normalized = " ".join(text.split())
    for pattern in patterns:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return {
                "level": "high",
                "reason": "tool call was blocked because it matched a high-risk destructive operation",
            }
    return {"level": "low", "reason": "sandboxed execution within the conversation workspace"}


def contains_high_risk_result(results: list[dict[str, Any]]) -> bool:
    for result in results:
        risk = result.get("risk") if isinstance(result.get("risk"), dict) else {}
        if risk.get("level") == "high" or result.get("error_code") == "AgentToolRiskError":
            return True
    return False


def high_risk_failure_message(results: list[dict[str, Any]]) -> str:
    tools = [
        str(result.get("tool") or "unknown")
        for result in results
        if (isinstance(result.get("risk"), dict) and result["risk"].get("level") == "high")
        or result.get("error_code") == "AgentToolRiskError"
    ]
    suffix = f"：{', '.join(tools)}" if tools else ""
    return f"工具调用风险过高，已中断任务，未执行高风险操作{suffix}。"


def agent_file_tool_output(workspace_path: Path, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool == "list_files":
        return agent_file_tools.list_files(workspace_path, arguments, recursive_default=False)
    if tool == "find_files":
        return agent_file_tools.list_files(workspace_path, arguments, recursive_default=True)
    if tool == "read_file":
        return agent_file_tools.read_file(workspace_path, arguments)
    if tool == "write_file":
        return agent_file_tools.write_file(workspace_path, arguments, append=False)
    if tool == "append_file":
        return agent_file_tools.write_file(workspace_path, arguments, append=True)
    if tool == "search_files":
        return agent_file_tools.search_files(workspace_path, arguments)
    raise AgentToolError(f"unsupported file tool: {tool}")


def run_shell_tool(workspace_path: Path, arguments: dict[str, Any], *, run_context: dict[str, Any]) -> dict[str, Any]:
    command = bounded_script(arguments.get("command"), label="command")
    entrypoint = "agent-task.sh"
    request = sandbox_request(
        workspace_path,
        {
            **run_context,
            "runtime_kind": "sandbox_shell",
            "skill_key": "agent.shell",
            "entrypoint": entrypoint,
            "content": command,
            "input": {"arguments": safe_tool_arguments(arguments), "workspace": "/workspace"},
        },
    )
    output = skill_runtime.run_sandbox_request(request)
    return with_workspace_changes(workspace_path, output)


def run_python_tool(workspace_path: Path, arguments: dict[str, Any], *, run_context: dict[str, Any]) -> dict[str, Any]:
    code = bounded_script(arguments.get("code"), label="code")
    entrypoint = "agent_task.py"
    request = sandbox_request(
        workspace_path,
        {
            **run_context,
            "runtime_kind": "sandbox_python",
            "skill_key": "agent.python",
            "entrypoint": entrypoint,
            "content": code,
            "input": {"arguments": safe_tool_arguments(arguments), "workspace": "/workspace"},
        },
    )
    output = skill_runtime.run_sandbox_request(request)
    return with_workspace_changes(workspace_path, output)


def sandbox_request(workspace_path: Path, base: dict[str, Any]) -> dict[str, Any]:
    runtime_config = base.get("runtime_config") if isinstance(base.get("runtime_config"), dict) else {}
    return {
        **base,
        "conversation_workspace": str(workspace_path.resolve()),
        "workspace_files": workspace_snapshot(workspace_path),
        "return_workspace_files": True,
        "runtime_config": runtime_config or {"entrypoint": base.get("entrypoint")},
        "runtime_constraints": {"network": "enabled"},
    }


def bounded_script(value: Any, *, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise AgentToolError(f"{label} is required")
    if len(text) > MAX_COMMAND_CHARS:
        raise AgentToolError(f"{label} is too large; max {MAX_COMMAND_CHARS} characters")
    return text


def workspace_snapshot(workspace_path: Path) -> list[dict[str, Any]]:
    root = workspace_path.resolve()
    files: list[dict[str, Any]] = []
    if not root.exists():
        return files
    paths = [path for path in root.rglob("*") if path.is_file()]
    for path in sorted(paths, key=lambda item: workspace_snapshot_sort_key(root, item)):
        if not path.is_file():
            continue
        try:
            relative = path.resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        data = path.read_bytes()
        if len(data) > MAX_INLINE_WORKSPACE_FILE_BYTES:
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            files.append({"path": relative, "base64": base64.b64encode(data).decode("ascii")})
        else:
            files.append({"path": relative, "content": content})
        if len(files) >= MAX_INLINE_WORKSPACE_FILES:
            break
    return files


def workspace_snapshot_sort_key(root: Path, path: Path) -> tuple[int, str]:
    try:
        relative = path.resolve().relative_to(root).as_posix()
    except ValueError:
        return (99, path.as_posix())
    if relative.startswith("uploads/"):
        return (0, relative)
    if relative.startswith("scripts/") or relative == "SKILL.md":
        return (1, relative)
    return (2, relative)


def apply_workspace_files(workspace_path: Path, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    written: list[dict[str, Any]] = []
    for item in files[:MAX_INLINE_WORKSPACE_FILES]:
        if not isinstance(item, dict):
            continue
        path_value = item.get("path")
        content = item.get("content")
        if not isinstance(content, str):
            continue
        target = agent_file_tools.resolve_path(workspace_path, path_value)
        encoded = content.encode("utf-8")
        if len(encoded) > agent_file_tools.MAX_WRITE_BYTES:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="")
        preview = content[:4000] + ("\n...[truncated]" if len(content) > 4000 else "")
        written.append(
            {
                "path": agent_file_tools.relative_path_for(workspace_path, target),
                "size": int(target.stat().st_size),
                "content_preview": preview,
            }
        )
    return written


def with_workspace_changes(workspace_path: Path, output: dict[str, Any]) -> dict[str, Any]:
    result = dict(output)
    files = output.get("workspace_files")
    if isinstance(files, list):
        result["workspace_changes"] = apply_workspace_files(workspace_path, files)
        result.pop("workspace_files", None)
    return truncate_output(result)


def truncate_output(value: Any, *, max_text: int = 120_000) -> Any:
    if isinstance(value, dict):
        return {str(key): truncate_output(item, max_text=max_text) for key, item in value.items()}
    if isinstance(value, list):
        return [truncate_output(item, max_text=max_text) for item in value[:100]]
    if isinstance(value, str) and len(value) > max_text:
        return value[:max_text] + "\n...[truncated]"
    return value


def safe_tool_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in arguments.items():
        normalized_key = str(key)
        if normalized_key in {"content", "code", "command", "cmd", "script"} and isinstance(value, str) and len(value) > 500:
            result[normalized_key] = value[:500] + "..."
        else:
            result[normalized_key] = value
    return result


def build_follow_up_messages(messages: list[dict[str, Any]], assistant_tool_request: str, tool_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        *messages,
        {"role": "assistant", "content": normalized_tool_request_text(assistant_tool_request)},
        {
            "role": "user",
            "content": (
                "Agent tool results:\n"
                f"{json_dump(tool_results)}\n\n"
                "Use these results to answer the user's latest request. Do not emit another tool_calls JSON object now."
            ),
        },
    ]


def normalized_tool_request_text(value: str) -> str:
    request = parse_tool_request(value)
    if request.get("tool_calls"):
        return json_dump(request)
    return str(value or "")


def merge_usage(*items: dict[str, Any]) -> dict[str, Any]:
    return agent_file_tools.merge_usage(*items)


def snapshot(workspace: dict[str, Any] | None) -> dict[str, Any]:
    return agent_file_tools.snapshot(workspace)


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
