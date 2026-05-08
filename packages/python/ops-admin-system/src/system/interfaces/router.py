from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from system.application import health_service
from system.interfaces.http import ok


router = APIRouter()


@router.get("/health")
def health() -> dict[str, Any]:
    return ok(health_service.health_payload())
