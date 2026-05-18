# AI Capabilities

`ai_capabilities` owns internal AI capabilities that are called by platform modules through APIs such as `aiService.execute`.

Responsibilities:

- Capability metadata and prompt runtime configuration.
- Tenant-scoped capability management.
- Internal execution endpoints for capability calls.

It reuses the AI application prompt runtime execution service for AI Studio v1, but it owns the `ai_capabilities` table and must not live inside `llm_runtime`.

See `docs/ai-capability-integration.md` for business-context integration rules, media variable shape, and provider-specific pitfalls.

