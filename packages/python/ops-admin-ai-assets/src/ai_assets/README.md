# AI Assets

The `ai_assets` bounded context manages tenant-scoped prompt assets and their versions.

The first phase deliberately stays focused on prompt library management: create prompts, edit metadata, maintain versions, publish versions, and archive prompts. Task contracts, prompt bindings, and contract-driven execution are not part of this module.

Prompt authoring assistance uses the `ai_service_api` contract and must not import `ai_capabilities` directly. When `ai_capabilities` is installed, `prompt.polish` is resolved through the current tenant override first and then the platform-seeded capability. When `ai_capabilities` is omitted, the prompt library still starts and the assist endpoint reports that AI service is unavailable.

Runtime code checks that the schema already exists. Initialize storage explicitly with:

```bash
python scripts/init_ai_assets.py
```
