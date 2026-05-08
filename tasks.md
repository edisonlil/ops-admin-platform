# ops-admin-platform Tasks

## Phase 1 - Clean Starter Baseline
- [x] Copy source from fg-agent into ops-admin-platform.
- [x] Remove function_point backend context and database artifacts.
- [x] Remove function point frontend pages, APIs, routes, and menu entries.
- [x] Rename project metadata to ops-admin-platform.
- [x] Update README and AGENTS.md for platform usage.
- [x] Run backend tests.
- [x] Run frontend build.
- [x] Push clean baseline to GitHub.

## Phase 2 - Python Package Split
- [x] Create monorepo package layout under packages/python.
- [x] Extract ops-admin-system.
- [x] Extract ops-admin-identity-access.
- [x] Extract ops-admin-appearance.
- [x] Extract ops-admin-llm-runtime.
- [x] Define router/init-task entrypoints for each package.
- [x] Update starter to install and compose packages.
- [x] Add package-level and starter integration tests.

## Phase 3 - Frontend Modular Package
- [x] Create packages/web/ops-admin-web.
- [x] Extract shared layout, request client, auth flow, menu, and stores.
- [x] Add module registration API for identity_access.
- [x] Add module registration API for appearance.
- [x] Add module registration API for llm_runtime.
- [x] Update starter to consume @edisonlil/ops-admin-web.
- [x] Verify starter build with LLM enabled and disabled.

## Phase 4 - Skill Automation
- [ ] Create skills/ops-admin-platform.
- [ ] Add create_project workflow.
- [ ] Add enable/disable module workflow.
- [ ] Add create bounded context workflow.
- [ ] Add create admin feature workflow.
- [ ] Validate skill by generating a sample project.

## Rules
- Do not reintroduce function_point into platform packages.
- Runtime code must not initialize, migrate, seed, backfill, or repair schema implicitly.
- Every backend module keeps DDD boundaries and its own persistence resources.
- Frontend components consume unwrapped business data only.
- Optional modules must be installable/registerable independently.
