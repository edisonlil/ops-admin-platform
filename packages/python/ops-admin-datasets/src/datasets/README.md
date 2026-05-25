# Datasets

The datasets bounded context owns tenant dataset definitions, field schemas, manual dataset rows, publish snapshots, and runtime preview contracts for dashboard and future data-source consumers.

Runtime code must not initialize or repair storage implicitly. Run `python scripts/init_datasets.py` after installing or changing the module schema.
