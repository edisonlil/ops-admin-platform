from __future__ import annotations

from typing import Any, Mapping

from ai_service_api import AIExecuteOptions, AIExecuteResult

from ai_capabilities.application import services


class AICapabilityService:
    def execute(
        self,
        capability_key: str,
        variables: Mapping[str, Any],
        *,
        options: AIExecuteOptions | None = None,
    ) -> AIExecuteResult:
        payload: dict[str, Any] = {"variables": dict(variables)}
        if options:
            if options.model:
                payload["model"] = options.model
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.response_format is not None:
                payload["response_format"] = options.response_format
            if options.extra_body is not None:
                payload["extra_body"] = options.extra_body
            if options.enable_think_output is not None:
                payload["enable_think_output"] = options.enable_think_output
        result = services.execute_ai_capability(capability_key, payload)
        return AIExecuteResult(
            answer=str(result.get("answer") or ""),
            trace_id=str(result.get("trace_id") or ""),
            usage=result.get("usage") if isinstance(result.get("usage"), dict) else {},
            trace=result.get("trace") if isinstance(result.get("trace"), dict) else {},
            raw=result,
        )
