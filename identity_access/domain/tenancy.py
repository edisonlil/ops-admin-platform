from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tenant:
    id: int
    tenant_key: str
    name: str
    status: str
    remark: str = ""
