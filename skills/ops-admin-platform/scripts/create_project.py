from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_MODULES = ("identity_access", "appearance", "llm_runtime")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def package_name(module: str) -> str:
    return f"ops-admin-{module.replace('_', '-')}"


def create_python_package(root: Path, module: str) -> None:
    package = root / "packages" / "python" / package_name(module)
    module_dir = package / "src" / module
    write(
        package / "pyproject.toml",
        f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{package_name(module)}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["fastapi"]

[project.entry-points."ops_admin.routers"]
{module} = "{module}.entrypoints:router"

[project.entry-points."ops_admin.init_tasks"]
{module} = "{module}.entrypoints:init_tasks"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
{module} = ["infrastructure/persistence/*.sql"]
""",
    )
    write(module_dir / "README.md", f"# {module}\n\nBounded context for {module}.\n")
    write(module_dir / "__init__.py", "")
    write(
        module_dir / "entrypoints.py",
        f"""from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/{module.replace('_', '-')}", tags=["{module}"])


def init_tasks() -> Mapping[str, Callable[[Any], None]]:
    return {{}}
""",
    )
    for folder in ("domain", "application", "infrastructure", "infrastructure/persistence", "interfaces", "interfaces/http"):
        write(module_dir / folder / "__init__.py", "")
    for filename in ("ddl.sqlite.sql", "ddl.postgres.sql", "seed.sql"):
        write(module_dir / "infrastructure" / "persistence" / filename, "-- explicit initialization resource\n")


def create_project(target: Path, name: str, modules: tuple[str, ...]) -> None:
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"target directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    write(
        target / "AGENTS.md",
        """# ops-admin-platform Project Rules

- Keep backend bounded contexts under packages/python.
- Keep frontend shared module contracts under packages/web.
- Runtime code must not initialize or seed database schema implicitly.
""",
    )
    write(
        target / "tasks.md",
        """# Tasks

- [ ] Create project from ops-admin-platform starter.
- [ ] Enable required modules.
- [ ] Run backend tests.
- [ ] Run frontend build.
""",
    )
    write(
        target / "requirements.txt",
        "\n".join(["fastapi", "uvicorn[standard]", *(f"-e packages/python/{package_name(module)}" for module in modules), ""]),
    )
    write(
        target / "api" / "module_registry.py",
        f"""MODULES = {json.dumps(list(modules), indent=2)}
""",
    )
    write(target / "api" / "__init__.py", "")
    write(
        target / "web" / "admin" / "src" / "modules.ts",
        """import {
  clearOpsAdminModules,
  registerAppearanceModule,
  registerIdentityAccessModule,
  registerLlmRuntimeModule,
} from '@edisonlil/ops-admin-web';

export function setupStarterModules() {
  clearOpsAdminModules();
  registerIdentityAccessModule();
  registerAppearanceModule();
  registerLlmRuntimeModule();
}
""",
    )
    write(
        target / "packages" / "web" / "ops-admin-web" / "package.json",
        """{
  "name": "@edisonlil/ops-admin-web",
  "version": "0.1.0",
  "type": "module"
}
""",
    )
    for module in modules:
        create_python_package(target, module)


def parse_modules(value: str) -> tuple[str, ...]:
    modules = tuple(item.strip() for item in value.split(",") if item.strip())
    return modules or DEFAULT_MODULES


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an ops-admin-platform starter skeleton.")
    parser.add_argument("target", type=Path)
    parser.add_argument("--name", default="ops-admin-starter")
    parser.add_argument("--modules", default=",".join(DEFAULT_MODULES), help="Comma-separated module names.")
    args = parser.parse_args()

    create_project(args.target.resolve(), args.name, parse_modules(args.modules))
    print(f"created {args.name}: {args.target.resolve()}")


if __name__ == "__main__":
    main()
