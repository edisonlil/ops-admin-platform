# Authorization

The authorization bounded context owns data-scope resource descriptors, tenant role data policies, and filter resolution.

Resource descriptors are platform-level capability definitions. Role data policies are tenant-scoped records: each tenant administrator configures the scopes for roles inside the current tenant.

It is optional and implements the shared `system.application.data_access.DataAccessFilterProvider` contract. Business contexts should depend on the shared contract instead of this context directly.
