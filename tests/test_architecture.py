from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGES_ROOT = ROOT / "packages" / "python"
BOUNDED_CONTEXTS = {
    "appearance": PYTHON_PACKAGES_ROOT / "ops-admin-appearance" / "src" / "appearance",
    "cron": PYTHON_PACKAGES_ROOT / "ops-admin-cron" / "src" / "cron",
    "identity_access": PYTHON_PACKAGES_ROOT / "ops-admin-identity-access" / "src" / "identity_access",
    "llm_runtime": PYTHON_PACKAGES_ROOT / "ops-admin-llm-runtime" / "src" / "llm_runtime",
    "messaging": PYTHON_PACKAGES_ROOT / "ops-admin-messaging" / "src" / "messaging",
    "system": PYTHON_PACKAGES_ROOT / "ops-admin-system" / "src" / "system",
}
PACKAGE_DIRS = {
    "ops-admin-appearance": PYTHON_PACKAGES_ROOT / "ops-admin-appearance",
    "ops-admin-cron": PYTHON_PACKAGES_ROOT / "ops-admin-cron",
    "ops-admin-identity-access": PYTHON_PACKAGES_ROOT / "ops-admin-identity-access",
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
        for filename in ("ddl.sqlite.sql", "ddl.postgres.sql"):
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
        ROOT / "scripts" / "init_llm_runtime.py",
        ROOT / "scripts" / "init_appearance.py",
        ROOT / "scripts" / "init_cron.py",
        BOUNDED_CONTEXTS["appearance"] / "entrypoints.py",
        BOUNDED_CONTEXTS["appearance"] / "infrastructure" / "persistence" / "bootstrap.py",
        BOUNDED_CONTEXTS["cron"] / "entrypoints.py",
        BOUNDED_CONTEXTS["cron"] / "infrastructure" / "persistence" / "bootstrap.py",
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
        "_ensure_tenant_schema",
        "ensure_appearance_schema",
        "ensure_cron_schema",
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
        "ops-admin-cron": ("cron", "cron.entrypoints:router", "cron.entrypoints:init_tasks"),
        "ops-admin-identity-access": (
            "identity_access",
            "identity_access.entrypoints:router",
            "identity_access.entrypoints:init_tasks",
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
