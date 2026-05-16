# AI Applications

`ai_applications` owns tenant-facing AI applications in AI Studio.

Responsibilities:

- Application metadata and prompt runtime configuration.
- Publishable application API behavior.
- Tenant AI Studio quota records for applications and capabilities.
- Prompt runtime traces and application run logs for AI Studio v1.

It may call the `llm_runtime` application layer as an LLM gateway adapter. It must not import `llm_runtime.infrastructure` directly.

