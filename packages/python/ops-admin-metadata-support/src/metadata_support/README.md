# Metadata Support

`metadata_support` owns reusable metadata and tag bindings for resources from other bounded contexts.

The context stores complete metadata JSON for display and audit, and expands searchable scalar fields into typed index rows for filtering and sorting. Business contexts should call application services or ports instead of importing this context's infrastructure package.

Runtime request handling must only verify that persistence resources already exist. Schema creation and seed application are explicit initialization tasks exposed through `metadata_support.entrypoints:init_tasks`.
