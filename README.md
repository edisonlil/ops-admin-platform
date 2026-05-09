# ops-admin-platform

`ops-admin-platform` is a modular operations admin platform starter. It provides a FastAPI backend and a Vue 3 / Naive UI admin frontend with identity, tenancy, RBAC, API key management, appearance configuration, and LLM runtime configuration.

This repository is the platform baseline. Business modules should be added as bounded contexts instead of being implemented in the `api` entrypoint package.

## Current Modules

| Module | Responsibility |
| --- | --- |
| `system` | Request context, unified response envelope, health checks, events, and shared persistence infrastructure. |
| `identity_access` | Users, login, tenants, roles, permissions, menus, and API keys. |
| `appearance` | Platform and tenant appearance themes and branding. |
| `llm_runtime` | LLM providers, models, tasks, routing policies, logs, and OpenAI-compatible debug endpoints. |
| `web/admin` | Vue admin application using the shared alova request client. |

## Backend Setup

Install dependencies:

```powershell
pip install -r requirements.txt
```

Initialize required storage explicitly:

```powershell
python scripts/init_identity_access.py
python scripts/init_appearance.py
python scripts/init_llm_runtime.py
```

Run the API:

```powershell
uvicorn api.main:app --reload
```

Default development login:

- Tenant: `platform`
- Username: `admin`
- Password: `edc3000`

Runtime code must not initialize, migrate, seed, backfill, or repair schema implicitly. Initialization is an operations task run through the scripts above.

## One-Click Development Startup

Use the Windows starter to configure and run both services:

```powershell
.\start-dev.bat
```

The script asks for backend/frontend ports and database settings, writes local-only configuration to `config/database.local.json` and `web/admin/.env.development.local`, installs missing backend/frontend dependencies, builds the frontend if `dist` is missing, and then starts FastAPI plus Vite. Logs and pid files are written under `.tmp`.

For unattended runs, pass parameters through the batch file:

```powershell
.\start-dev.bat -BackendPort 8000 -FrontendPort 8001 -NonInteractive
```

Add `-InitializeStorage` when you want the script to run the explicit storage initialization tasks before startup.

## Frontend Setup

```powershell
cd web/admin
pnpm install
pnpm dev
```

Build:

```powershell
pnpm build
```

The future package target for the reusable admin frontend is `@edisonlil/ops-admin-web`.

## Configuration

The backend reads database configuration from:

1. `FG_AGENT_DATABASE_CONFIG`
2. `config/database.local.json`
3. `config/database.json`

If no Postgres URL is configured, SQLite is used. The default local SQLite file is `ops_admin.db`.

## Development Direction

Phase 1 keeps this as a clean runnable platform baseline. Later phases split the backend modules into Python packages and extract reusable frontend modules under `@edisonlil/ops-admin-web`.

See `tasks.md` for the implementation backlog.
