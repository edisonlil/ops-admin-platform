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
        return LLMResponse(content=content, elapsed_seconds=elapsed_seconds, usage=usage, think_content=think_content)

    def generate(self, prompt: str, *, enable_think_output: bool | None = None) -> str:
        return self.generate_response(prompt, enable_think_output=enable_think_output).content

    def stream_chat_completions(
        self,
        messages: list[dict[str, Any]],
        *,
        extra_body: dict[str, Any] | None = None,
        enable_think_output: bool | None = None,
    ) -> Iterator[str]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": normalize_chat_messages(messages),
            "temperature": self.temperature,
            "stream": True,
        }
        merged_extra_body = provider_extra_body(self.extra_body)
        merged_extra_body.update(provider_extra_body(extra_body or {}))
        payload.update(merged_extra_body)
        yield from stream_openai_compatible_request(
            provider_name=self.provider_name,
            api_key=self.api_key,
            base_url=self.base_url,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )


THINK_BLOCK_PATTERN = re.compile(r"<think\b[^>]*>(.*?)</think>", flags=re.IGNORECASE | re.DOTALL)


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


def normalize_chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role") or "user").strip() or "user"
        normalized.append(
            {
                "role": role,
                "content": message.get("content", ""),
            }
        )
    return normalized or [{"role": "user", "content": ""}]


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
