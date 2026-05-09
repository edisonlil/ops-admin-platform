from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_PROJECT_SCRIPT = ROOT / "skills" / "ops-admin-platform" / "scripts" / "create_project.py"


def load_create_project_module():
    spec = importlib.util.spec_from_file_location("ops_admin_create_project", CREATE_PROJECT_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_project_generates_package_consuming_scaffold(tmp_path: Path) -> None:
    module = load_create_project_module()
    target = tmp_path / "sample"

    module.create_project(
        target,
        "sample",
        ("identity_access", "appearance", "llm_runtime"),
        package_version="1.2.3",
        frontend_package_version="4.5.6",
    )

    requirements = (target / "requirements.txt").read_text(encoding="utf-8")
    package_json = json.loads((target / "web" / "admin" / "package.json").read_text(encoding="utf-8"))
    module_registry = (target / "api" / "module_registry.py").read_text(encoding="utf-8")
    frontend_modules = (target / "web" / "admin" / "src" / "modules.ts").read_text(encoding="utf-8")

    assert not (target / "packages" / "python").exists()
    assert not (target / "packages" / "web" / "ops-admin-web").exists()
    assert "-e packages/python/" not in requirements
    assert "ops-admin-system==1.2.3" in requirements
    assert "ops-admin-identity-access==1.2.3" in requirements
    assert "ops-admin-appearance==1.2.3" in requirements
    assert "ops-admin-llm-runtime==1.2.3" in requirements
    assert package_json["dependencies"]["@edisonlil/ops-admin-web"] == "4.5.6"
    assert '"identity_access"' in module_registry
    assert "registerIdentityAccessModule();" in frontend_modules
    assert "registerAppearanceModule();" in frontend_modules
    assert "registerLlmRuntimeModule();" in frontend_modules


def test_create_project_leaves_versions_unpinned_by_default(tmp_path: Path) -> None:
    module = load_create_project_module()
    target = tmp_path / "sample"

    module.create_project(target, "sample", ("appearance",))

    requirements = (target / "requirements.txt").read_text(encoding="utf-8")
    package_json = json.loads((target / "web" / "admin" / "package.json").read_text(encoding="utf-8"))
    frontend_modules = (target / "web" / "admin" / "src" / "modules.ts").read_text(encoding="utf-8")

    assert "ops-admin-system\n" in requirements
    assert "ops-admin-appearance\n" in requirements
    assert "ops-admin-identity-access" not in requirements
    assert package_json["dependencies"]["@edisonlil/ops-admin-web"] == "*"
    assert "registerAppearanceModule();" in frontend_modules
    assert "registerIdentityAccessModule();" not in frontend_modules
