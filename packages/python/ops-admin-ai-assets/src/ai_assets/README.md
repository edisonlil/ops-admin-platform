# AI Assets

The `ai_assets` bounded context manages tenant-scoped prompt assets and their versions.

The first phase deliberately stays focused on prompt library management: create prompts, edit metadata, maintain versions, publish versions, and archive prompts. Task contracts, prompt bindings, and contract-driven execution are not part of this module.

Runtime code checks that the schema already exists. Initialize storage explicitly with:

```bash
python scripts/init_ai_assets.py
```
