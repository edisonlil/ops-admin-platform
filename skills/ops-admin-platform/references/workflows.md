# Ops Admin Platform Workflows

## create_project

Use `scripts/create_project.py` for a deterministic starter skeleton when the user wants a new project.

Required decisions:

- Project name.
- Target directory.
- Enabled modules: default to `identity_access,appearance,llm_runtime`.

After generation:

- Check that backend packages live under `packages/python`.
- Check that frontend module registration lives under `packages/web/ops-admin-web` and `web/admin/src/modules.ts`.
- Run the generated test command if the target includes tests.

## enable_module

Backend steps:

- Add the package to starter installation metadata, usually `requirements.txt` for Python packages.
- Ensure the package exposes `ops_admin.routers` and `ops_admin.init_tasks` entry points.
- Ensure runtime compose code discovers routers through `api.module_registry`.
- Add or update architecture tests for dependencies, persistence resources, and entry points.

Frontend steps:

- Add a module registration function to `packages/web/ops-admin-web/src/module-registry.ts`.
- Register the module from `web/admin/src/modules.ts`.
- Ensure backend menu keys map to the module's `menuKeys`.
- Run `npm run build`.

## disable_module

Backend steps:

- Remove the package from starter installation metadata.
- Do not leave direct imports to that module from `api`, other bounded contexts, or init scripts.
- Keep database initialization explicit; never compensate by runtime seeding.

Frontend steps:

- Remove or guard the module registration in `web/admin/src/modules.ts`.
- Keep unknown custom menu keys allowed, but filter known disabled platform module keys.
- Run `npm run build` with the module disabled when a flag exists.

## create_bounded_context

Package shape:

```text
packages/python/ops-admin-<context>/
  pyproject.toml
  src/<context>/
    README.md
    entrypoints.py
    domain/
    application/
    infrastructure/persistence/
      ddl.sqlite.sql
      ddl.postgres.sql
      seed.sql
    interfaces/http/
```

Rules:

- Domain code must not import FastAPI, database clients, storage adapters, or other frameworks.
- HTTP routers receive input, call application services, and return the unified envelope.
- Cross-context collaboration should use application ports or domain events.
- Add package metadata with `ops_admin.routers` and `ops_admin.init_tasks`.
- Add architecture tests for the new context.

## create_admin_feature

Backend path:

- Put business behavior inside the owning bounded context.
- Add DTOs and router functions under `interfaces/http`.
- Return list payloads as `data.items` and `data.pagination`.
- Add schema and seed changes only under the context's `infrastructure/persistence`.
- Add tests for the application behavior and HTTP envelope.

Frontend path:

- Add API wrappers that use `web/admin/src/utils/http/alova`.
- Return unwrapped business data from wrappers.
- Keep Vue page components unaware of the envelope.
- Add or update menu registration when the feature belongs to an optional module.
- Run `npm run build`.
