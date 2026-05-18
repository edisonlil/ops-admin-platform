# Data Access Integration Guide

Data access is a shared system capability. New business modules should integrate it through the unified helpers in `system.application.data_access` instead of resolving policies or hand-building predicates directly.

The design is explicit rather than transparent SQL interception: application services choose the business action (`read`, `write`, or `manage`), repositories apply the resulting predicate to SQL, and write paths guard the target record before mutation. This keeps behavior easy to review while keeping module integration small.

## Required Table Columns

Every table that participates in data access must include:

```sql
tenant_id BIGINT NOT NULL
owner_user_id BIGINT DEFAULT NULL
owner_department_id BIGINT DEFAULT NULL
creator_id BIGINT DEFAULT NULL
deleted BOOLEAN/INTEGER NOT NULL DEFAULT 0
```

Default scope mapping:

- `tenant`: records in the current tenant.
- `self`: records where `owner_user_id` matches the current user.
- `department`, `department_and_children`, `custom_departments`: records where `owner_department_id` is in the resolved department set.

Prefer these standard column names. If a legacy table cannot use them, declare the custom column names in its `ResourceDescriptor`.

## Register A Resource

Add the resource to `packages/python/ops-admin-authorization/src/authorization/infrastructure/persistence/seed.sql`:

```sql
SELECT
    'sales.order',
    'Sales Order',
    'Tenant sales order data',
    'tenant_id',
    'creator_id',
    'owner_user_id',
    'owner_department_id',
    '["self","department","department_and_children","custom_departments","tenant"]',
    FALSE
```

After changing authorization seed data, run:

```powershell
python scripts/init_authorization.py
```

If the module also changed its own schema or seed data, run that module's explicit init script too. Do not initialize, migrate, seed, backfill, or repair this data from runtime request handlers, repositories, routers, or application services.

## Application Service Pattern

Declare the resource once in the bounded context application layer:

```python
from system.application.data_access import ResourceDescriptor, data_access_for, data_owner_fields

ORDER_RESOURCE = ResourceDescriptor(resource_key="sales.order")
```

For legacy column names:

```python
ORDER_RESOURCE = ResourceDescriptor(
    resource_key="sales.order",
    tenant_column="tenant_id",
    owner_user_column="created_by_id",
    owner_department_column="department_id",
)
```

Use `data_access_for` to generate action-specific predicates:

```python
scope = data_access_for(current_user, ORDER_RESOURCE)

items, total = repo().list_orders(
    tenant_id=current_tenant_id(current_user),
    page=page,
    page_size=page_size,
    data_scope=scope.read(),
)
```

Use the action that matches the operation:

| Operation | Action |
| --- | --- |
| list, detail, preview, download | `read` |
| create child record under an accessible parent, update draft/editable record | `write` |
| delete, publish, enable, disable, trigger, archive, reindex, status change | `manage` |

When creating a record, stamp ownership with the shared helper:

```python
payload = {
    **payload,
    **data_owner_fields(current_user),
}
```

## Repository SQL Pattern

Repository methods should accept a `DataAccessPredicate | None` and apply it with `apply_data_access`.

```python
from system.application.data_access import DataAccessPredicate, ResourceDescriptor, apply_data_access

ORDER_RESOURCE = ResourceDescriptor(resource_key="sales.order")


def list_orders(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    data_scope: DataAccessPredicate | None = None,
) -> tuple[list[Order], int]:
    filters = ["o.tenant_id = ?", "o.deleted = 0"]
    params: list[object] = [tenant_id]
    apply_data_access(filters, params, data_scope=data_scope, resource=ORDER_RESOURCE, alias="o")
    where_sql = " AND ".join(filters)
    ...
```

`apply_data_access` avoids adding a duplicate tenant predicate when the repository already has one. Pass `alias` whenever the table is referenced with an alias.

Detail queries must also accept and apply `data_scope`:

```python
def get_order_detail(
    *,
    tenant_id: int,
    order_id: int,
    data_scope: DataAccessPredicate | None = None,
) -> Order | None:
    filters = ["o.id = ?", "o.tenant_id = ?", "o.deleted = 0"]
    params: list[object] = [order_id, tenant_id]
    apply_data_access(filters, params, data_scope=data_scope, resource=ORDER_RESOURCE, alias="o")
    ...
```

## Write And Manage Guard

Do not mutate a row after checking only `tenant_id`. Load the target with a scoped detail query or guard a raw row before mutation.

Scoped detail query:

```python
existing = repo().get_order_detail(
    tenant_id=tenant_id,
    order_id=order_id,
    data_scope=data_access_for(current_user, ORDER_RESOURCE).write(),
)
if not existing:
    raise OrderNotFoundError("order not found")
```

Record guard:

```python
from system.application.data_access import ensure_data_access_record

row = repo().get_order_row(tenant_id=tenant_id, order_id=order_id)
ensure_data_access_record(
    row,
    current_user=current_user,
    resource=ORDER_RESOURCE,
    action="manage",
    denied=OrderNotFoundError("order not found"),
)
```

Prefer returning a not-found domain error for inaccessible records so APIs do not disclose whether another user's record exists.

## Import Jobs, Trees, And Derived Reads

Bulk import, tree, option, and aggregate endpoints still need an explicit decision:

- If they expose business rows, apply data access.
- If they expose system reference data that must be tenant-wide, document why and keep tenant filtering.
- If they update existing rows, check `write` access for every existing target row before applying changes.

Do not assume that a page is safe because its list endpoint is scoped; every detail, export, mutation, and background-triggered operation needs its own action decision.

## Test Requirements

Every module that joins data access should add regression tests for:

1. `self` scope list returns only owned rows.
2. Detail read cannot load another user's row.
3. `write` cannot update another user's row.
4. `manage` cannot delete, publish, enable, disable, trigger, archive, or reindex another user's row.
5. Tenant admins can still access tenant-wide rows when expected.

Tests can install a small provider with `configure_data_access_filter_provider(...)` and reset it to `TenantOnlyDataAccessFilterProvider()` in `tearDown`.

## New Module Checklist

1. Add `owner_user_id` and `owner_department_id` to all protected business tables in sqlite, postgres, and mysql DDL.
2. Add useful indexes, usually `(tenant_id, owner_department_id, deleted)` and existing business lookup indexes.
3. Register the resource descriptor in authorization seed data.
4. Declare `ResourceDescriptor` in the module application layer.
5. Use `data_access_for(current_user, RESOURCE).read()` for list/detail reads.
6. Use `.write()` for updates and `.manage()` for destructive or operational actions.
7. Stamp new rows with `data_owner_fields(current_user)`.
8. Apply repository SQL with `apply_data_access(...)`.
9. Add scoped detail or record guards before every mutation.
10. Run explicit init scripts and backend tests before shipping.
