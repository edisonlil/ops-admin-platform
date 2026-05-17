from __future__ import annotations

from typing import Any, Mapping

from ai_service_api.contracts import AIExecuteOptions
from ai_service_api.contracts import AIExecuteResult
from ai_service_api.contracts import AIService
from ai_service_api.contracts import AIServiceUnavailable


class UnavailableAIService:
    def execute(
        self,
        capability_key: str,
        variables: Mapping[str, Any],
        *,
        options: AIExecuteOptions | None = None,
    ) -> AIExecuteResult:
        raise AIServiceUnavailable("AI service is not available")


_ai_service: AIService = UnavailableAIService()


def register_ai_service(service: AIService) -> None:
    global _ai_service
    _ai_service = service


def reset_ai_service() -> None:
    global _ai_service
    _ai_service = UnavailableAIService()


def get_ai_service() -> AIService:
    return _ai_service
