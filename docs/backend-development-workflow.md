# Backend Development Workflow

This project keeps schema creation, seed data, menu setup, and role/menu repair out of business runtime. Runtime code may check that storage is ready, but it must not initialize, migrate, seed, backfill, or repair data implicitly.

That rule does not mean developers can skip initialization. After adding or changing backend storage, seed data, permissions, menus, tenant menu defaults, or module entry points, run the relevant explicit initialization script once in the development database before declaring the feature ready.

## Required Post-Development Checks

1. Update the bounded context persistence resources:
   - `infrastructure/persistence/ddl.sqlite.sql`
   - `infrastructure/persistence/ddl.postgres.sql`
   - `infrastructure/persistence/seed.sql`
   - the context bootstrap or init task entry point

2. If the feature exposes an admin page, update the full menu chain:
   - permission codes
   - `menus.menu_scope`
   - page/action menu rows
   - role menu or role permission defaults
   - tenant menu default enablement when the menu belongs to tenant scope
   - frontend module menu keys under `@edisonlil/ops-admin-web`
   - starter registration under `web/admin/src/modules.ts`

3. Run the explicit initialization script for every changed storage context, for example:

```powershell
python scripts/init_identity_access.py
python scripts/init_ai_assets.py
```

Do this manually as part of development validation. Do not move this work into request handlers, repositories, routers, or application services.

4. Verify the initialized database, not only the source SQL:
   - required tables exist
   - permission rows exist
   - menu rows have the expected `menu_scope`
   - tenant-scoped menus are enabled in `tenant_menu_overrides`
   - the expected role has the relevant menu and permission bindings

5. Verify through the same user flow the frontend will use:
   - login as the expected tenant or platform user
   - call `/api/admin_info`
   - confirm the returned `menus` tree includes the new menu
   - confirm the sidebar renders the menu after logout/login or route reset

6. Run tests after backend changes:

```powershell
python -m pytest tests/test_package_entrypoints.py tests/test_architecture.py
```

Add or run module-specific tests when the feature owns new behavior.

## Menu Visibility Pitfall

Menu visibility is a chain, not a single permission checkbox. A menu can be present in the RBAC configuration UI and still not appear in the sidebar if any part of this chain is missing:

- the menu has the wrong `menu_scope`
- the current login scope is different from the menu scope
- the role lacks a role-menu binding
- the tenant has no enabled `tenant_menu_overrides` row for a tenant menu
- the frontend module registry has not registered the menu key
- the browser still has old route or user state cached

When a newly developed page does not appear, inspect this chain before assuming the page component or router is broken.

