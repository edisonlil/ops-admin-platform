# AI Assets

The `ai_assets` bounded context manages prompt assets, prompt versions, task contracts, bindings, and prompt run evidence.

Business contexts should call the application layer with a `contract_key` and variables. They should not own prompt text or bind directly to arbitrary prompt versions.

Runtime code checks that the schema already exists. Initialize storage explicitly with:

```bash
python scripts/init_ai_assets.py
```
