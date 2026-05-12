from __future__ import annotations

from typing import Any

from system.application.health_service import health_payload


def system_health_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": "system.health.snapshot",
        "input": payload,
        "health": health_payload(),
    }
