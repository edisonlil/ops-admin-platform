# AI Applications

`ai_applications` owns tenant-facing AI applications in AI Studio.

Responsibilities:

- Application metadata and prompt runtime configuration.
- Publishable application API behavior.
- Tenant AI Studio quota records for applications and capabilities.
- Prompt runtime traces and application run logs for AI Studio v1.
- Application-bound Skills for single-turn and Agent runs.

It may call the `llm_runtime` application layer as an LLM gateway adapter. It must not import `llm_runtime.infrastructure` directly.

## Skill Runtime

Applications bind skills through `runtime_config.skills`:

```json
[
  {
    "skill_key": "log-analysis",
    "mode": "required",
    "inject_as": "analysis.log",
      "allowed_app_types": ["single_turn_generation", "agent"]
  }
]
```

Supported modes are `required`, `auto`, `manual`, and `disabled`. A run may also pass `skill_calls` for explicit manual calls. Skill results are injected into variables at `inject_as`, or under `_skills.<alias>` by default.

Workflow definitions do not support Skill nodes. Skills are conversation runtime capabilities for single-turn and Agent applications.

Script-capable skills never run inside the FastAPI process. They go through the `SkillSandboxRunner` port. The Docker adapter is opt-in with:

- `OPS_ADMIN_SKILL_SANDBOX_ENABLED=true`
- `OPS_ADMIN_SKILL_SANDBOX_IMAGE=python:3.11-slim`
- `OPS_ADMIN_SKILL_SANDBOX_NETWORK=bridge`
- `OPS_ADMIN_SKILL_SANDBOX_TIMEOUT_SECONDS=30`
- `OPS_ADMIN_SKILL_SANDBOX_USER=65534:65534`

Skill packages may declare `requirements.txt` or `scripts/requirements.txt`; the Docker runner installs them into `/workspace/.skill_deps` before executing the entrypoint. Without the sandbox being configured, script skills fail with a clear runtime error while prompt-context, LLM-task, and built-in skills still work.

## Agent File Workspace

Agent conversations include default file workspace tools for reading, writing, listing, finding, and searching files. The model requests these tools by returning `tool_calls` JSON; the application service executes the calls inside the conversation workspace, records the tool result as an agent `tool` message, and feeds the result back to the model.

The workspace root defaults to `.tmp/ai-agent-workspaces` and can be moved with `OPS_ADMIN_AGENT_WORKSPACE_ROOT`. Paths are always relative to the conversation workspace; absolute paths, drive letters, and `..` segments are rejected. Uploaded inline text/base64 files are materialized under `uploads/` when they fit the runtime size limits.

File tools are enabled by default for Agent applications. Disable them per app with:

```json
{
  "agent": {
    "file_tools_enabled": false
  }
}
```

Streaming Agent runs perform a lightweight file-tool planning preflight by default so stream and non-stream conversations have the same tool behavior. A single request can opt out with `file_tool_preflight=false`.

