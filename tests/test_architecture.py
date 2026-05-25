from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGES_ROOT = ROOT / "packages" / "python"
BOUNDED_CONTEXTS = {
    "appearance": PYTHON_PACKAGES_ROOT / "ops-admin-appearance" / "src" / "appearance",
    "basic_data": PYTHON_PACKAGES_ROOT / "ops-admin-basic-data" / "src" / "basic_data",
    "metadata_support": PYTHON_PACKAGES_ROOT / "ops-admin-metadata-support" / "src" / "metadata_support",
    "personalization": PYTHON_PACKAGES_ROOT / "ops-admin-personalization" / "src" / "personalization",
    "page_designer": PYTHON_PACKAGES_ROOT / "ops-admin-page-designer" / "src" / "page_designer",
    "cron": PYTHON_PACKAGES_ROOT / "ops-admin-cron" / "src" / "cron",
    "file_management": PYTHON_PACKAGES_ROOT / "ops-admin-file-management" / "src" / "file_management",
    "datasets": PYTHON_PACKAGES_ROOT / "ops-admin-datasets" / "src" / "datasets",
    "ai_assets": PYTHON_PACKAGES_ROOT / "ops-admin-ai-assets" / "src" / "ai_assets",
    "ai_applications": PYTHON_PACKAGES_ROOT / "ops-admin-ai-applications" / "src" / "ai_applications",
    "ai_capabilities": PYTHON_PACKAGES_ROOT / "ops-admin-ai-capabilities" / "src" / "ai_capabilities",
    "audit_logging": PYTHON_PACKAGES_ROOT / "ops-admin-audit-logging" / "src" / "audit_logging",
    "identity_access": PYTHON_PACKAGES_ROOT / "ops-admin-identity-access" / "src" / "identity_access",
    "organization": PYTHON_PACKAGES_ROOT / "ops-admin-organization" / "src" / "organization",
    "authorization": PYTHON_PACKAGES_ROOT / "ops-admin-authorization" / "src" / "authorization",
    "llm_runtime": PYTHON_PACKAGES_ROOT / "ops-admin-llm-runtime" / "src" / "llm_runtime",
    "messaging": PYTHON_PACKAGES_ROOT / "ops-admin-messaging" / "src" / "messaging",
    "system": PYTHON_PACKAGES_ROOT / "ops-admin-system" / "src" / "system",
}
APPLICATION_INFRASTRUCTURE_IMPORT_MIGRATION_ALLOWLIST = {
    # Temporary migration allowlist: these business contexts still predate the
    # application.ports repository boundary and are intentionally deferred.
    "identity_access",
    "system",
}
PACKAGE_DIRS = {
    "ops-admin-appearance": PYTHON_PACKAGES_ROOT / "ops-admin-appearance",
    "ops-admin-basic-data": PYTHON_PACKAGES_ROOT / "ops-admin-basic-data",
    "ops-admin-metadata-support": PYTHON_PACKAGES_ROOT / "ops-admin-metadata-support",
    "ops-admin-personalization": PYTHON_PACKAGES_ROOT / "ops-admin-personalization",
    "ops-admin-page-designer": PYTHON_PACKAGES_ROOT / "ops-admin-page-designer",
    "ops-admin-cron": PYTHON_PACKAGES_ROOT / "ops-admin-cron",
    "ops-admin-file-management": PYTHON_PACKAGES_ROOT / "ops-admin-file-management",
    "ops-admin-datasets": PYTHON_PACKAGES_ROOT / "ops-admin-datasets",
    "ops-admin-ai-assets": PYTHON_PACKAGES_ROOT / "ops-admin-ai-assets",
    "ops-admin-ai-applications": PYTHON_PACKAGES_ROOT / "ops-admin-ai-applications",
    "ops-admin-ai-capabilities": PYTHON_PACKAGES_ROOT / "ops-admin-ai-capabilities",
    "ops-admin-audit-logging": PYTHON_PACKAGES_ROOT / "ops-admin-audit-logging",
    "ops-admin-identity-access": PYTHON_PACKAGES_ROOT / "ops-admin-identity-access",
    "ops-admin-organization": PYTHON_PACKAGES_ROOT / "ops-admin-organization",
    "ops-admin-authorization": PYTHON_PACKAGES_ROOT / "ops-admin-authorization",
    "ops-admin-llm-runtime": PYTHON_PACKAGES_ROOT / "ops-admin-llm-runtime",
    "ops-admin-messaging": PYTHON_PACKAGES_ROOT / "ops-admin-messaging",
    "ops-admin-system": PYTHON_PACKAGES_ROOT / "ops-admin-system",
}
FORBIDDEN_DOMAIN_IMPORTS = {
    "fastapi",
    "sqlite3",
    "psycopg",
    "storage",
}
LEGACY_TOP_LEVEL_PACKAGES = {"fp_recommender", "storage"}
REQUIRED_PERSISTENCE_FILES = {
    "ddl.sqlite.sql",
    "ddl.postgres.sql",
    "ddl.mysql.sql",
    "seed.sql",
}
BASE_TABLE_COLUMNS = {
    "id",
    "tenant_id",
    "lock_version",
    "deleted",
    "create_time",
    "creator",
    "creator_id",
    "update_time",
    "editor",
    "editor_id",
}
SYSTEM_TABLELESS_DDL_COMMENT = "-- The system context currently has no durable tables."
RELATION_UNIQUE_COLUMNS = {
    "tenant_memberships": ("tenant_id", "user_id"),
    "user_roles": ("tenant_id", "user_id", "role_id"),
    "role_permissions": ("tenant_id", "role_id", "permission_id"),
    "role_menus": ("tenant_id", "role_id", "menu_id"),
}


def python_files(path: Path) -> list[Path]:
    return [item for item in path.rglob("*.py") if "__pycache__" not in item.parts]


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".", 1)[0])
    return modules


def test_domain_packages_do_not_import_framework_or_database_adapters() -> None:
    violations: list[str] = []
    for context, context_path in BOUNDED_CONTEXTS.items():
        domain_path = context_path / "domain"
        if not domain_path.exists():
            continue
        for path in python_files(domain_path):
            forbidden = imported_modules(path) & FORBIDDEN_DOMAIN_IMPORTS
            if forbidden:
                violations.append(f"{path.relative_to(ROOT)} imports {', '.join(sorted(forbidden))}")
    assert not violations, "\n".join(violations)


def test_contexts_do_not_import_other_context_infrastructure_directly() -> None:
    violations: list[str] = []
    for context, context_path in BOUNDED_CONTEXTS.items():
        if not context_path.exists():
            continue
        for path in python_files(context_path):
            if "infrastructure" in path.relative_to(context_path).parts:
                continue
            source = path.read_text(encoding="utf-8")
            for other in set(BOUNDED_CONTEXTS) - {context}:
                forbidden = f"{other}.infrastructure"
                if forbidden in source:
                    violations.append(f"{path.relative_to(ROOT)} imports {forbidden}")
    assert not violations, "\n".join(violations)


def test_business_application_layers_do_not_import_sqlite3_except_migration_allowlist() -> None:
    violations: list[str] = []
    for context, context_path in BOUNDED_CONTEXTS.items():
        if context == "system" or context in APPLICATION_INFRASTRUCTURE_IMPORT_MIGRATION_ALLOWLIST:
            continue
        application_path = context_path / "application"
        if not application_path.exists():
            continue
        for path in python_files(application_path):
            if "sqlite3" in imported_modules(path):
                violations.append(f"{path.relative_to(ROOT)} imports sqlite3")
    assert not violations, "\n".join(violations)


def test_business_application_layers_do_not_import_own_infrastructure_except_migration_allowlist() -> None:
    violations: list[str] = []
    for context, context_path in BOUNDED_CONTEXTS.items():
        if context == "system" or context in APPLICATION_INFRASTRUCTURE_IMPORT_MIGRATION_ALLOWLIST:
            continue
        application_path = context_path / "application"
        if not application_path.exists():
            continue
        forbidden_prefixes = (f"{context}.infrastructure",)
        for path in python_files(application_path):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules.append(node.module)
                for module in modules:
                    if module.startswith(forbidden_prefixes):
                        violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert not violations, "\n".join(violations)


def test_ai_applications_does_not_couple_to_file_management_context() -> None:
    violations: list[str] = []
    context_path = BOUNDED_CONTEXTS["ai_applications"]
    forbidden_import_roots = {
        "file_management",
    }
    for path in python_files(context_path):
        imports = imported_modules(path) & forbidden_import_roots
        if imports:
            violations.append(f"{path.relative_to(ROOT)} imports {', '.join(sorted(imports))}")
        source = path.read_text(encoding="utf-8")
        if "file_objects" in source:
            violations.append(f"{path.relative_to(ROOT)} references file_objects")
    assert not violations, "\n".join(violations)


def test_legacy_top_level_packages_are_not_reintroduced() -> None:
    violations = [package for package in LEGACY_TOP_LEVEL_PACKAGES if (ROOT / package).exists()]
    assert not violations, f"legacy top-level packages still exist: {', '.join(sorted(violations))}"


def test_each_context_owns_persistence_sql_resources() -> None:
    violations: list[str] = []
    for context, context_path in BOUNDED_CONTEXTS.items():
        persistence_path = context_path / "infrastructure" / "persistence"
        for filename in REQUIRED_PERSISTENCE_FILES:
            if not (persistence_path / filename).exists():
                violations.append(f"{context} missing infrastructure/persistence/{filename}")
    assert not violations, "\n".join(violations)


def test_identity_access_does_not_depend_on_api_or_business_infrastructure() -> None:
    violations: list[str] = []
    identity_path = BOUNDED_CONTEXTS["identity_access"]
    for path in python_files(identity_path):
        source = path.read_text(encoding="utf-8")
        for forbidden in ("from api ", "import api\n", "import api.", "llm_runtime.infrastructure"):
            if forbidden in source:
                violations.append(f"{path.relative_to(ROOT)} imports {forbidden}")
    assert not violations, "\n".join(violations)


def ddl_tables(sql: str) -> dict[str, str]:
    pattern = re.compile(r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\n\);", re.IGNORECASE | re.DOTALL)
    return {match.group(1): match.group(2) for match in pattern.finditer(sql)}


def ddl_columns(body: str) -> set[str]:
    columns: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip().lstrip("\ufeff")
        if not stripped:
            continue
        name = stripped.split(None, 1)[0].strip('"`,')
        if name.upper() in {"PRIMARY", "UNIQUE", "FOREIGN", "CHECK", "CONSTRAINT"}:
            continue
        columns.add(name)
    return columns


def test_business_tables_use_standard_base_columns() -> None:
    violations: list[str] = []
    for context, context_path in BOUNDED_CONTEXTS.items():
        persistence_path = context_path / "infrastructure" / "persistence"
        for filename in ("ddl.sqlite.sql", "ddl.postgres.sql", "ddl.mysql.sql"):
            ddl_path = persistence_path / filename
            sql = ddl_path.read_text(encoding="utf-8")
            tables = ddl_tables(sql)
            if not tables and SYSTEM_TABLELESS_DDL_COMMENT not in sql:
                violations.append(f"{ddl_path.relative_to(ROOT)} defines no tables")
            for table_name, body in tables.items():
                missing = BASE_TABLE_COLUMNS - ddl_columns(body)
                if missing:
                    violations.append(
                        f"{ddl_path.relative_to(ROOT)} table {table_name} missing {', '.join(sorted(missing))}"
                    )
    assert not violations, "\n".join(violations)


def test_response_envelope_does_not_expand_business_data_to_top_level() -> None:
    http_path = BOUNDED_CONTEXTS["system"] / "interfaces" / "http.py"
    source = http_path.read_text(encoding="utf-8")
    assert "payload.update(data)" not in source


def test_list_pagination_uses_standard_field_names() -> None:
    violations: list[str] = []
    for base_path in (ROOT / "api", ROOT / "packages" / "python"):
        for path in python_files(base_path):
            source = path.read_text(encoding="utf-8")
            if '"pagination"' in source and ('"limit"' in source or '"offset"' in source):
                violations.append(str(path.relative_to(ROOT)))
    assert not violations, "pagination should use page/page_size/total:\n" + "\n".join(violations)


def test_application_code_uses_standard_time_field_names() -> None:
    violations: list[str] = []
    for base_path in (ROOT / "api", ROOT / "packages", ROOT / "web" / "admin" / "src"):
        for path in base_path.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".py", ".ts", ".tsx", ".vue", ".sql"}:
                continue
            source = path.read_text(encoding="utf-8")
            if "created_at" in source or "updated_at" in source:
                violations.append(str(path.relative_to(ROOT)))
    assert not violations, "use create_time/update_time instead of created_at/updated_at:\n" + "\n".join(violations)


def test_identity_relation_tables_use_id_primary_key_and_unique_business_key() -> None:
    violations: list[str] = []
    ddl_path = BOUNDED_CONTEXTS["identity_access"] / "infrastructure" / "persistence" / "ddl.sqlite.sql"
    tables = ddl_tables(ddl_path.read_text(encoding="utf-8"))
    for table_name, unique_columns in RELATION_UNIQUE_COLUMNS.items():
        body = tables.get(table_name, "")
        first_column = next((line.strip() for line in body.splitlines() if line.strip()), "")
        if not first_column.startswith("id "):
            violations.append(f"{table_name} does not define id as the first primary key column")
        unique_sql = f"UNIQUE ({', '.join(unique_columns)})"
        if unique_sql not in body:
            violations.append(f"{table_name} missing {unique_sql}")
    assert not violations, "\n".join(violations)


def test_runtime_code_does_not_trigger_database_initialization() -> None:
    violations: list[str] = []
    allowed_files = {
        ROOT / "scripts" / "init_identity_access.py",
        ROOT / "scripts" / "init_basic_data.py",
        ROOT / "scripts" / "init_personalization.py",
        ROOT / "scripts" / "init_page_designer.py",
        ROOT / "scripts" / "init_llm_runtime.py",
        ROOT / "scripts" / "init_appearance.py",
        ROOT / "scripts" / "init_cron.py",
        ROOT / "scripts" / "init_file_management.py",
        ROOT / "scripts" / "init_datasets.py",
        ROOT / "scripts" / "init_audit_logging.py",
        ROOT / "scripts" / "init_ai_assets.py",
        ROOT / "scripts" / "init_ai_applications.py",
        ROOT / "scripts" / "init_ai_capabilities.py",
        ROOT / "scripts" / "init_organization.py",
        ROOT / "scripts" / "init_authorization.py",
        BOUNDED_CONTEXTS["appearance"] / "entrypoints.py",
        BOUNDED_CONTEXTS["appearance"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["basic_data"] / "entrypoints.py",
        BOUNDED_CONTEXTS["basic_data"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["metadata_support"] / "entrypoints.py",
        BOUNDED_CONTEXTS["metadata_support"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["personalization"] / "entrypoints.py",
        BOUNDED_CONTEXTS["personalization"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["page_designer"] / "entrypoints.py",
        BOUNDED_CONTEXTS["page_designer"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["cron"] / "entrypoints.py",
        BOUNDED_CONTEXTS["cron"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["file_management"] / "entrypoints.py",
        BOUNDED_CONTEXTS["file_management"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["datasets"] / "entrypoints.py",
        BOUNDED_CONTEXTS["datasets"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["audit_logging"] / "entrypoints.py",
        BOUNDED_CONTEXTS["audit_logging"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["ai_assets"] / "entrypoints.py",
        BOUNDED_CONTEXTS["ai_assets"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["ai_applications"] / "entrypoints.py",
        BOUNDED_CONTEXTS["ai_applications"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["ai_capabilities"] / "entrypoints.py",
        BOUNDED_CONTEXTS["ai_capabilities"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["organization"] / "entrypoints.py",
        BOUNDED_CONTEXTS["organization"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["authorization"] / "entrypoints.py",
        BOUNDED_CONTEXTS["authorization"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["identity_access"] / "entrypoints.py",
        BOUNDED_CONTEXTS["identity_access"] / "infrastructure" / "persistence" / "common.py",
        BOUNDED_CONTEXTS["identity_access"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["llm_runtime"] / "entrypoints.py",
        BOUNDED_CONTEXTS["llm_runtime"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["messaging"] / "entrypoints.py",
        BOUNDED_CONTEXTS["messaging"] / "infrastructure" / "persistence" / "bootstrap.py",
    }
    forbidden = {
        "initialize_auth_storage",
        "ensure_auth_schema",
        "ensure_identity_schema",
        "ensure_identity_seed",
        "ensure_llm_schema",
        "ensure_ai_applications_schema",
        "ensure_ai_capabilities_schema",
        "_ensure_tenant_schema",
        "ensure_appearance_schema",
        "ensure_basic_data_schema",
            "ensure_cron_schema",
            "ensure_audit_logging_schema",
            "ensure_organization_schema",
        "ensure_authorization_schema",
        "ensure_personalization_schema",
        "ensure_page_designer_schema",
    }
    package_paths = [*BOUNDED_CONTEXTS.values(), ROOT / "api"]
    for package_path in package_paths:
        for path in python_files(package_path):
            if path in allowed_files:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in forbidden:
                    violations.append(f"{path.relative_to(ROOT)} calls {name}")
    assert not violations, "\n".join(violations)


def test_api_package_stays_entrypoint_only() -> None:
    forbidden_files = [
        ROOT / "api" / "services.py",
        ROOT / "api" / "schemas.py",
    ]
    existing = [str(path.relative_to(ROOT)) for path in forbidden_files if path.exists()]
    assert not existing, f"api package should not own business services or DTOs: {', '.join(existing)}"


def test_llm_core_stays_business_agnostic() -> None:
    violations: list[str] = []
    llm_core_path = PYTHON_PACKAGES_ROOT / "ops-admin-llm-runtime" / "src" / "framework" / "llm_core"
    forbidden = set(BOUNDED_CONTEXTS) | {"api", "fp_recommender"}
    for path in python_files(llm_core_path):
        imports = imported_modules(path) & forbidden
        if imports:
            violations.append(f"{path.relative_to(ROOT)} imports {', '.join(sorted(imports))}")
    assert not violations, "\n".join(violations)


def test_python_packages_have_required_metadata_and_entrypoints() -> None:
    expected = {
        "ops-admin-system": ("system", "system.entrypoints:router", "system.entrypoints:init_tasks"),
        "ops-admin-basic-data": ("basic_data", "basic_data.entrypoints:router", "basic_data.entrypoints:init_tasks"),
        "ops-admin-metadata-support": (
            "metadata_support",
            "metadata_support.entrypoints:router",
            "metadata_support.entrypoints:init_tasks",
        ),
        "ops-admin-personalization": (
            "personalization",
            "personalization.entrypoints:router",
            "personalization.entrypoints:init_tasks",
        ),
        "ops-admin-page-designer": (
            "page_designer",
            "page_designer.entrypoints:router",
            "page_designer.entrypoints:init_tasks",
        ),
        "ops-admin-cron": ("cron", "cron.entrypoints:router", "cron.entrypoints:init_tasks"),
        "ops-admin-file-management": (
            "file_management",
            "file_management.entrypoints:router",
            "file_management.entrypoints:init_tasks",
        ),
        "ops-admin-datasets": (
            "datasets",
            "datasets.entrypoints:router",
            "datasets.entrypoints:init_tasks",
        ),
        "ops-admin-audit-logging": (
            "audit_logging",
            "audit_logging.entrypoints:router",
            "audit_logging.entrypoints:init_tasks",
        ),
        "ops-admin-ai-assets": ("ai_assets", "ai_assets.entrypoints:router", "ai_assets.entrypoints:init_tasks"),
        "ops-admin-ai-applications": (
            "ai_applications",
            "ai_applications.entrypoints:router",
            "ai_applications.entrypoints:init_tasks",
        ),
        "ops-admin-ai-capabilities": (
            "ai_capabilities",
            "ai_capabilities.entrypoints:router",
            "ai_capabilities.entrypoints:init_tasks",
        ),
        "ops-admin-identity-access": (
            "identity_access",
            "identity_access.entrypoints:router",
            "identity_access.entrypoints:init_tasks",
        ),
        "ops-admin-organization": (
            "organization",
            "organization.entrypoints:router",
            "organization.entrypoints:init_tasks",
        ),
        "ops-admin-authorization": (
            "authorization",
            "authorization.entrypoints:router",
            "authorization.entrypoints:init_tasks",
        ),
        "ops-admin-appearance": ("appearance", "appearance.entrypoints:router", "appearance.entrypoints:init_tasks"),
        "ops-admin-llm-runtime": ("llm_runtime", "llm_runtime.entrypoints:router", "llm_runtime.entrypoints:init_tasks"),
        "ops-admin-messaging": ("messaging", "messaging.entrypoints:router", "messaging.entrypoints:init_tasks"),
    }
    violations: list[str] = []
    for package_name, (module_name, router_entrypoint, init_entrypoint) in expected.items():
        package_dir = PACKAGE_DIRS[package_name]
        pyproject_path = package_dir / "pyproject.toml"
        if not pyproject_path.exists():
            violations.append(f"{package_name} missing pyproject.toml")
            continue
        metadata = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = metadata["project"]
        if project["name"] != package_name:
            violations.append(f"{package_name} has project.name {project['name']}")
        if not (package_dir / "src" / module_name / "entrypoints.py").exists():
            violations.append(f"{package_name} missing {module_name}.entrypoints")
        entrypoints = project.get("entry-points", {})
        routers = entrypoints.get("ops_admin.routers", {})
        init_tasks = entrypoints.get("ops_admin.init_tasks", {})
        if routers.get(module_name) != router_entrypoint:
            violations.append(f"{package_name} missing router entrypoint")
        if init_tasks.get(module_name) != init_entrypoint:
            violations.append(f"{package_name} missing init task entrypoint")
    assert not violations, "\n".join(violations)
