# Project Agents Guide

This project extends [scaffold AGENTS.md](./.ops-scaffold/AGENTS.md) with project-specific rules.

## Scaffold Rules (Reference)

This project is based on [ops-admin-platform](https://github.com/edisonlil/ops-admin-platform).
See `.ops-scaffold/AGENTS.md` for the full scaffold rules including:
- DDD architecture and bounded contexts
- API contract format
- Backend development patterns
- Frontend rules (Page Runtime, alova client)

**These scaffold rules remain in effect. This document adds project-specific overrides.**

---

## Project-Specific Overrides

### 1. Business Code Isolation

Unlike pure scaffold development, this project has custom business logic.
Business code must be isolated to avoid conflicts during `ops-cli sync`.

#### Backend: Bounded Contexts

Place custom business code in dedicated bounded contexts:

```
backend/src/{your_context}/
├── domain/               # Business entities, value objects
├── application/          # Business use cases
├── infrastructure/        # DB, external adapters
└── interfaces/http/      # API routers
```

**Rules:**
- DO NOT modify scaffold bounded contexts (`system`, `identity_access`, etc.)
- DO NOT add business logic to `packages/`
- Create new bounded context for new features

#### Frontend: Business Directory

```
web/admin/src/
├── pages/               # Scaffold pages (DO NOT MODIFY)
├── page-runtime/        # Framework (DO NOT MODIFY)
└── business/            # YOUR BUSINESS CODE
    ├── modules/          # Business module pages
    │   ├── sales/
    │   ├── inventory/
    │   └── reports/
    ├── components/       # Business components
    ├── router/           # Business routes
    └── api/              # Business API clients
```

**Rules:**
- All new pages go under `business/modules/`
- DO NOT add pages to `pages/` root
- Register routes in `business/router/`
- Use `/business/` prefix to avoid conflicts

### 2. Sync with Scaffold

Run `ops-cli sync` to pull scaffold updates:

```bash
ops-cli sync              # Apply updates
ops-cli sync --check       # Preview only
```

**What sync does:**
- Clones latest scaffold to temp
- Compares with last synced version
- Applies framework changes only
- **Skips**: `business/`, `.ops-config`, `config/database.*.json`

**What sync protects:**
- All files in `business/` directory
- Your custom bounded contexts
- Environment-specific configs

### 3. Configuration

- Environment configs: `config/database.{env}.json`
- DO NOT commit secrets to git
- Use `.ops-scaffold/config/` as templates

### 4. Important Principles

1. **Scaffold is read-only** - Don't modify framework files directly
2. **Extend, don't modify** - Create new files/dirs for custom code
3. **Business isolation** - Keep custom code in `business/` or separate bounded contexts
4. **Sync-safe** - Business code survives `ops-cli sync` intact

### 5. Codex/AI Development Guidelines

When developing with Codex or other AI assistants:

1. **Context**: Start by reading `.ops-scaffold/AGENTS.md` for scaffold rules
2. **Business code**: Place in `business/` (frontend) or new bounded context (backend)
3. **Extensions**: Extend existing components, don't modify scaffold components
4. **Conflicts**: If scaffold has similar functionality, extend it rather than replace

**Example workflow:**
```
# Add a sales module
1. Create backend: backend/src/sales/
2. Create frontend: web/admin/src/business/modules/sales/
3. Register routes in business/router/
4. Add menu/permission in infrastructure/seed.sql
5. Test and deploy
```

### 6. Directory Reference

| Directory | Action |
|-----------|--------|
| `.ops-scaffold/` | Reference only (scaffold rules) |
| `ops_cli/` | Tool code (DO NOT MODIFY) |
| `packages/` | Framework (DO NOT MODIFY) |
| `backend/src/system/` | Scaffold context (extend only) |
| `backend/src/{custom}/` | OK to add new bounded contexts |
| `web/admin/src/pages/` | DO NOT MODIFY |
| `web/admin/src/business/` | OK for business code |
| `config/` | Reference templates |
| `config/database.*.json` | OK for env configs |

---

## Questions?

- Scaffold rules: `.ops-scaffold/AGENTS.md`
- Backend development: `docs/backend-development-workflow.md`
- Frontend development: Follow patterns in existing `business/` or `pages/`