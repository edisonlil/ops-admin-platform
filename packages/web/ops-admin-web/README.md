# @edisonlil/ops-admin-web

Shared frontend contracts for ops-admin-platform starters.

The package owns reusable module registration, menu filtering, request envelope, auth, layout, and store contracts. Starter applications can keep their concrete pages and styling local while consuming the package-level APIs to opt modules in or out independently.

## Module Registration

```ts
import {
  clearOpsAdminModules,
  registerAppearanceModule,
  registerIdentityAccessModule,
  registerLlmRuntimeModule,
} from '@edisonlil/ops-admin-web';

clearOpsAdminModules();
registerIdentityAccessModule();
registerAppearanceModule();
registerLlmRuntimeModule();
```

When a known module is not registered, its known menu keys are filtered from backend menu trees.
