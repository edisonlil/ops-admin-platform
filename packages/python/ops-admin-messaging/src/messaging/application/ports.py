from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RecipientProfile:
    user_id: int
    username: str
    tenant_id: int


class RecipientDirectoryPort(Protocol):
    def resolve_users(self, tenant_id: int, target: dict[str, Any]) -> list[RecipientProfile]:
        ...
