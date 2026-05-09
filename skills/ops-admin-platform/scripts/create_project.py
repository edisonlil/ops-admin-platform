from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_MODULES = ("identity_access", "appearance", "llm_runtime")
FRONTEND_MODULE_REGISTRATIONS = {
    "appearance": "registerAppearanceModule",
    "identity_access": "registerIdentityAccessModule",
    "llm_runtime": "registerLlmRuntimeModule",
}


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def package_name(module: str) -> str:
    return f"ops-admin-{module.replace('_', '-')}"


def versioned_package(name: str, version: str | None) -> str:
    if version:
        return f"{name}=={version}"
    return name


def npm_dependency_version(version: str | None) -> str:
    return version or "*"


def frontend_modules_source(modules: tuple[str, ...]) -> str:
    registrations = [
        FRONTEND_MODULE_REGISTRATIONS[module]
        for module in modules
        if module in FRONTEND_MODULE_REGISTRATIONS
    ]
    imports = ["clearOpsAdminModules", *sorted(registrations)]
    import_lines = ",\n  ".join(imports)
    register_lines = "\n".join(f"  {registration}();" for registration in sorted(registrations))
    if register_lines:
        register_lines = f"\n{register_lines}"
    return f"""import {{
  {import_lines},
}} from '@edisonlil/ops-admin-web';

export function setupStarterModules() {{
  clearOpsAdminModules();{register_lines}
}}
"""


def create_project(
    target: Path,
    name: str,
    modules: tuple[str, ...],
    package_version: str | None = None,
    frontend_package_version: str | None = None,
) -> None:
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"target directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    write(
        target / "AGENTS.md",
        """# ops-admin-platform Project Rules

- This project uses the scaffold route and consumes ops-admin-platform public packages.
- Platform capabilities come from pip/npm dependencies, not copied platform package source.
- Add local business bounded contexts under the application's own source tree.
- Do not create packages/python/ops-admin-* or packages/web/ops-admin-web as scaffold output.
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
        "\n".join(
            [
                "fastapi",
                "uvicorn[standard]",
                versioned_package("ops-admin-system", package_version),
                *(
                    versioned_package(package_name(module), package_version)
                    for module in modules
                    if module != "system"
                ),
                "",
            ]
        ),
    )
    write(
        target / "api" / "module_registry.py",
        f"""MODULES = {json.dumps(list(modules), indent=2)}
""",
    )
    write(target / "api" / "__init__.py", "")
    write(
        target / "web" / "admin" / "src" / "modules.ts",
        frontend_modules_source(modules),
    )
    write(
        target / "web" / "admin" / "package.json",
        json.dumps(
            {
                "name": f"{name}-admin",
                "private": True,
                "type": "module",
                "dependencies": {
                    "@edisonlil/ops-admin-web": npm_dependency_version(frontend_package_version),
                },
            },
            indent=2,
        )
        + "\n",
    )


def parse_modules(value: str) -> tuple[str, ...]:
    modules = tuple(item.strip() for item in value.split(",") if item.strip())
    return modules or DEFAULT_MODULES


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an ops-admin-platform starter skeleton.")
    parser.add_argument("target", type=Path)
    parser.add_argument("--name", default="ops-admin-starter")
    parser.add_argument("--modules", default=",".join(DEFAULT_MODULES), help="Comma-separated module names.")
    parser.add_argument("--package-version", default=None, help="Optional version pin for ops-admin Python packages.")
    parser.add_argument(
        "--frontend-package-version",
        default=None,
        help="Optional version pin for @edisonlil/ops-admin-web.",
    )
    args = parser.parse_args()

    create_project(
        args.target.resolve(),
        args.name,
        parse_modules(args.modules),
        package_version=args.package_version,
        frontend_package_version=args.frontend_package_version,
    )
    print(f"created {args.name}: {args.target.resolve()}")


if __name__ == "__main__":
    main()
