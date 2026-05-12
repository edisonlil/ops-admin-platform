# File Management

`file_management` owns tenant file libraries, file metadata, tenant storage quotas, object storage profiles, and file search boundaries.

Runtime request handling must only verify that persistence resources already exist. Schema creation and seed application are explicit initialization tasks exposed through `file_management.entrypoints:init_tasks`.

The first storage adapter targets MinIO. Other object storage providers are modeled as provider values for future adapters, but unsupported providers are rejected by application services.
