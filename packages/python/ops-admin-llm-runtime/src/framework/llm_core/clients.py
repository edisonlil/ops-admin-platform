from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol


class LLMClient(Protocol):
    def generate(self, prompt: str, *, enable_think_output: bool | None = None) -> str:
        """Return model text for a single prompt."""


@dataclass(frozen=True)
class LLMResponse:
    content: str
    elapsed_seconds: float
    usage: dict[str, Any] = field(default_factory=dict)
    think_content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CommandLLMClient:
    command: str
    enable_think_output: bool = False

    def generate_response(self, prompt: str, *, enable_think_output: bool | None = None) -> LLMResponse:
        started_at = time.perf_counter()
        completed = subprocess.run(
            self.command,
            input=prompt,
            text=True,
            capture_output=True,
            shell=True,
            check=False,
        )
        elapsed_seconds = time.perf_counter() - started_at
        if completed.returncode != 0:
            raise RuntimeError(f"llm command failed: {completed.stderr.strip()}")
        content, think_content = normalize_think_output(
            completed.stdout,
            enable_think_output=self.enable_think_output if enable_think_output is None else enable_think_output,
        )
        return LLMResponse(content=content, elapsed_seconds=elapsed_seconds, think_content=think_content)

    def generate(self, prompt: str, *, enable_think_output: bool | None = None) -> str:
        return self.generate_response(prompt, enable_think_output=enable_think_output).content


@dataclass(frozen=True)
class MiniMaxLLMClient:
    api_key: str
    model: str = "MiniMax-M2.7"
    base_url: str = "https://api.minimaxi.com/v1"
    timeout_seconds: float = 120.0
    temperature: float = 0.1
    extra_body: dict[str, Any] = field(default_factory=dict)
    enable_think_output: bool = False

    def generate_response(self, prompt: str, *, enable_think_output: bool | None = None) -> LLMResponse:
        return self.generate_chat_response(
            [{"role": "user", "content": prompt}],
            enable_think_output=enable_think_output,
        )

    def generate_chat_response(
        self,
        messages: list[dict[str, Any]],
        *,
        extra_body: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any | None = None,
        enable_think_output: bool | None = None,
    ) -> LLMResponse:
        think_output_enabled = self.enable_think_output if enable_think_output is None else enable_think_output
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": normalize_chat_messages(messages),
            "temperature": self.temperature,
            "stream": False,
        }
        merged_extra_body = provider_extra_body(self.extra_body)
        merged_extra_body.update(provider_extra_body(extra_body or {}))
        if tools is not None:
            merged_extra_body["tools"] = tools
        normalized_tool_choice = normalize_tool_choice(tool_choice)
        if normalized_tool_choice is not None:
            merged_extra_body["tool_choice"] = normalized_tool_choice
        if think_output_enabled:
            merged_extra_body["reasoning_split"] = True
        else:
            merged_extra_body.pop("reasoning_split", None)
        payload.update(merged_extra_body)

        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            started_at = time.perf_counter()
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
            elapsed_seconds = time.perf_counter() - started_at
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"minimax request failed: HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"minimax request failed: {exc.reason}") from exc

        data = json.loads(response_body)
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"minimax response missing message: {response_body[:500]}") from exc
        if not isinstance(message, dict):
            raise RuntimeError("minimax response message must be an object")
        content = message_text(message.get("content"))
        think_content = first_text(
            message.get("reasoning_content"),
            message.get("reasoning"),
            message.get("think"),
            message.get("thinking"),
        )
        if not isinstance(content, str):
            raise RuntimeError("minimax response message content must be a string")
        usage = data.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        content, think_content = normalize_think_output(
            content,
            think_content=think_content,
            enable_think_output=think_output_enabled,
        )
        return LLMResponse(content=content, elapsed_seconds=elapsed_seconds, usage=usage, think_content=think_content)

    def generate(self, prompt: str, *, enable_think_output: bool | None = None) -> str:
        return self.generate_response(prompt, enable_think_output=enable_think_output).content

    def stream_chat_completions(
        self,
        messages: list[dict[str, Any]],
        *,
        extra_body: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any | None = None,
        enable_think_output: bool | None = None,
    ) -> Iterator[str]:
        think_output_enabled = self.enable_think_output if enable_think_output is None else enable_think_output
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": normalize_chat_messages(messages),
            "temperature": self.temperature,
            "stream": True,
        }
        merged_extra_body = provider_extra_body(self.extra_body)
        merged_extra_body.update(provider_extra_body(extra_body or {}))
        if tools is not None:
            merged_extra_body["tools"] = tools
        normalized_tool_choice = normalize_tool_choice(tool_choice)
        if normalized_tool_choice is not None:
            merged_extra_body["tool_choice"] = normalized_tool_choice
        if think_output_enabled:
            merged_extra_body["reasoning_split"] = True
        else:
            merged_extra_body.pop("reasoning_split", None)
        payload.update(merged_extra_body)
        yield from stream_openai_compatible_request(
            provider_name="minimax",
            api_key=self.api_key,
            base_url=self.base_url,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )


@dataclass(frozen=True)
class OpenAICompatibleLLMClient:
    provider_name: str
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float = 120.0
    temperature: float = 0.1
    extra_body: dict[str, Any] = field(default_factory=dict)
    enable_think_output: bool = False

    def generate_response(self, prompt: str, *, enable_think_output: bool | None = None) -> LLMResponse:
        return self.generate_chat_response(
            [{"role": "user", "content": prompt}],
            enable_think_output=enable_think_output,
        )

    def generate_chat_response(
        self,
        messages: list[dict[str, Any]],
        *,
        extra_body: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any | None = None,
        enable_think_output: bool | None = None,
    ) -> LLMResponse:
        think_output_enabled = self.enable_think_output if enable_think_output is None else enable_think_output
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": normalize_provider_chat_messages(self.provider_name, messages),
            "temperature": self.temperature,
            "stream": False,
        }
        merged_extra_body = provider_extra_body(self.extra_body)
        merged_extra_body.update(provider_extra_body(extra_body or {}))
        if tools is not None:
            merged_extra_body["tools"] = tools
        normalized_tool_choice = normalize_tool_choice(tool_choice)
        if normalized_tool_choice is not None:
            merged_extra_body["tool_choice"] = normalized_tool_choice
        payload.update(merged_extra_body)

        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            started_at = time.perf_counter()
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
            elapsed_seconds = time.perf_counter() - started_at
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{self.provider_name} request failed: HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"{self.provider_name} request failed: {exc.reason}") from exc

        data = json.loads(response_body)
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"{self.provider_name} response missing message: {response_body[:500]}") from exc
        if not isinstance(message, dict):
            raise RuntimeError(f"{self.provider_name} response message must be an object")
        content = message_text(message.get("content"))
        tool_calls = parse_tool_calls(message)
        think_content = first_text(
            message.get("reasoning_content"),
            message.get("reasoning"),
            message.get("think"),
            message.get("thinking"),
        )
        if not isinstance(content, str):
            raise RuntimeError(f"{self.provider_name} response message content must be a string")
        usage = data.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        content, think_content = normalize_think_output(
            content,
            think_content=think_content,
            enable_think_output=think_output_enabled,
        )
        return LLMResponse(
            content=content,
            elapsed_seconds=elapsed_seconds,
            usage=usage,
            think_content=think_content,
            tool_calls=tool_calls,
        )

    def generate(self, prompt: str, *, enable_think_output: bool | None = None) -> str:
        return self.generate_response(prompt, enable_think_output=enable_think_output).content

    def stream_chat_completions(
        self,
        messages: list[dict[str, Any]],
        *,
        extra_body: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any | None = None,
        enable_think_output: bool | None = None,
    ) -> Iterator[str]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": normalize_provider_chat_messages(self.provider_name, messages),
            "temperature": self.temperature,
            "stream": True,
        }
        merged_extra_body = provider_extra_body(self.extra_body)
        merged_extra_body.update(provider_extra_body(extra_body or {}))
        if tools is not None:
            merged_extra_body["tools"] = tools
        normalized_tool_choice = normalize_tool_choice(tool_choice)
        if normalized_tool_choice is not None:
            merged_extra_body["tool_choice"] = normalized_tool_choice
        payload.update(merged_extra_body)
        yield from stream_openai_compatible_request(
            provider_name=self.provider_name,
            api_key=self.api_key,
            base_url=self.base_url,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )


THINK_BLOCK_PATTERN = re.compile(r"<think\b[^>]*>(.*?)</think>", flags=re.IGNORECASE | re.DOTALL)

# `role: "developer"` 是 OpenAI 在 o 系列推理模型上引入的指令分层角色。
# 截至目前，全行业只有 OpenAI 原生（含 Azure OpenAI 的 o 系列）支持该 role；
# 其他 OpenAI 兼容 provider（dashscope、siliconflow、deepseek、kimi、mimo、
# 智谱、mistral、cohere、groq 等）以及 anthropic（用 Messages API、根本没有
# message 内的 system role）都不支持，发出去会直接 400。
# 业务层在 ai_applications.application 里把 system/developer 当作两个独立来源
# 拼消息，client 层负责按 provider 做兼容：
#   - provider == "openai" → 原样保留 developer（让 o 系列推理模型拿到分层指令）
#   - 其他所有 provider     → 把 developer 合并到最近的 system 后面，标注来源
# 这样业务代码不需要知道下游是哪个 provider，也不会因为切了模型就炸。
DEVELOPER_MERGE_SEPARATOR = "\n\n## Developer Notes\n"

# 哪些 provider 原生支持 role="developer"。
# 当前仅 OpenAI 原生。Azure OpenAI 的 o 系列应该走单独的 provider name（业务侧可扩展）。
DEVELOPER_AWARE_PROVIDERS: frozenset[str] = frozenset({"openai"})


def normalize_think_output(
    content: str,
    *,
    think_content: str = "",
    enable_think_output: bool = False,
) -> tuple[str, str]:
    embedded_think = "\n".join(match.group(1).strip() for match in THINK_BLOCK_PATTERN.finditer(content) if match.group(1).strip())
    final_content = THINK_BLOCK_PATTERN.sub("", content).strip()
    normalized_think = (think_content or embedded_think).strip()
    if enable_think_output and normalized_think:
        if embedded_think:
            return content.strip(), normalized_think
        return f"<think>\n{normalized_think}\n</think>\n{final_content}".strip(), normalized_think
    return final_content, normalized_think


def message_text(value: Any) -> str:
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
    return ""


def first_text(*values: Any) -> str:
    for value in values:
        text = message_text(value)
        if text.strip():
            return text.strip()
    return ""


def normalize_tool_choice(tool_choice: Any) -> Any:
    if tool_choice is None:
        return None
    if isinstance(tool_choice, str):
        normalized = tool_choice.strip().lower()
        return normalized if normalized in {"auto", "none"} else None
    if isinstance(tool_choice, dict):
        function = tool_choice.get("function") if isinstance(tool_choice.get("function"), dict) else {}
        name = str(function.get("name") or "").strip()
        if name:
            return {"type": "function", "function": {"name": name}}
    return None


def normalize_tool_call_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def parse_tool_calls(message: Any) -> list[dict[str, Any]]:
    if not isinstance(message, dict):
      return []
    raw_calls = message.get("tool_calls") or message.get("skill_calls") or message.get("calls") or []
    if not isinstance(raw_calls, list):
        return []
    parsed: list[dict[str, Any]] = []
    for item in raw_calls:
        if not isinstance(item, dict):
            continue
        function = item.get("function") if isinstance(item.get("function"), dict) else {}
        parsed.append(
            {
                "id": item.get("id"),
                "type": item.get("type") or "function",
                "index": item.get("index"),
                "function": {
                    "name": function.get("name") or item.get("tool_name") or item.get("skill_key") or "",
                    "arguments": function.get("arguments")
                    if isinstance(function.get("arguments"), str)
                    else json.dumps(normalize_tool_call_arguments(item.get("arguments")), ensure_ascii=False),
                },
            }
        )
    return parsed


def collapse_developer_role_to_system(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把所有 ``role == "developer"`` 的消息合并到最近的 ``role == "system"`` 后面。

    行为约定：
    - 业务层在组装 messages 时，会按 ``(system, developer)`` 顺序、可能穿插
      skill 上下文，调用此函数后再下发，可保证下游不认 developer 的 provider
      不会因为 role 不识别返回 400。
    - 如果整段 messages 里没有 ``system``，第一段 ``developer`` 会被提升为
      ``system``；后续 developer 继续追加在该 system 末尾。
    - 多段 developer 之间也按出现顺序串接，每段都加 ``## Developer Notes``
      分隔标题，方便下游模型在 system 长上下文里区分来源。
    - 非字符串 content（list of parts）按字符串化处理拼接，避免破坏 siliconflow
      那一类依赖 content 形状的特殊处理。
    """
    collapsed: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            collapsed.append(message)
            continue
        role = str(message.get("role") or "").strip().lower()
        content = message.get("content", "")
        if role != "developer":
            collapsed.append(message)
            continue
        text = _message_content_to_text(content)
        if not text.strip():
            # 空的 developer 直接丢弃，不污染 system
            continue
        if collapsed and str(collapsed[-1].get("role") or "").strip().lower() == "system":
            existing = collapsed[-1].get("content", "")
            collapsed[-1] = {
                **collapsed[-1],
                "content": _join_text_content(existing, text, DEVELOPER_MERGE_SEPARATOR),
            }
        else:
            collapsed.append({"role": "system", "content": text})
    return collapsed


def _message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def _join_text_content(existing: Any, addition: str, separator: str) -> Any:
    """拼接两段 content，保持原形状。

    - existing 为字符串 → 直接字符串拼接
    - existing 为 list of parts → 在末尾追加一个 text part（避免破坏 siliconflow
      那类需要 content 是 list 的 provider）
    - 其它情况 → 退化为字符串
    """
    if isinstance(existing, str):
        if not existing:
            return addition
        return f"{existing}{separator}{addition}"
    if isinstance(existing, list):
        text_part: dict[str, Any] = {"type": "text", "text": separator[2:] + addition}
        if existing and isinstance(existing[-1], dict) and existing[-1].get("type") == "text":
            existing = [*existing]
            existing[-1] = {**existing[-1], "text": f"{existing[-1].get('text', '')}{separator}{addition}"}
            return existing
        return [*existing, text_part]
    if existing is None or existing == "":
        return addition
    return f"{existing}{separator}{addition}"


def normalize_chat_messages(
    messages: list[dict[str, Any]],
    *,
    collapse_developer: bool = True,
) -> list[dict[str, Any]]:
    """基础 messages 归一化。

    ``collapse_developer=True`` 时，会把所有 ``role == "developer"`` 消息
    合并到最近的 system 后面。绝大多数 provider（除 OpenAI 原生 o 系列外）
    都不支持 developer role，业务侧不应该传 False；只有确认走 OpenAI o 系列的
    调用方才传 False 保留分层语义。
    """
    working: list[dict[str, Any]] = (
        collapse_developer_role_to_system(messages) if collapse_developer else list(messages)
    )
    normalized: list[dict[str, Any]] = []
    for message in working:
        if not isinstance(message, dict):
            # 保留异常输入的形状，不主动补默认 role（避免静默丢字段）
            normalized.append(message)
            continue
        role = str(message.get("role") or "user").strip() or "user"
        normalized.append(
            {
                "role": role,
                "content": message.get("content", ""),
            }
        )
    return normalized or [{"role": "user", "content": ""}]


def normalize_provider_chat_messages(
    provider_name: str,
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """按 provider 名字做归一化。

    - 非 siliconflow：保持 content 原样
    - siliconflow：把 ``input_audio`` 形态转换成 ``audio_url``（旧版 SDK 约定）
    - role 归一化与 ``developer`` → ``system`` 降级在 ``normalize_chat_messages``
      里完成；只有 provider 原生支持 ``developer`` 的才传 ``collapse_developer=False``
    """
    provider_key = provider_name.strip().lower()
    collapse_developer = provider_key not in DEVELOPER_AWARE_PROVIDERS
    normalized = normalize_chat_messages(messages, collapse_developer=collapse_developer)
    if provider_key != "siliconflow":
        return normalized
    return [
        {
            **message,
            "content": siliconflow_content_parts(message.get("content", "")),
        }
        for message in normalized
    ]


def siliconflow_content_parts(content: Any) -> Any:
    if not isinstance(content, list):
        return content
    return [siliconflow_content_part(part) if isinstance(part, dict) else part for part in content]


def siliconflow_content_part(part: dict[str, Any]) -> dict[str, Any]:
    if part.get("type") != "input_audio":
        return part
    input_audio = part.get("input_audio") if isinstance(part.get("input_audio"), dict) else {}
    data = str(input_audio.get("data") or "")
    audio_format = str(input_audio.get("format") or "mpeg").strip().lower() or "mpeg"
    return {
        "type": "audio_url",
        "audio_url": {
            "url": audio_data_url(data, audio_format),
        },
    }


def audio_data_url(data: str, audio_format: str) -> str:
    if data.startswith("data:"):
        return data
    mime_subtype = {"mp3": "mpeg", "m4a": "x-m4a"}.get(audio_format, audio_format)
    return f"data:audio/{mime_subtype};base64,{data}"


def provider_extra_body(extra_body: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in extra_body.items() if key != "enable_think_output"}


def stream_openai_compatible_request(
    *,
    provider_name: str,
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> Iterator[str]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace")
                if not line.strip():
                    yield "\n"
                    continue
                yield line if line.endswith("\n") else f"{line}\n"
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{provider_name} request failed: HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{provider_name} request failed: {exc.reason}") from exc
