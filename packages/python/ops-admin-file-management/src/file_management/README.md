# File Management

`file_management` owns tenant file libraries, file metadata, tenant storage quotas, object storage profiles, external preview profiles, and file search boundaries.

Runtime request handling must only verify that persistence resources already exist. Schema creation and seed application are explicit initialization tasks exposed through `file_management.entrypoints:init_tasks`.

The first storage adapter targets MinIO. Other object storage providers are modeled as provider values for future adapters, but unsupported providers are rejected by application services.

Native preview handles images, PDF, plain text, JSON, CSV, Markdown, common audio, and common video directly. External preview profiles are platform-level configuration records for formats such as Office documents. The initial external provider builds kkFileView `/onlinePreview` URLs from signed, short-lived source URLs; the same profile model also leaves a custom provider slot for later preview services.

When an external preview service must fetch source files, set `OPS_ADMIN_PUBLIC_API_BASE_URL` to the public API origin and optional API prefix through `OPS_ADMIN_PUBLIC_API_URL_PREFIX` (default `/api`). Signatures use `OPS_ADMIN_FILE_PREVIEW_SECRET` when present.
