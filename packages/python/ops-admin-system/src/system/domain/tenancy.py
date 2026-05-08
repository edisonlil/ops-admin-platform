from __future__ import annotations

from dataclasses import dataclass


DEFAULT_TENANT_KEY = "default"


@dataclass(frozen=True)
class TenantScope:
    tenant_id: int
    tenant_key: str
    tenant_name: str
    is_platform_admin: bool = False
    source: str = "user"
    principal_id: int | None = None


def default_tenant_scope() -> TenantScope:
    return TenantScope(
        tenant_id=1,
        tenant_key=DEFAULT_TENANT_KEY,
        tenant_name="Default Tenant",
        is_platform_admin=True,
        source="system",
    )
