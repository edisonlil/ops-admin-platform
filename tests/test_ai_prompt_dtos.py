from __future__ import annotations

from ai_applications.interfaces.http.dtos import AIApplicationRequest
from ai_capabilities.interfaces.http.dtos import AICapabilityRequest


def test_ai_application_system_prompt_has_no_dto_length_limit() -> None:
    payload = AIApplicationRequest(
        app_key="long-system-prompt",
        name="长系统提示词应用",
        system_prompt="指令" * 10001,
    )

    assert len(payload.system_prompt) > 20000


def test_ai_capability_system_prompt_has_no_dto_length_limit() -> None:
    payload = AICapabilityRequest(
        capability_key="long.system.prompt",
        name="长系统提示词能力",
        system_prompt="指令" * 10001,
    )

    assert len(payload.system_prompt) > 20000
