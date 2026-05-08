# Appearance Context

## Responsibilities

The `appearance` bounded context owns persisted UI appearance themes and platform branding for the admin console. It manages reusable theme assets, separates draft edits from published runtime payloads, resolves the effective theme for each tenant, and stores the platform name/logo shown in the shell.

## Boundaries

- `domain` defines theme payloads, draft payloads, theme entities, and platform branding values.
- `application` exposes use cases for theme library management, draft saving, publishing, tenant assignment, effective theme resolution, and platform branding updates.
- `infrastructure/persistence` owns SQL DDL and repository adapters for `appearance_*` tables.
- `interfaces/http` exposes FastAPI routes under `/api/appearance`.

The context depends on `system.application.database` for database connections and on `identity_access.interfaces.http.dependencies` only at the HTTP boundary for authentication/authorization.

## HTTP APIs

- `GET /api/appearance/effective-theme`: authenticated users read the effective runtime theme. Resolution order is tenant assignment, platform default, then frontend builtin.
- `GET /api/appearance/platform-branding`: authenticated users read the platform name and optional logo URL.
- `PUT /api/appearance/platform-branding`: platform admins update the platform name and optional logo URL.
- `GET /api/appearance/themes`: platform admins list theme cards.
- `POST /api/appearance/themes`: platform admins create a theme draft.
- `GET /api/appearance/themes/{theme_id}`: platform admins load a theme, including its draft payload.
- `PUT /api/appearance/themes/{theme_id}`: platform admins save a draft. This does not change tenant runtime appearance.
- `POST /api/appearance/themes/{theme_id}/publish`: platform admins publish the draft into the runtime payload and create a revision.
- `POST /api/appearance/themes/{theme_id}/disable`: platform admins stop a theme from future assignment.
- `POST /api/appearance/themes/{theme_id}/platform-default`: platform admins set a published theme as the platform default fallback.
- `GET /api/appearance/tenants/{tenant_id}/theme`: tenant admins or platform admins read a tenant's assigned theme.
- `PUT /api/appearance/tenants/{tenant_id}/theme`: tenant admins or platform admins assign or clear a tenant theme.
- `PUT /api/appearance/tenant-theme`: compatibility endpoint for the first tenant-direct implementation.

## Persistence

Owned tables:

- `appearance_themes`
- `appearance_theme_assignments`
- `appearance_theme_revisions`
- `appearance_platform_branding`

DDL lives in `infrastructure/persistence/ddl.sqlite.sql` and `ddl.postgres.sql`. Runtime code checks that the tables exist but never creates or migrates them. Run `python scripts/init_appearance.py` explicitly to initialize storage.

## Testing

Run targeted backend tests after changes:

```bash
pytest tests/test_api.py tests/test_architecture.py
```
