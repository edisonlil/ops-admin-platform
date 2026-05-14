# Authorization

The authorization bounded context owns data-scope resource descriptors, role data policies, and filter resolution.

It is optional and implements the shared `system.application.data_access.DataAccessFilterProvider` contract. Business contexts should depend on the shared contract instead of this context directly.
