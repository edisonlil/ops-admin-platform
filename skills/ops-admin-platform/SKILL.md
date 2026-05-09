---
name: ops-admin-platform
description: Build, customize, or extend ops-admin-platform starters. Use when creating a new project from this platform, enabling or disabling backend/frontend modules, adding a DDD bounded context, creating an admin feature across FastAPI and Vue, or validating that generated projects follow ops-admin-platform package, envelope, module-registration, and initialization rules.
---

# Ops Admin Platform

Use this skill for ops-admin-platform project automation and extensions.

## First Moves

1. Read the nearest `AGENTS.md` and `tasks.md`.
2. Identify the active workflow:
   - `create_project`
   - `enable_module` or `disable_module`
   - `create_bounded_context`
   - `create_admin_feature`
3. Read [references/workflows.md](references/workflows.md) for the selected workflow.
4. Prefer existing package patterns over inventing new structure.
5. Validate with backend tests after server changes and frontend build after `web/admin` changes.

## Project Creation Routes

When the user wants a new project, choose the route before acting:

- Scaffold route, recommended by default: run `scripts/create_project.py` to create an application shell that consumes published ops-admin-platform packages through `pip` and `@edisonlil/ops-admin-web` through npm. The scaffold must not copy `packages/python/ops-admin-*` or `packages/web/ops-admin-web` source into the generated project.
- Clone route: default to the `main` branch unless the user names another branch, then use `git clone --branch <branch> https://github.com/edisonlil/ops-admin-platform.git <target>` when the user wants to own and modify the full platform source. Do not ask for a repository URL unless the user explicitly wants a fork or mirror. After cloning, remove only the cloned target's `.git` directory so the new project cannot accidentally commit or push to the platform repository. The cloned project keeps the monorepo package layout and the user takes on future merge/upgrade work.

## Guardrails

- Keep backend DDD boundaries: `interfaces/http`, `application`, `domain`, `infrastructure`.
- In the platform repository or clone route, keep each platform bounded context under `packages/python/<package>/src/<context>`.
- In scaffold route projects, consume platform bounded contexts as package dependencies and add only local application-owned business contexts.
- Use package entry points for routers and explicit init tasks.
- Never initialize, migrate, seed, backfill, or repair schema implicitly at runtime.
- Keep frontend envelope handling in the request layer; components consume unwrapped data.
- Register optional frontend modules through `@edisonlil/ops-admin-web`.
- Mark completed `tasks.md` items and commit after each completed phase when requested.

## Scripts

- `scripts/create_project.py`: generate a scaffold-route starter that depends on published platform packages instead of embedding platform package source.

Example:

```bash
python skills/ops-admin-platform/scripts/create_project.py C:/tmp/ops-admin-sample --name ops-admin-sample --modules identity_access,appearance,llm_runtime
```
