# Ops Admin Platform Workflows

## create_project

First choose the project creation route:

- Scaffold route, recommended by default: use `scripts/create_project.py` for a deterministic application shell that consumes published platform packages.
- Clone route: use `git clone` when the user wants the complete platform source and accepts owning future source maintenance.

Required decisions:

- Route: scaffold or clone.
- Project name.
- Target directory.
- Enabled modules: default to `identity_access,appearance,llm_runtime`.
- Optional package versions for published Python packages and `@edisonlil/ops-admin-web`.

Scaffold route rules:

- Generate `requirements.txt` with `ops-admin-system` and selected `ops-admin-*` module dependencies.
- Generate `web/admin/package.json` with `@edisonlil/ops-admin-web`.
- Keep project composition local in files such as `api/module_registry.py` and `web/admin/src/modules.ts`.
- Do not generate `packages/python/ops-admin-*` or `packages/web/ops-admin-web`.

Clone route rules:

- Clone the platform repository into the target directory.
- Keep backend platform packages under `packages/python`.
- Keep the shared frontend package under `packages/web/ops-admin-web`.
- Tell the user that source-level customization also means source-level upgrade work.

After scaffold generation:

- Check that backend platform packages are listed as dependencies, not copied as source.
- Check that frontend module registration lives in `web/admin/src/modules.ts`.
- Check that `web/admin/package.json` depends on `@edisonlil/ops-admin-web`.
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
