# ops-admin-platform Project Rules

## Architecture
- The Python server uses DDD-style bounded contexts.
- Current bounded contexts:
  - `system`: request context, response envelope, events, health, and shared infrastructure.
  - `identity_access`: users, login, API keys, roles, permissions, menus, and tenants.
  - `appearance`: platform and tenant appearance configuration.
  - `llm_runtime`: LLM provider configuration and runtime configuration.
- Each bounded context should keep this shape when it grows:
  - `domain`: entities, value objects, domain services, domain events, domain exceptions.
  - `application`: use cases, transaction orchestration, ports, event publication.
  - `infrastructure`: database, external service, file, queue, and legacy adapters.
  - `interfaces/http`: FastAPI routers, DTOs, and HTTP response mapping.
- Dependency direction is inward: `interfaces` and `infrastructure` may depend on `application`; `application` may depend on `domain`; `domain` must not depend on FastAPI, database clients, storage adapters, or other frameworks.
- Cross-context collaboration should use application ports or domain events. Do not import another context's `infrastructure` package directly.
- Each bounded context owns its persistence resources under `infrastructure/persistence`: `ddl.sqlite.sql`, `ddl.postgres.sql`, and `seed.sql`.
- `api` is only an entrypoint/composition compatibility layer. New business capability must be implemented inside a bounded context and exposed through that context's `interfaces/http` router.
- Shared backend framework and reusable capability packages live under `packages/python/framework/`.
- Framework packages are not bounded contexts. They may provide pure runtime engines, shared contracts, value objects, helpers, and ports that multiple bounded contexts reuse.
- Framework packages must not own business tables, HTTP routers, menu/permission seed data, tenant policy, RBAC rules, or product concepts such as AI applications and AI capabilities.
- Framework packages must not import bounded context `infrastructure` packages. When they need external execution, storage, or model calls, define ports/interfaces and let bounded contexts or composition layers provide adapters.
- AI runtime shared primitives should live in `packages/python/framework/ops-admin-ai-runtime-core/`. This package is the common runtime core for `ai_applications`, `ai_capabilities`, and future workflow or agent runtimes; it must not depend on `llm_runtime` directly.
- Business contexts that need productized AI capabilities must depend only on `packages/python/framework/ops-admin-ai-service-api/` and call the `AIService` contract (`aiService.execute("capability.key", variables)`). They must not import `ai_capabilities` directly. `ai_capabilities` owns the implementation: resolve current-tenant same-key overrides first, fall back to platform-seeded capabilities, then execute using the current tenant's model route. Projects that do not include `ai_capabilities` must still start; the default AI service implementation should report the capability as unavailable rather than creating import-time failures.

## API Contract
- All business HTTP responses must use the unified envelope:
```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "req_xxx",
  "timestamp": "2026-05-05T12:00:00+08:00"
}
```
- List endpoints place rows and pagination under `data.items` and `data.pagination`.
- Errors must use `success=false`, a stable `code`, a human-readable `message`, and optional `errors`.
- Frontend request utilities unwrap the envelope. Page components should consume business data only.

## Backend Rules
- FastAPI routers should only receive input, call application services, and return the response envelope.
- Business rules belong in `domain` or `application`, not in routers.
- SQL, schema initialization, seed data, and external adapters belong in `infrastructure`.
- Business tables must follow `docs/backend-table-conventions.md`: `id`, `tenant_id`, `lock_version`, `deleted`, `create_time`, `creator`, `creator_id`, `update_time`, `editor`, and `editor_id` are required base fields.
- Business runtime must never initialize, migrate, seed, backfill, or repair database schema/data implicitly.
- Runtime code may check that required tables/data already exist and fail with a clear operational error if they do not.
- After adding or changing backend storage, seed data, permissions, menus, tenant menu defaults, or module entry points, explicitly run the relevant initialization script once in the development database and verify the menu/permission chain. This remains a development/operations step, not runtime behavior. See `docs/backend-development-workflow.md`.
- Every bounded context must maintain its own `README.md` at the context root.
- Do not add new direct imports from `domain` packages to FastAPI, `sqlite3`, `psycopg`, or storage implementations.

## Frontend Rules
- Use the shared request client under `web/admin/src/utils/http/alova`.
- API wrapper functions should return unwrapped business data.
- Components should not know the envelope format; only the request layer should.
- Keep backend module capabilities aligned with default frontend module pages where practical.
- List pages, table pages, and data-view pages must be modeled through `web/admin/src/page-runtime`.
- New list/data-view shapes such as tabbed lists, split master-detail views, kanban, tree, calendar, timeline, gallery, or map views should be added as Page Runtime view types/adapters instead of hand-building equivalent page structure inside business pages.
- Business pages may provide schemas, rows, loading state, actions, and item/detail slots, but Page Runtime owns header, filters, toolbar, collection boundaries, table tools, pagination placement, density, spacing, and visual consistency.
- Table pagination should be rendered by Page Runtime outside the data table; do not enable `n-data-table` internal pagination to simulate page-level pagination.

## Testing
- Run backend tests after server changes.
- Run the frontend build after changing `web/admin`.
- Architecture tests must prevent framework/database dependencies from entering domain packages and prevent cross-context infrastructure imports.
