# identity_access

## Responsibilities

`identity_access` owns tenant-scoped users, login, API keys, RBAC menus/roles/permissions, and platform tenant administration.

## Boundaries

- `domain`: identity and tenancy domain concepts/events.
- `application`: authentication, API key, RBAC, tenant orchestration.
- `infrastructure`: password/API-key security and persistence adapters.
- `interfaces/http`: FastAPI routers, request DTOs, and response mapping.

Other contexts should consume identity data through application services or request principal context, not by importing this context's infrastructure package.

## HTTP APIs

- `/api/auth/token`, `/api/login`, `/api/auth/me`, `/api/admin_info`, `/api/auth/tenant/switch`
- `/api/api-keys` for platform-level API key management
- `/api/tenant/users`, `/api/tenant/roles`, `/api/tenant/api-keys` for current-tenant self-service
- `/api/rbac/users`, `/api/rbac/roles`, `/api/rbac/permissions`, `/api/rbac/menus`
- `/api/tenants`, `/api/tenants/{tenant_id}/users`, `/api/tenants/{tenant_id}/api-keys`

All business responses use the system response envelope.

## Persistence

Owned tables include `users`, `api_keys`, `roles`, `permissions`, `menus`, role mapping tables, `tenants`, and `tenant_memberships`.

`users.username` is unique only inside a tenant. The durable identity key is `(tenant_id, username)`, so different tenants may each have an `admin` account. Login callers must provide a tenant key.

`platform` is a reserved system tenant used only for platform administrators. It is stored in `tenants` so platform users have an explicit database owner, but it is hidden from business tenant management and cannot be created or managed through tenant APIs. Business tenants start from the `default` tenant and get their own users, memberships, API keys, and tenant menu overrides.

DDL and seed data live in `infrastructure/persistence`.

All identity tables follow the repository-wide base field convention in `docs/backend-table-conventions.md`, including `id` primary keys on relation tables plus unique business keys such as `(tenant_id, user_id, role_id)`.

Initialization is an explicit operations step, not a runtime behavior. Run it manually when provisioning or migrating an environment:

```bash
python scripts/init_identity_access.py
```

Business request paths only verify that identity storage is already initialized and return an operational error if it is not.

## Tenancy

The default mode is shared database row isolation. Login users and API keys resolve a `TenantScope`; platform admins may switch into a business tenant context through `/api/auth/tenant/switch`.

## Permission Model

Menus only control navigation visibility. HTTP routes must enforce the actual authorization and data scope.

- Platform administration routes use `/api/rbac/*`, `/api/tenants/*`, and `/api/api-keys`; they require platform-admin context or platform permissions.
- Current-tenant routes use `/api/tenant/*`; they require tenant permission codes such as `tenant:user:manage` or `tenant:api_key:manage` and must derive `tenant_id` from the authenticated tenant context.
- Shared Vue pages may be reused by platform and tenant menus, but their API wrapper must branch by user context and call the matching platform or current-tenant endpoint. Do not make tenant menu pages call `/api/rbac/*`, `/api/tenants/*`, or `/api/api-keys`.
- Permission codes are scope-specific. Do not reuse a platform permission code for a tenant menu unless the backend route intentionally supports tenant context and enforces tenant row isolation.

## Testing

Run backend API and architecture tests after changes:

```bash
python -m pytest tests/test_api.py tests/test_architecture.py
```
