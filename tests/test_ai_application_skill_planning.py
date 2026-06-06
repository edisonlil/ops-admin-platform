from __future__ import annotations

from ai_applications.application import services
from ai_applications.application import skill_runtime


def test_plan_agent_skills_if_enabled_selects_auto_skills(monkeypatch) -> None:
    monkeypatch.setattr(
        skill_runtime,
        "resolve_published_skill",
        lambda skill_key, *, tenant_id: {
            "skill_key": skill_key,
            "name": skill_key,
            "description": "Analyze logs" if skill_key == "log-analysis" else "Other",
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
            "agent": {"skill_planning": True, "skill_call_budget": 2},
            "skills": [
                {"skill_key": "log-analysis", "mode": "auto"},
                {"skill_key": "manual-only", "mode": "manual"},
            ],
        },
    }
    plan = skill_runtime.prepare_skill_runtime(app, {}, {}, app_type="agent")
    captured: dict = {}

    def fake_chat_completions(**kwargs):
        captured.update(kwargs)
        return {"choices": [{"message": {"content": '{"skill_calls":[{"skill_key":"log-analysis","input":{"q":"error"}}]}'}}]}

    monkeypatch.setattr(services.gateway, "chat_completions", fake_chat_completions)

    services.plan_agent_skills_if_enabled(
        app,
        {},
        {"topic": "logs"},
        "please inspect errors",
        plan,
        model="test-model",
        temperature=0.7,
    )

    assert captured["model"] == "test-model"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["temperature"] == 0.2
    assert len(plan.planned_calls) == 1
    assert plan.planned_calls[0].skill_key == "log-analysis"
    assert plan.planned_calls[0].input == {"q": "error"}


def test_plan_agent_skills_if_enabled_is_opt_in(monkeypatch) -> None:
    app = {"app_key": "agent", "tenant_id": 1, "runtime_config": {"skills": []}}
    plan = skill_runtime.SkillRuntimePlan(app_key="agent", app_type="agent", tenant_id=1)

    def fail_chat_completions(**kwargs):
        raise AssertionError("planner should not call the LLM unless enabled")

    monkeypatch.setattr(services.gateway, "chat_completions", fail_chat_completions)

    services.plan_agent_skills_if_enabled(app, {}, {}, "hello", plan, model="test", temperature=None)

    assert plan.planned_calls == []


def test_workflow_definition_rejects_skill_nodes() -> None:
    workflow = {
        "nodes": [
            {"id": "start", "type": "start", "data": {"variables": []}},
            {"id": "skill_1", "type": "skill", "data": {"skill_key": "quiz-from-content"}},
            {"id": "end", "type": "end", "data": {"output": "{{skill_result}}"}},
        ],
        "edges": [
            {"id": "start-skill_1", "source": "start", "target": "skill_1"},
            {"id": "skill_1-end", "source": "skill_1", "target": "end"},
        ],
    }

    try:
        services.validate_workflow_definition_payload(workflow)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 422
        assert "Skill" in str(getattr(exc, "detail", ""))
    else:
        raise AssertionError("workflow Skill nodes must be rejected")
