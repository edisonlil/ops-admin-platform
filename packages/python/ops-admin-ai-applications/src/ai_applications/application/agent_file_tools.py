from __future__ import annotations

import base64
import fnmatch
import json
import time
from pathlib import Path
from typing import Any

from ai_applications.application.sandbox_settings import resolve_agent_workspace_root


TOOL_NAMES = {"list_files", "find_files", "read_file", "write_file", "append_file", "search_files"}
MAX_CALLS = 8
MAX_READ_CHARS = 100_000
DEFAULT_READ_CHARS = 20_000
MAX_WRITE_BYTES = 2 * 1024 * 1024
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SEARCH_MATCHES = 100
TEXT_EXTENSIONS = {
    ".cfg",
    ".conf",
    ".csv",
    ".env",
    ".html",
    ".ini",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".py",
    ".sql",
    ".text",
    ".toml",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
class AgentFileToolError(ValueError):
    pass


def enabled(app: dict[str, Any], payload: dict[str, Any]) -> bool:
    request_value = optional_bool(payload.get("file_tools_enabled"))
    if request_value is not None:
        return request_value
    runtime_config = app.get("runtime_config") if isinstance(app.get("runtime_config"), dict) else {}
    agent_config = runtime_config.get("agent") if isinstance(runtime_config.get("agent"), dict) else {}
    agent_value = optional_bool(agent_config.get("file_tools_enabled"))
    if agent_value is not None:
        return agent_value
    file_tool_config = runtime_config.get("file_tools") if isinstance(runtime_config.get("file_tools"), dict) else {}
    config_value = optional_bool(file_tool_config.get("enabled"))
    return True if config_value is None else config_value


def optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled"}:
        return False
    return None


def prepare_workspace(
    app: dict[str, Any],
    conversation: dict[str, Any],
    payload: dict[str, Any],
    files: list[dict[str, Any]],
) -> dict[str, Any]:
    if not enabled(app, payload):
        return {"enabled": False}
    workspace = workspace_path(app, conversation)
    try:
        workspace.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AgentFileToolError(f"agent file workspace unavailable: {exc}") from exc
    return {
        "enabled": True,
        "path": workspace,
        "display_path": "/workspace",
        "uploads": materialize_uploads(workspace, files),
    }


def workspace_path(app: dict[str, Any], conversation: dict[str, Any]) -> Path:
    root = Path(resolve_agent_workspace_root(app))
    tenant_part = safe_workspace_part(f"tenant_{app.get('tenant_id') or 0}", fallback="tenant_0")
    app_part = safe_workspace_part(app.get("app_key"), fallback="app")
    conversation_part = safe_workspace_part(conversation.get("conversation_key"), fallback="conversation")
    return root / tenant_part / app_part / conversation_part


def safe_workspace_part(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)
    cleaned = cleaned.strip("._-")[:80]
    return cleaned or fallback


def materialize_uploads(workspace: Path, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    uploads_dir = workspace / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    uploads: list[dict[str, Any]] = []
    for index, item in enumerate(files[:50], start=1):
        name = safe_filename(item.get("name") or item.get("filename") or f"upload-{index}.txt")
        relative_path = f"uploads/{name}"
        try:
            data = upload_bytes(item)
            if data is None:
                uploads.append({"name": name, "path": relative_path, "status": "skipped", "reason": "no_inline_content"})
                continue
            if len(data) > MAX_UPLOAD_BYTES:
                uploads.append({"name": name, "path": relative_path, "status": "skipped", "reason": "too_large", "size": len(data)})
                continue
            target = unique_upload_path(uploads_dir, name)
            target.write_bytes(data)
            uploads.append(
                {
                    "name": target.name,
                    "path": relative_path_for(workspace, target),
                    "status": "ready",
                    "size": len(data),
                    "mime_type": str(item.get("mime_type") or item.get("content_type") or ""),
                }
            )
        except (OSError, ValueError) as exc:
            uploads.append({"name": name, "path": relative_path, "status": "failed", "reason": str(exc)})
    return uploads


def safe_filename(value: Any) -> str:
    text = str(value or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    invalid = '<>:"|?*\x00'
    cleaned = "".join("_" if ch in invalid or ord(ch) < 32 else ch for ch in text)
    cleaned = cleaned.strip(" .")
    if cleaned in {"", ".", ".."}:
        cleaned = "upload.txt"
    return cleaned[:160]


def unique_upload_path(directory: Path, filename: str) -> Path:
    target = directory / filename
    if not target.exists():
        return target
    stem = target.stem or "upload"
    suffix = target.suffix
    for index in range(2, 1000):
        candidate = directory / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise ValueError("too many uploads with the same file name")


def upload_bytes(item: dict[str, Any]) -> bytes | None:
    if "text" in item or "content" in item:
        return str(item.get("text") if "text" in item else item.get("content") or "").encode("utf-8")
    data_url = str(item.get("data_url") or item.get("dataUrl") or "").strip()
    if data_url:
        if "," not in data_url:
            return None
        header, encoded = data_url.split(",", 1)
        if "base64" not in {part.strip().lower() for part in header.split(";")}:
            return encoded.encode("utf-8")
        return base64.b64decode(encoded)
    encoded = str(item.get("base64") or "").strip()
    if encoded:
        return base64.b64decode(encoded)
    return None


def build_prompt(workspace: dict[str, Any] | None) -> str:
    if not workspace or not workspace.get("enabled"):
        return ""
    uploads = [
        {key: upload.get(key) for key in ("name", "path", "status", "size", "mime_type", "reason") if upload.get(key) not in (None, "")}
        for upload in workspace.get("uploads", [])
        if isinstance(upload, dict)
    ]
    payload = {
        "workspace": workspace.get("display_path") or "/workspace",
        "path_policy": "All paths are relative to the workspace. Absolute paths, drive letters, and '..' are rejected.",
        "tools": {
            "list_files": {"path": ".", "pattern": "*", "recursive": False, "max_items": 100},
            "find_files": {"path": ".", "pattern": "*.md", "recursive": True, "max_items": 100},
            "read_file": {"path": "relative/path.txt", "max_chars": 20000},
            "write_file": {"path": "relative/path.txt", "content": "text", "overwrite": False},
            "append_file": {"path": "relative/path.txt", "content": "text"},
            "search_files": {"query": "text", "path": ".", "pattern": "*", "recursive": True, "max_matches": 50},
        },
        "uploaded_files": uploads,
    }
    return (
        "Agent file workspace tools are available for this conversation. "
        "If you need to read, write, find, or search files, respond with JSON only in this shape: "
        '{"tool_calls":[{"tool":"read_file","arguments":{"path":"uploads/example.txt"}}]}. '
        "If you do not need file tools, answer normally. After tool results are supplied, answer normally.\n"
        f"{json_dump(payload)}"
    )


def stream_preflight_required(workspace: dict[str, Any] | None, payload: dict[str, Any]) -> bool:
    if not workspace or not workspace.get("enabled"):
        return False
    request_value = optional_bool(payload.get("file_tool_preflight"))
    if request_value is not None:
        return request_value
    return True


def parse_tool_request(answer: str) -> dict[str, Any]:
    payload = parse_json_text(answer)
    if not isinstance(payload, dict):
        return {}
    raw_calls = payload.get("tool_calls")
    if raw_calls is None:
        raw_calls = payload.get("tools")
    if not isinstance(raw_calls, list):
        return {}
    calls: list[dict[str, Any]] = []
    for raw in raw_calls[:MAX_CALLS]:
        if not isinstance(raw, dict):
            continue
        tool = str(raw.get("tool") or raw.get("name") or "").strip().lower()
        arguments = raw.get("arguments") if isinstance(raw.get("arguments"), dict) else raw.get("input")
        if tool in TOOL_NAMES:
            calls.append({"tool": tool, "arguments": dict(arguments) if isinstance(arguments, dict) else {}})
    return {"tool_calls": calls}


def parse_json_text(text: str) -> Any:
    candidate = str(text or "").strip()
    if not candidate:
        return None
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        return json.loads(candidate)
    except ValueError:
        return None


def protocol_final_answer(answer: str) -> str:
    payload = parse_json_text(answer)
    if not isinstance(payload, dict) or "final_answer" not in payload:
        return ""
    if set(payload.keys()).issubset({"final_answer"}):
        return str(payload.get("final_answer") or "")
    return ""


def execute_tool_calls(workspace: dict[str, Any], calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    workspace_path = workspace.get("path")
    if not isinstance(workspace_path, Path):
        return []
    results: list[dict[str, Any]] = []
    for index, call in enumerate(calls[:MAX_CALLS], start=1):
        started_at = time.perf_counter()
        tool = str(call.get("tool") or "").strip().lower()
        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        try:
            if tool == "list_files":
                output = list_files(workspace_path, arguments, recursive_default=False)
            elif tool == "find_files":
                output = list_files(workspace_path, arguments, recursive_default=True)
            elif tool == "read_file":
                output = read_file(workspace_path, arguments)
            elif tool == "write_file":
                output = write_file(workspace_path, arguments, append=False)
            elif tool == "append_file":
                output = write_file(workspace_path, arguments, append=True)
            elif tool == "search_files":
                output = search_files(workspace_path, arguments)
            else:
                raise AgentFileToolError(f"unsupported file tool: {tool}")
            results.append(
                {
                    "index": index,
                    "tool": tool,
                    "status": "success",
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
                    "arguments": safe_tool_arguments(arguments),
                    "error_code": exc.__class__.__name__,
                    "error_message": str(exc),
                    "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                }
            )
    return results


def safe_tool_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in arguments.items():
        if key == "content" and isinstance(value, str) and len(value) > 500:
            result[key] = value[:500] + "..."
        else:
            result[str(key)] = value
    return result


def list_files(workspace: Path, arguments: dict[str, Any], *, recursive_default: bool) -> dict[str, Any]:
    base = resolve_path(workspace, arguments.get("path") or ".")
    if not base.exists():
        raise AgentFileToolError("path does not exist")
    if not base.is_dir():
        raise AgentFileToolError("path is not a directory")
    pattern = safe_pattern(arguments.get("pattern") or "*")
    recursive = bool(arguments.get("recursive", recursive_default))
    max_items = max(1, min(500, int(arguments.get("max_items") or 100)))
    iterator = base.rglob("*") if recursive else base.iterdir()
    items: list[dict[str, Any]] = []
    for path in sorted(iterator, key=lambda item: relative_path_for(workspace, item)):
        relative = relative_path_for(workspace, path)
        if not pattern_matches(relative, path.name, pattern):
            continue
        stat = path.stat()
        items.append(
            {
                "path": relative,
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "size": 0 if path.is_dir() else int(stat.st_size),
                "modified_time": int(stat.st_mtime),
            }
        )
        if len(items) >= max_items:
            break
    return {"items": items, "truncated": len(items) >= max_items}


def read_file(workspace: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    path = resolve_path(workspace, required_argument(arguments, "path"))
    if not path.exists():
        raise AgentFileToolError("file does not exist")
    if not path.is_file():
        raise AgentFileToolError("path is not a file")
    max_chars = max(1, min(MAX_READ_CHARS, int(arguments.get("max_chars") or DEFAULT_READ_CHARS)))
    byte_limit = max(4096, max_chars * 4) + 1
    data = path.read_bytes()[:byte_limit]
    text = decode_text(data, path)
    truncated = len(text) > max_chars or path.stat().st_size > len(data)
    if len(text) > max_chars:
        text = text[:max_chars]
    return {
        "path": relative_path_for(workspace, path),
        "size": int(path.stat().st_size),
        "content": text,
        "truncated": truncated,
    }


def write_file(workspace: Path, arguments: dict[str, Any], *, append: bool) -> dict[str, Any]:
    path = resolve_path(workspace, required_argument(arguments, "path"))
    content = str(arguments.get("content") or "")
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_WRITE_BYTES:
        raise AgentFileToolError(f"content is too large; max {MAX_WRITE_BYTES} bytes")
    if path.exists() and path.is_dir():
        raise AgentFileToolError("path is a directory")
    if path.exists() and not append and not bool(arguments.get("overwrite", False)):
        raise AgentFileToolError("file already exists; set overwrite=true to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    if append:
        with path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(content)
    else:
        path.write_text(content, encoding="utf-8", newline="")
    return {
        "path": relative_path_for(workspace, path),
        "size": int(path.stat().st_size),
        "operation": "append" if append else "write",
    }


def search_files(workspace: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(required_argument(arguments, "query"))
    if not query:
        raise AgentFileToolError("query is required")
    base = resolve_path(workspace, arguments.get("path") or ".")
    if not base.exists():
        raise AgentFileToolError("path does not exist")
    pattern = safe_pattern(arguments.get("pattern") or "*")
    recursive = bool(arguments.get("recursive", True))
    max_matches = max(1, min(MAX_SEARCH_MATCHES, int(arguments.get("max_matches") or 50)))
    case_sensitive = bool(arguments.get("case_sensitive", False))
    needle = query if case_sensitive else query.lower()
    files = [base] if base.is_file() else list(base.rglob("*") if recursive else base.iterdir())
    matches: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for path in sorted(files, key=lambda item: relative_path_for(workspace, item)):
        if not path.is_file():
            continue
        relative = relative_path_for(workspace, path)
        if not pattern_matches(relative, path.name, pattern):
            continue
        if path.stat().st_size > MAX_WRITE_BYTES:
            skipped.append({"path": relative, "reason": "too_large"})
            continue
        try:
            text = decode_text(path.read_bytes(), path)
        except AgentFileToolError:
            skipped.append({"path": relative, "reason": "binary_or_unsupported"})
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            haystack = line if case_sensitive else line.lower()
            if needle not in haystack:
                continue
            matches.append({"path": relative, "line": line_number, "preview": line[:500]})
            if len(matches) >= max_matches:
                return {"matches": matches, "skipped": skipped, "truncated": True}
    return {"matches": matches, "skipped": skipped, "truncated": False}


def required_argument(arguments: dict[str, Any], key: str) -> Any:
    value = arguments.get(key)
    if value is None or str(value).strip() == "":
        raise AgentFileToolError(f"{key} is required")
    return value


def resolve_path(workspace: Path, raw_path: Any) -> Path:
    text = str(raw_path or ".").replace("\\", "/").strip()
    if not text:
        text = "."
    if "\x00" in text or ":" in text:
        raise AgentFileToolError("path is not allowed")
    candidate = Path(text)
    if candidate.is_absolute():
        raise AgentFileToolError("absolute paths are not allowed")
    parts = [part for part in text.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        raise AgentFileToolError("parent path segments are not allowed")
    root = workspace.resolve()
    resolved = (root.joinpath(*parts) if parts else root).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AgentFileToolError("path escapes workspace") from exc
    return resolved


def safe_pattern(value: Any) -> str:
    pattern = str(value or "*").replace("\\", "/").strip()[:200] or "*"
    if "\x00" in pattern or ":" in pattern:
        raise AgentFileToolError("pattern is not allowed")
    if pattern.startswith("/") or any(part == ".." for part in pattern.split("/")):
        raise AgentFileToolError("pattern is not allowed")
    return pattern


def pattern_matches(relative: str, name: str, pattern: str) -> bool:
    return fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(name, pattern)


def relative_path_for(workspace: Path, path: Path) -> str:
    return path.resolve(strict=False).relative_to(workspace.resolve()).as_posix()


def decode_text(data: bytes, path: Path) -> str:
    if b"\x00" in data[:4096] and path.suffix.lower() not in TEXT_EXTENSIONS:
        raise AgentFileToolError("file appears to be binary")
    for encoding in ("utf-8-sig", "utf-16", "gb18030", "big5", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise AgentFileToolError("file cannot be decoded as text")


def build_follow_up_messages(
    messages: list[dict[str, Any]],
    assistant_tool_request: str,
    tool_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        *messages,
        {"role": "assistant", "content": assistant_tool_request},
        {
            "role": "user",
            "content": (
                "Agent file tool results:\n"
                f"{json_dump(tool_results)}\n\n"
                "Use these results to answer the user's latest request. Do not emit another tool_calls JSON object now."
            ),
        },
    ]


def merge_usage(*items: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                merged[key] = merged.get(key, 0) + value
            elif key not in merged:
                merged[key] = value
    return merged


def snapshot(workspace: dict[str, Any] | None) -> dict[str, Any]:
    if not workspace or not workspace.get("enabled"):
        return {"enabled": False}
    return {
        "enabled": True,
        "display_path": workspace.get("display_path") or "/workspace",
        "uploads": workspace.get("uploads") if isinstance(workspace.get("uploads"), list) else [],
    }


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
