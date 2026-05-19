from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from identity_access.interfaces.http import dependencies as auth
from personalization.application import services
from personalization.interfaces.http.dtos import TableColumnPreferenceRequest
from system.interfaces.http import ok


router = APIRouter(prefix="/personalization")


@router.get("/table-columns/{view_key:path}")
def table_columns(
    view_key: str,
    current_user: dict[str, Any] = Depends(auth.require_user),
) -> dict[str, Any]:
    return ok(services.get_table_columns(view_key, current_user))


@router.put("/table-columns/{view_key:path}")
def save_table_columns(
    view_key: str,
    payload: TableColumnPreferenceRequest,
    current_user: dict[str, Any] = Depends(auth.require_user),
) -> dict[str, Any]:
    return ok(services.save_table_columns(view_key, payload.model_dump(by_alias=False), current_user))


@router.delete("/table-columns/{view_key:path}")
def reset_table_columns(
    view_key: str,
    current_user: dict[str, Any] = Depends(auth.require_user),
) -> dict[str, Any]:
    return ok(services.reset_table_columns(view_key, current_user))
