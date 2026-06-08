from __future__ import annotations

import base64
from io import BytesIO
import zipfile

from ai_applications.application import skill_runtime


def test_skill_runtime_executes_multiple_bound_skills_and_injects_results(monkeypatch) -> None:
    def fake_resolver(skill_key: str, *, tenant_id: int) -> dict:
        runtime = (
            {"kind": "builtin_executor", "executor": "log_zip_error_inspector"}
            if skill_key == "log-analysis"
            else {"kind": "prompt_context"}
        )
        return {
            "skill_key": skill_key,
            "name": skill_key,
            "description": "",
            "resolved_version": "1.0.0",
            "manifest": {"runtime": runtime},
            "runtime_constraints": {},
            "content": "Use the provided study material.",
        }

    monkeypatch.setattr(skill_runtime, "resolve_published_skill", fake_resolver)
    zip_content = BytesIO()
    with zipfile.ZipFile(zip_content, "w") as archive:
        archive.writestr("app.log", "INFO boot\nERROR failed to connect\nTraceback: boom")
        archive.writestr("../secret.log", "ERROR unsafe")
    encoded = base64.b64encode(zip_content.getvalue()).decode("ascii")
    app = {
        "app_key": "log-helper",
        "app_type": "single_turn_generation",
        "tenant_id": 1,
        "runtime_config": {
            "skills": [
                {"skill_key": "log-analysis", "mode": "required", "inject_as": "analysis.log"},
                {"skill_key": "exam-material", "mode": "manual"},
            ]
        },
    }
    payload = {
        "files": [{"name": "logs.zip", "data_url": f"data:application/zip;base64,{encoded}"}],
        "skill_calls": [{"skill_key": "exam-material"}],
    }

    plan = skill_runtime.prepare_skill_runtime(app, payload, {"topic": "ops"}, app_type="single_turn_generation")
    results = skill_runtime.execute_pre_model_skills(plan)
    variables = skill_runtime.merge_skill_results_into_variables({"topic": "ops"}, plan, results)

    assert [item.skill_key for item in results] == ["log-analysis", "exam-material"]
    assert variables["analysis"]["log"]["scanned_files"] == 1
    assert variables["analysis"]["log"]["error_groups"]["error"] == 1
    assert variables["_skills"]["exam-material"]["content"] == "Use the provided study material."
    assert results[0].output["skipped_files"][0]["reason"] == "unsafe_path"


def test_sandbox_skill_uses_configured_runner(monkeypatch) -> None:
    monkeypatch.setattr(
        skill_runtime,
        "resolve_published_skill",
        lambda skill_key, *, tenant_id: {
            "skill_key": skill_key,
            "name": skill_key,
            "resolved_version": "1.0.0",
            "manifest": {"runtime": {"kind": "sandbox_python"}, "entrypoint": "main.py"},
            "runtime_constraints": {"network": "none"},
            "content": "print('ok')",
            "content_sha256": "abc",
        },
    )
    captured: dict = {}

    class FakeRunner:
        def run(self, request: dict) -> dict:
            captured.update(request)
            return {"status": "success", "output": {"answer": "ok"}}

    skill_runtime.configure_sandbox_runner(FakeRunner())
    try:
        app = {
            "app_key": "agent",
            "app_type": "agent",
            "tenant_id": 1,
            "runtime_config": {"skills": [{"skill_key": "python-tool", "mode": "required"}]},
        }
        plan = skill_runtime.prepare_skill_runtime(app, {}, {}, app_type="agent")
        results = skill_runtime.execute_pre_model_skills(plan)
    finally:
        skill_runtime.configure_sandbox_runner(None)

    assert results[0].output == {"answer": "ok"}
    assert captured["skill_key"] == "python-tool"
    assert captured["runtime_kind"] == "sandbox_python"
    assert captured["runtime_constraints"]["network"] == "none"


def test_llm_task_skill_uses_configured_runner(monkeypatch) -> None:
    monkeypatch.setattr(
        skill_runtime,
        "resolve_published_skill",
        lambda skill_key, *, tenant_id: {
            "skill_key": skill_key,
            "name": skill_key,
            "resolved_version": "1.0.0",
            "manifest": {"runtime": {"kind": "llm_task"}, "outputs": {"artifacts": [{"key": "quiz_html", "type": "text/html"}]}},
            "runtime_constraints": {},
            "content": "Generate quiz HTML.",
            "content_sha256": "abc",
            "package_data_base64": "UEsDBAo=",
            "package_sha256": "def",
            "package_files": [{"path": "SKILL.md"}],
        },
    )
    captured: dict = {}

    class FakeLLMTaskRunner:
        def run(self, request: dict) -> dict:
            captured.update(request)
            return {"status": "success", "output": {"answer": "<html>quiz</html>", "artifacts": [{"type": "text/html"}]}}

    skill_runtime.configure_llm_task_runner(FakeLLMTaskRunner())
    try:
        app = {
            "app_key": "quiz",
            "app_type": "single_turn_generation",
            "tenant_id": 1,
            "runtime_config": {"skills": [{"skill_key": "quiz-from-content", "mode": "required"}]},
        }
        plan = skill_runtime.prepare_skill_runtime(app, {}, {"question": "docs"}, app_type="single_turn_generation")
        results = skill_runtime.execute_pre_model_skills(plan)
    finally:
        skill_runtime.configure_llm_task_runner(None)

    assert results[0].output["answer"] == "<html>quiz</html>"
    assert captured["skill_key"] == "quiz-from-content"
    assert captured["runtime_kind"] == "llm_task"
    assert captured["package_data_base64"] == "UEsDBAo="
    assert captured["package_files"] == [{"path": "SKILL.md"}]


def test_parse_planned_skill_calls_filters_to_auto_candidates(monkeypatch) -> None:
    monkeypatch.setattr(
        skill_runtime,
        "resolve_published_skill",
        lambda skill_key, *, tenant_id: {
            "skill_key": skill_key,
            "name": skill_key,
            "resolved_version": "1.0.0",
            "manifest": {"runtime": {"kind": "prompt_context"}},
            "runtime_constraints": {},
            "content": "",
        },
    )
    app = {
        "app_key": "agent",
        "tenant_id": 1,
        "runtime_config": {
            "skills": [
                {"skill_key": "log-analysis", "alias": "logs", "mode": "auto"},
                {"skill_key": "private-tool", "mode": "manual"},
            ]
        },
    }
    plan = skill_runtime.prepare_skill_runtime(app, {}, {}, app_type="agent")

    calls = skill_runtime.parse_planned_skill_calls(
        '{"skill_calls":[{"skill_key":"logs","input":{"q":"x"}},{"skill_key":"private-tool"},{"skill_key":"missing"}]}',
        plan,
        budget=3,
    )

    assert len(calls) == 1
    assert calls[0].skill_key == "logs"
    assert calls[0].input == {"q": "x"}


def test_materialize_toolbox_packages_extracts_sandbox_scripts(tmp_path) -> None:
    package = BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("scripts/pypdf_cli.py", "def main(argv): return {'argv': argv}")
        archive.writestr("SKILL.md", "name: pdf-tool")
    encoded = base64.b64encode(package.getvalue()).decode("ascii")
    plan = skill_runtime.SkillRuntimePlan(
        app_key="pdf-agent",
        app_type="agent",
        tenant_id=1,
        toolbox=[
            skill_runtime.SkillDescriptor(
                binding=skill_runtime.SkillBinding(skill_key="pdf-tool", alias="pdf"),
                resolved={"package_data_base64": encoded},
                manifest={"runtime": {"kind": "sandbox_python"}},
                runtime_config={},
                runtime_constraints={},
                runtime_kind="sandbox_python",
                executor_key="",
                content="",
                version="1.0.0",
            )
        ],
    )

    materialized = skill_runtime.materialize_toolbox_packages(tmp_path, plan)

    script_path = tmp_path / "scripts" / "pypdf_cli.py"
    assert script_path.exists()
    assert "scripts/pypdf_cli.py" in materialized
