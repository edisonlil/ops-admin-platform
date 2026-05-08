from __future__ import annotations

import contextvars

from system.domain.tenancy import TenantScope, default_tenant_scope


tenant_scope_var: contextvars.ContextVar[TenantScope | None] = contextvars.ContextVar(
    "tenant_scope",
    default=None,
)


def current_tenant_scope() -> TenantScope:
    return tenant_scope_var.get() or default_tenant_scope()


def set_tenant_scope(scope: TenantScope) -> contextvars.Token[TenantScope | None]:
    return tenant_scope_var.set(scope)


def reset_tenant_scope(token: contextvars.Token[TenantScope | None]) -> None:
    tenant_scope_var.reset(token)


def clear_tenant_scope() -> contextvars.Token[TenantScope | None]:
    return tenant_scope_var.set(None)
