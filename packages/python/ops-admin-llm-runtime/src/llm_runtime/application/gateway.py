from __future__ import annotations

from pathlib import Path
import time
import uuid
from typing import Any, Iterable, Iterator
import json

from framework.llm_core import CommandLLMClient, LLMClient, LLMResponse, MiniMaxLLMClient, OpenAICompatibleLLMClient
from llm_runtime.domain.models import RoutingEntry, RoutingPolicy, RouteResolution
from llm_runtime.infrastructure.persistence.bootstrap import require_llm_schema
from llm_runtime.infrastructure.persistence import repositories
from system.application.database import connect, resolve_database_url, resolve_db_path
from system.interfaces.http import current_request_id


class LLMRoutingError(RuntimeError):
    pass


def database_target() -> str | Path:
    database_url = resolve_database_url()
    if database_url:
        return database_url
    return resolve_db_path()


def generate(
    *,
    task_key: str,
    prompt: str | None = None,
    messages: list[dict[str, str]] | None = None,
    response_format: str | None = None,
    database_target_override: str | Path | None = None,
    correlation_id: str | None = None,
) -> LLMResponse:
    text_prompt = prompt_from_messages(prompt=prompt, messages=messages)
    target = database_target_override or database_target()
    with connect(target, readonly=False) as conn:
        require_llm_schema(conn)
        resolution = repositories.resolve_route(conn, task_key)
        if not resolution:
            raise LLMRoutingError(f"LLM route not configured for task: {task_key}")
        return generate_with_resolution(
            conn=conn,
            resolution=resolution,
            prompt=text_prompt,
            response_format=response_format,
            correlation_id=correlation_id,
        )


def chat_completions(
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float | None = None,
    response_format: dict[str, Any] | None = None,
    extra_body: dict[str, Any] | None = None,
    enable_think_output: bool | None = None,
    database_target_override: str | Path | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    target = database_target_override or database_target()
    model_key_or_route = model.strip()
    if not model_key_or_route:
        raise LLMRoutingError("model is required")
    with connect(target, readonly=False) as conn:
        require_llm_schema(conn)
        entry = repositories.entry_for_model(conn, model_key_or_route)
        if entry:
            response = chat_with_entry(
                conn=conn,
                entry=entry,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                extra_body=extra_body,
                enable_think_output=enable_think_output,
                correlation_id=correlation_id,
            )
            return openai_chat_response(model=entry.model_key, response=response)
        response_format_name = openai_response_format_name(response_format)
        resolution = repositories.resolve_route(conn, model_key_or_route)
        if not resolution:
            raise LLMRoutingError(f"LLM route not configured for task: {model_key_or_route}")
        response = generate_with_resolution(
            conn=conn,
            resolution=resolution,
            prompt=prompt_from_messages(prompt=None, messages=messages_as_text_messages(messages)),
            response_format=response_format_name,
            enable_think_output=enable_think_output,
            correlation_id=correlation_id,
        )
        return openai_chat_response(model=model_key_or_route, response=response)


def stream_chat_completions(
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float | None = None,
    response_format: dict[str, Any] | None = None,
    extra_body: dict[str, Any] | None = None,
    enable_think_output: bool | None = None,
    database_target_override: str | Path | None = None,
    correlation_id: str | None = None,
) -> Iterator[str]:
    target = database_target_override or database_target()
    model_key_or_route = model.strip()
    if not model_key_or_route:
        raise LLMRoutingError("model is required")
    with connect(target, readonly=False) as conn:
        require_llm_schema(conn)
        entry = repositories.entry_for_model(conn, model_key_or_route)
        if not entry:
            resolution = repositories.resolve_route(conn, model_key_or_route)
            if not resolution or not resolution.policy.entries:
                raise LLMRoutingError(f"LLM route not configured for task: {model_key_or_route}")
            entry = resolution.policy.entries[0]
        if temperature is not None:
            entry = replace_entry_temperature(entry, temperature)
        request_extra_body = dict(extra_body or {})
        if response_format:
            request_extra_body["response_format"] = response_format
        client = client_for_entry(entry)
        if not hasattr(client, "stream_chat_completions"):
            response = chat_with_entry(
                conn=conn,
                entry=entry,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                extra_body=extra_body,
                enable_think_output=enable_think_output,
                correlation_id=correlation_id,
            )
            yield from openai_chat_completion_stream_events(openai_chat_response(model=model_key_or_route, response=response))
            return
        started_at = time.perf_counter()
        content_parts: list[str] = []
        try:
            for event in client.stream_chat_completions(  # type: ignore[attr-defined]
                messages,
                extra_body=request_extra_body,
                enable_think_output=entry.enable_think_output if enable_think_output is None else enable_think_output,
            ):
                content_parts.append(stream_event_content(event))
                yield event
            response = LLMResponse(content="".join(content_parts), elapsed_seconds=time.perf_counter() - started_at)
            repositories.record_call_log(
                conn,
                call_log_payload(
                    resolution=RouteResolution(
                        task_key=f"debug.model.{entry.model_key}",
                        route_key=entry.model_key,
                        policy=single_entry_policy(entry),
                    ),
                    entry=entry,
                    status="success",
                    is_fallback=False,
                    response=response,
                    correlation_id=correlation_id,
                ),
            )
        except Exception as exc:
            repositories.record_call_log(
                conn,
                call_log_payload(
                    resolution=RouteResolution(
                        task_key=f"debug.model.{entry.model_key}",
                        route_key=entry.model_key,
                        policy=single_entry_policy(entry),
                    ),
                    entry=entry,
                    status="failed",
                    is_fallback=False,
                    error=exc,
                    correlation_id=correlation_id,
                ),
            )
            yield sse_error(str(exc))
            yield "data: [DONE]\n\n"


def chat_with_entry(
    *,
    conn: Any,
    entry: RoutingEntry,
    messages: list[dict[str, Any]],
    temperature: float | None,
    response_format: dict[str, Any] | None,
    extra_body: dict[str, Any] | None,
    enable_think_output: bool | None,
    correlation_id: str | None,
) -> LLMResponse:
    request_extra_body = dict(extra_body or {})
    if response_format:
        request_extra_body["response_format"] = response_format
    if temperature is not None:
        entry = replace_entry_temperature(entry, temperature)
    try:
        client = client_for_entry(entry)
        if not hasattr(client, "generate_chat_response"):
            response = client.generate_response(prompt_from_messages(prompt=None, messages=messages_as_text_messages(messages)))  # type: ignore[attr-defined]
        else:
            response = client.generate_chat_response(  # type: ignore[attr-defined]
                messages,
                extra_body=request_extra_body,
                enable_think_output=entry.enable_think_output if enable_think_output is None else enable_think_output,
            )
        repositories.record_call_log(
            conn,
            call_log_payload(
                resolution=RouteResolution(
                    task_key=f"debug.model.{entry.model_key}",
                    route_key=entry.model_key,
                    policy=single_entry_policy(entry),
                ),
                entry=entry,
                status="success",
                is_fallback=False,
                response=response,
                correlation_id=correlation_id,
            ),
        )
        return response
    except Exception as exc:
        repositories.record_call_log(
            conn,
            call_log_payload(
                resolution=RouteResolution(
                    task_key=f"debug.model.{entry.model_key}",
                    route_key=entry.model_key,
                    policy=single_entry_policy(entry),
                ),
                entry=entry,
                status="failed",
                is_fallback=False,
                error=exc,
                correlation_id=correlation_id,
            ),
        )
        raise


def prompt_from_messages(*, prompt: str | None, messages: list[dict[str, str]] | None) -> str:
    if prompt is not None:
        return prompt
    if not messages:
        return ""
    parts: list[str] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = str(message.get("content", ""))
        parts.append(f"{role}: {content}" if role else content)
    return "\n".join(parts)


def messages_as_text_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "role": str(message.get("role") or "user"),
            "content": message_content_as_text(message.get("content")),
        }
        for message in messages
    ]


def message_content_as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(value or "")


def generate_with_resolution(
    *,
    conn: Any,
    resolution: RouteResolution,
    prompt: str,
    response_format: str | None,
    enable_think_output: bool | None = None,
    correlation_id: str | None,
) -> LLMResponse:
    failures: list[str] = []
    for index, entry in enumerate(resolution.policy.entries):
        try:
            client = client_for_entry(entry, response_format=response_format)
            response = client.generate_response(
                prompt,
                enable_think_output=entry.enable_think_output if enable_think_output is None else enable_think_output,
            )  # type: ignore[attr-defined]
            repositories.record_call_log(
                conn,
                call_log_payload(
                    resolution=resolution,
                    entry=entry,
                    status="success",
                    is_fallback=index > 0,
                    response=response,
                    correlation_id=correlation_id,
                ),
            )
            return response
        except Exception as exc:
            failures.append(f"{entry.model_key}: {exc}")
            repositories.record_call_log(
                conn,
                call_log_payload(
                    resolution=resolution,
                    entry=entry,
                    status="failed",
                    is_fallback=index > 0,
                    error=exc,
                    correlation_id=correlation_id,
                ),
            )
            if not is_recoverable_error(exc):
                break
    raise LLMRoutingError(f"LLM route failed for task {resolution.task_key}: {'; '.join(failures)}")


def client_for_entry(entry: RoutingEntry, *, response_format: str | None = None) -> LLMClient:
    extra_body = dict(entry.provider_extra_body)
    extra_body.update(entry.extra_body)
    effective_response_format = response_format or entry.response_format
    if effective_response_format == "json":
        extra_body.setdefault("response_format", {"type": "json_object"})

    if entry.provider_key == "minimax":
        if not entry.api_key:
            raise LLMRoutingError("MiniMax LLM requires an API key")
        return MiniMaxLLMClient(
            api_key=entry.api_key,
            model=entry.model_name,
            base_url=entry.base_url or "https://api.minimaxi.com/v1",
            timeout_seconds=entry.timeout_seconds,
            temperature=entry.temperature,
            extra_body=extra_body,
            enable_think_output=entry.enable_think_output,
        )

    if entry.provider_key == "command":
        command = str(extra_body.get("command", "")).strip()
        if not command:
            raise LLMRoutingError("command LLM requires extra_body.command")
        return CommandLLMClient(command=command, enable_think_output=entry.enable_think_output)

    if not entry.api_key:
        raise LLMRoutingError(f"{entry.provider_key} LLM requires an API key")
    if not entry.base_url:
        raise LLMRoutingError(f"{entry.provider_key} LLM requires a base_url")
    return OpenAICompatibleLLMClient(
        provider_name=entry.provider_key,
        api_key=entry.api_key,
        model=entry.model_name,
        base_url=entry.base_url,
        timeout_seconds=entry.timeout_seconds,
        temperature=entry.temperature,
        extra_body=extra_body,
        enable_think_output=entry.enable_think_output,
    )


def single_entry_policy(entry: RoutingEntry) -> RoutingPolicy:
    return RoutingPolicy(
        id=entry.policy_id,
        route_key=entry.model_key,
        display_name=entry.model_key,
        strategy="direct",
        entries=[entry],
    )


def replace_entry_temperature(entry: RoutingEntry, temperature: float) -> RoutingEntry:
    return RoutingEntry(
        id=entry.id,
        policy_id=entry.policy_id,
        model_key=entry.model_key,
        provider_key=entry.provider_key,
        model_name=entry.model_name,
        provider_display_name=entry.provider_display_name,
        base_url=entry.base_url,
        api_key=entry.api_key,
        provider_extra_body=entry.provider_extra_body,
        model_capabilities=entry.model_capabilities,
        priority=entry.priority,
        temperature=temperature,
        timeout_seconds=entry.timeout_seconds,
        max_retries=entry.max_retries,
        response_format=entry.response_format,
        extra_body=entry.extra_body,
        enable_think_output=entry.enable_think_output,
    )


def openai_response_format_name(response_format: dict[str, Any] | None) -> str | None:
    if not response_format:
        return None
    return "json" if response_format.get("type") == "json_object" else None


def openai_chat_response(*, model: str, response: LLMResponse) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": response.usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def openai_chat_completion_stream_events(response: dict[str, Any]) -> list[str]:
    completion_id = str(response.get("id", ""))
    created = int(response.get("created", 0) or 0)
    model = str(response.get("model", ""))
    content = str((((response.get("choices") or [{}])[0].get("message") or {}).get("content") or ""))
    events = [
        sse_data(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            }
        )
    ]
    events.extend(
        sse_data(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
            }
        )
        for chunk in split_stream_content(content)
    )
    events.append(
        sse_data(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
        )
    )
    events.append("data: [DONE]\n\n")
    return events


def split_stream_content(content: str, chunk_size: int = 48) -> list[str]:
    if not content:
        return [""]
    return [content[index : index + chunk_size] for index in range(0, len(content), chunk_size)]


def sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def sse_error(message: str) -> str:
    return f"event: error\ndata: {json.dumps({'message': message}, ensure_ascii=False)}\n\n"


def stream_event_content(event: str) -> str:
    if not event.startswith("data: "):
        return ""
    data = event.removeprefix("data: ").strip()
    if not data or data == "[DONE]":
        return ""
    try:
        payload = json.loads(data)
    except Exception:
        return ""
    return str((((payload.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""))


def is_recoverable_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(token in text for token in ("timeout", "timed out", "429", "5xx", " 5", "temporar", "rate limit", "unavailable"))


def call_log_payload(
    *,
    resolution: RouteResolution,
    entry: RoutingEntry,
    status: str,
    is_fallback: bool,
    response: LLMResponse | None = None,
    error: Exception | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    usage = response.usage if response else {}
    return {
        "task_key": resolution.task_key,
        "route_key": resolution.route_key,
        "policy_id": resolution.policy.id,
        "entry_id": entry.id,
        "provider_key": entry.provider_key,
        "model_key": entry.model_key,
        "model_name": entry.model_name,
        "status": status,
        "is_fallback": is_fallback,
        "elapsed_ms": int((response.elapsed_seconds if response else 0.0) * 1000),
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
        "error_code": error.__class__.__name__ if error else "",
        "error_message": str(error) if error else "",
        "request_id": current_request_id(),
        "correlation_id": correlation_id or current_request_id(),
    }


class LLMGateway:
    def generate(self, **kwargs: Any) -> LLMResponse:
        return generate(**kwargs)


llm_gateway = LLMGateway()
