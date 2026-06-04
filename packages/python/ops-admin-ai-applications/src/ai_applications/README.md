# AI Applications

`ai_applications` owns tenant-facing AI applications in AI Studio.

Responsibilities:

- Application metadata and prompt runtime configuration.
- Publishable application API behavior.
- Tenant AI Studio quota records for applications and capabilities.
- Prompt runtime traces and application run logs for AI Studio v1.
- Application-bound Skills for single-turn, Agent, and workflow runs.

It may call the `llm_runtime` application layer as an LLM gateway adapter. It must not import `llm_runtime.infrastructure` directly.

## Skill Runtime

Applications bind skills through `runtime_config.skills`:

```json
[
  {
    "skill_key": "log-analysis",
    "mode": "required",
    "inject_as": "analysis.log",
    "allowed_app_types": ["single_turn_generation", "agent", "workflow"]
  }
]
```

Supported modes are `required`, `auto`, `manual`, and `disabled`. A run may also pass `skill_calls` for explicit manual calls. Skill results are injected into variables at `inject_as`, or under `_skills.<alias>` by default.

Script-capable skills never run inside the FastAPI process. They go through the `SkillSandboxRunner` port. The Docker adapter is opt-in with:

- `OPS_ADMIN_SKILL_SANDBOX_ENABLED=true`
- `OPS_ADMIN_SKILL_SANDBOX_IMAGE=python:3.11-slim`
- `OPS_ADMIN_SKILL_SANDBOX_NETWORK=none`
- `OPS_ADMIN_SKILL_SANDBOX_TIMEOUT_SECONDS=30`
- `OPS_ADMIN_SKILL_SANDBOX_USER=65534:65534`

Without the sandbox being configured, script skills fail with a clear runtime error while prompt-context and built-in skills still work.

