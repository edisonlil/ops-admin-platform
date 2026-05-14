# Organization

The organization bounded context owns tenant-scoped departments and user department memberships.

It exposes organization facts to identity and authorization through application services. Other bounded contexts must not import organization infrastructure directly.
