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

## Guardrails

- Keep backend DDD boundaries: `interfaces/http`, `application`, `domain`, `infrastructure`.
- Keep each bounded context under `packages/python/<package>/src/<context>`.
- Use package entry points for routers and explicit init tasks.
- Never initialize, migrate, seed, backfill, or repair schema implicitly at runtime.
- Keep frontend envelope handling in the request layer; components consume unwrapped data.
- Register optional frontend modules through `@edisonlil/ops-admin-web`.
- Mark completed `tasks.md` items and commit after each completed phase when requested.

## Scripts

- `scripts/create_project.py`: generate a small starter project skeleton for validating the create-project workflow.

Example:

```bash
python skills/ops-admin-platform/scripts/create_project.py C:/tmp/ops-admin-sample --name ops-admin-sample --modules identity_access,appearance,llm_runtime
```
