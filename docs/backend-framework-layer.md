# Backend Framework Layer

`packages/python/framework/` is the backend framework and reusable capability layer.

It is for code that is shared by multiple bounded contexts but is not itself a business domain. Framework packages should feel like internal libraries: reusable, deterministic, and free of product ownership.

## Package Location

Shared framework packages live here:

```text
packages/python/framework/<package-name>/
```

For the AI runtime core, use:

```text
packages/python/framework/ops-admin-ai-runtime-core/
```

The import package should be:

```text
ai_runtime_core
```

For the productized AI service contract, use:

```text
packages/python/framework/ops-admin-ai-service-api/
```

The import package should be:

```text
ai_service_api
```

## What Belongs Here

Framework packages may contain:

- Pure runtime engines and orchestration primitives.
- Shared DTOs, schemas, value objects, and validation helpers.
- Ports/interfaces for external execution, storage, tools, model calls, tracing, or events.
- Reusable parsing, rendering, variable binding, prompt assembly, and trace normalization logic.
- Tests for framework behavior that do not require product modules.

## What Does Not Belong Here

Framework packages must not contain:

- Business tables or persistence ownership.
- FastAPI routers or business HTTP endpoints.
- Menu, permission, tenant default, or RBAC seed data.
- Product concepts such as AI applications, AI capabilities, tenants, published APIs, or quotas.
- Direct imports from bounded context `infrastructure` packages.
- Direct dependencies on `llm_runtime` or any provider implementation.

## Dependency Rule

Bounded contexts may depend on framework packages:

```text
ai_applications
ai_capabilities
workflow_runtime
agent_runtime
        |
        v
packages/python/framework/ops-admin-ai-runtime-core
```

Framework packages should depend only on Python standard library, small stable third-party libraries, and other framework packages when necessary.

When framework code needs an LLM call or other external operation, it must define a port:

```python
class LLMGatewayPort(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...
```

The bounded context or composition layer provides the adapter. For example, `ai_applications` can wire `LLMGatewayPort` to an application service from `llm_runtime`, but `ai_runtime_core` must not import `llm_runtime`.

## AI Runtime Core Boundary

`ops-admin-ai-runtime-core` is the common execution kernel for AI-facing domains.

It should own reusable runtime mechanics such as:

- Prompt variable parsing and binding.
- Prompt message assembly.
- Runtime input/output contracts.
- Streaming event normalization.
- Runtime trace shape and replay-friendly metadata.
- Tool and model gateway ports.

It should not decide:

- Whether something is an AI application or an AI capability.
- Whether an API can be externally published.
- Which tenant owns a resource.
- Whether a user can create, publish, archive, or execute something.
- How menus, permissions, quotas, or audit policies work.

Those decisions stay in bounded contexts.

## AI Service API Boundary

`ops-admin-ai-service-api` is the stable business-facing contract for optional AI capability execution. Business contexts use it when they need a productized AI capability, for example:

```python
get_ai_service().execute("prompt.polish", {"prompt": text})
```

This package may define only contracts, DTOs, exceptions, and a default unavailable provider. It must not know how AI capabilities are stored, seeded, authorized, resolved, or executed.

The implementation lives in `ai_capabilities`. Its resolution rule is:

```text
current tenant AI capability with same key
  -> platform seeded AI capability with same key
  -> unavailable/not found
```

Execution always uses the current tenant context for model route resolution. Other bounded contexts must not import `ai_capabilities`; they depend only on `ai_service_api`. If a project omits `ai_capabilities`, the default provider should allow the app to start and return a clear "AI service is not available" error only when the AI-assisted feature is invoked.
