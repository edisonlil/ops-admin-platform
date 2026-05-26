# Datasets

The datasets bounded context owns platform-managed dataset definitions, field schemas, manual dataset rows, publish snapshots, and runtime preview contracts for page-designer charts and future platform data-source consumers.

Datasets are currently platform assets. Runtime services store and read them from the platform tenant domain; tenant-managed datasets and tenant-specific dataset implementations are intentionally deferred until their business scenarios are defined.

Runtime code must not initialize or repair storage implicitly. Run `python scripts/init_datasets.py` after installing or changing the module schema.
