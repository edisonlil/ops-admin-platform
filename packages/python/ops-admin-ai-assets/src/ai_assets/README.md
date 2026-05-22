# AI Assets

The `ai_assets` bounded context manages tenant-scoped AI assets and their versions.

Current asset families:

- Prompt assets: create prompts, edit metadata, maintain versions, publish versions, and archive prompts.
- Skill assets: upload ZIP packages containing `SKILL.md`, validate metadata/content, maintain versions, publish versions, and archive skills.

MCP definitions should follow the same asset pattern in a later phase, but execution adapters do not belong in this context.

AI applications and AI capabilities consume assets through application-layer resolvers such as `resolve_published_prompt` and `resolve_published_skill`. They must not import `ai_assets.infrastructure` directly.

Prompt authoring assistance uses the `ai_service_api` contract and must not import `ai_capabilities` directly. When `ai_capabilities` is installed, `prompt.polish` is resolved through the current tenant override first and then the platform-seeded capability. When `ai_capabilities` is omitted, the prompt library still starts and the assist endpoint reports that AI service is unavailable.

Skill upload only accepts ZIP packages and stores the validated `SKILL.md` definition. Uploaded skill content is not executed by this bounded context.

Runtime code checks that the schema already exists. Initialize storage explicitly with:

```bash
python scripts/init_ai_assets.py
```
