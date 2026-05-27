# 数据权限接入指南

数据权限是 `system` 提供的共享能力。业务模块接入时，应在应用服务层选择动作语义，在仓储层把数据权限谓词合入 SQL，不要在路由中拼权限条件，也不要绕过统一能力直接读取授权上下文。

当前资源配置支持两种归属模式：

- `owner_columns`：业务主表直接包含租户、用户、部门等归属字段。
- `relation_table`：业务主表不直接保存归属关系，归属关系由一张关系表维护。

## 资源归属字段

### owner_columns

`owner_columns` 适合大多数业务表。推荐业务表包含这些字段：

```sql
tenant_id BIGINT NOT NULL
owner_user_id BIGINT DEFAULT NULL
owner_department_id BIGINT DEFAULT NULL
creator_id BIGINT DEFAULT NULL
deleted BOOLEAN/INTEGER NOT NULL DEFAULT 0
```

资源配置字段含义：

- `tenant_column`：主表租户字段，默认 `tenant_id`。
- `creator_column`：主表创建人字段，默认 `creator_id`。
- `owner_user_column`：主表用户归属字段，默认 `owner_user_id`。
- `owner_department_column`：主表部门归属字段，默认 `owner_department_id`。

默认范围映射：

- `tenant`：当前租户内的全部记录。
- `self`：`owner_user_column` 等于当前用户。
- `self_and_subordinates`：`owner_user_column` 在当前用户及下属用户集合中。
- `department`、`department_and_children`、`custom_departments`：`owner_department_column` 在解析出的部门集合中。

### relation_table

`relation_table` 适合资源与用户或部门是多对多关系的场景，例如文档协作者、共享对象、统一访问条目。主表仍需有稳定主键和租户字段，关系表保存资源到用户或部门的归属关系。

资源配置字段含义：

- `relation_table`：关系表名，关系表模式必填。
- `resource_id_column`：资源主表主键字段，默认 `id`。
- `relation_resource_id_column`：关系表中指向资源主表主键的字段，关系表模式必填。
- `relation_user_column`：关系表中指向用户的字段。资源支持 `self` 或 `self_and_subordinates` 时必填。
- `relation_department_column`：关系表中指向部门的字段。资源支持部门范围时必填。
- `relation_tenant_column`：关系表租户字段，默认 `tenant_id`。
- `relation_deleted_column`：关系表软删字段，默认 `deleted`，留空表示不追加软删条件。
- `relation_resource_key_column` / `relation_resource_key_value`：统一 access entries 表可用，用于在同一关系表中区分不同资源类型。
- `relation_subject_type_column` / `relation_subject_type_user_value` / `relation_subject_type_department_value`：关系表区分用户/部门主体类型时使用；填写主体类型字段后，对应类型值也必须配置。
- `tenant_column`：资源主表租户字段，仍用于主表租户约束。

建议关系表也遵循业务表基础字段规范，至少包含 `id`、`tenant_id`、资源外键、用户或部门外键、`deleted`、`create_time` 和审计字段。常用索引：

```sql
CREATE INDEX idx_demo_document_member_tenant_user
  ON demo_document_members (tenant_id, subject_user_id, deleted);

CREATE INDEX idx_demo_document_member_tenant_document
  ON demo_document_members (tenant_id, document_id, deleted);
```

## 注册资源

授权资源由 `authorization` 上下文持久化。新增或修改资源 seed 后，需要显式运行初始化脚本，不允许业务运行时自动迁移、修复或补种。

`owner_columns` 示例：

```sql
SELECT
    resource_key, name, description, access_mode, tenant_column, resource_id_column,
    creator_column, owner_user_column, owner_department_column,
    relation_table, relation_resource_id_column, relation_user_column,
    relation_department_column, relation_tenant_column, relation_deleted_column,
    supported_scopes_json, requires_data_scope
FROM (
    SELECT
        'demo.document' AS resource_key,
        '演示文档' AS name,
        '演示文档数据' AS description,
        'owner_columns' AS access_mode,
        'tenant_id' AS tenant_column,
        'id' AS resource_id_column,
        'creator_id' AS creator_column,
        'owner_user_id' AS owner_user_column,
        'owner_department_id' AS owner_department_column,
        NULL AS relation_table,
        NULL AS relation_resource_id_column,
        NULL AS relation_user_column,
        NULL AS relation_department_column,
        'tenant_id' AS relation_tenant_column,
        'deleted' AS relation_deleted_column,
        '["self","department","department_and_children","custom_departments","tenant"]' AS supported_scopes_json,
        FALSE AS requires_data_scope
) AS seed;
```

`relation_table` 示例：

```sql
SELECT
    resource_key, name, description, access_mode, tenant_column, resource_id_column,
    creator_column, owner_user_column, owner_department_column,
    relation_table, relation_resource_id_column, relation_user_column,
    relation_department_column, relation_tenant_column, relation_deleted_column,
    supported_scopes_json, requires_data_scope
FROM (
    SELECT
        'demo.document' AS resource_key,
        '演示文档' AS name,
        '演示文档成员可访问的数据' AS description,
        'relation_table' AS access_mode,
        'tenant_id' AS tenant_column,
        'id' AS resource_id_column,
        NULL AS creator_column,
        NULL AS owner_user_column,
        NULL AS owner_department_column,
        'demo_document_members' AS relation_table,
        'document_id' AS relation_resource_id_column,
        'subject_user_id' AS relation_user_column,
        'subject_department_id' AS relation_department_column,
        'tenant_id' AS relation_tenant_column,
        'deleted' AS relation_deleted_column,
        '["self","department","department_and_children","tenant"]' AS supported_scopes_json,
        TRUE AS requires_data_scope
) AS seed;
```

初始化命令：

```powershell
python scripts/init_authorization.py
```

如果业务模块也改了自己的 DDL、seed、菜单或权限，继续运行该模块自己的初始化脚本，并验证菜单、权限、资源配置链路。

## 应用服务接入

在业务上下文应用层声明资源：

```python
from system.application.data_access import ResourceDescriptor, data_access_for, data_owner_fields

DOCUMENT_RESOURCE = ResourceDescriptor(resource_key="demo.document")
```

列表、详情、导出、预览使用 `read`：

```python
scope = data_access_for(current_user, DOCUMENT_RESOURCE)
items, total = repo().list_documents(
    tenant_id=current_tenant_id(current_user),
    page=page,
    page_size=page_size,
    data_scope=scope.read(),
)
```

写操作按动作选择范围：

| 操作 | 动作 |
| --- | --- |
| 列表、详情、预览、下载、导出 | `read` |
| 在可访问父对象下创建子记录、更新草稿或可编辑记录 | `write` |
| 删除、发布、启停、触发任务、归档、重建索引、状态流转 | `manage` |

创建记录时用统一 helper 写入归属字段：

```python
payload = {
    **payload,
    **data_owner_fields(current_user),
}
```

`relation_table` 模式下，创建主表记录后还需要由业务上下文显式写入关系表。不要由数据权限运行时隐式创建关系。

## 仓储 SQL 接入

仓储方法接受 `DataAccessPredicate | None`，并调用统一 SQL 注入 helper：

```python
from system.application.data_access import DataAccessPredicate, ResourceDescriptor, apply_data_access

DOCUMENT_RESOURCE = ResourceDescriptor(resource_key="demo.document")


def list_documents(
    *,
    tenant_id: int,
    page: int,
    page_size: int,
    data_scope: DataAccessPredicate | None = None,
) -> tuple[list[Document], int]:
    filters = ["d.tenant_id = ?", "d.deleted = 0"]
    params: list[object] = [tenant_id]
    apply_data_access(filters, params, data_scope=data_scope, resource=DOCUMENT_RESOURCE, alias="d")
    where_sql = " AND ".join(filters)
    ...
```

详情查询也必须接入数据权限：

```python
def get_document_detail(
    *,
    tenant_id: int,
    document_id: int,
    data_scope: DataAccessPredicate | None = None,
) -> Document | None:
    filters = ["d.id = ?", "d.tenant_id = ?", "d.deleted = 0"]
    params: list[object] = [document_id, tenant_id]
    apply_data_access(filters, params, data_scope=data_scope, resource=DOCUMENT_RESOURCE, alias="d")
    ...
```

`apply_data_access` 会避免重复添加已有租户条件。只要 SQL 中使用了表别名，就必须传入 `alias`。

## SQLGlot AST 动态 SQL 注入

复杂查询、动态 SQL、报表查询和 Page Designer 数据源不能靠字符串拼接注入权限条件。应使用 SQLGlot 解析 SQL AST，在最外层查询和需要保护的资源表上注入数据权限谓词。

接入原则：

1. 先用 SQLGlot 解析 SQL，拒绝解析失败、非查询语句、危险语句或多语句输入。
2. 识别资源主表、别名和租户字段；无法唯一识别时要求调用方传入资源 key 与主表别名。
3. 对 `owner_columns` 注入主表字段谓词。
4. 对 `relation_table` 注入 `EXISTS` 子查询，子查询约束关系表租户、资源外键、用户或部门集合。
5. 参数必须走绑定变量，不能把用户 id、部门 id、租户 id 拼进 SQL 文本。
6. 注入后再由 SQLGlot 序列化 SQL，保持分页、排序、limit/offset 由原查询或仓储层控制。

`relation_table` 的动态注入形态示例：

```sql
EXISTS (
  SELECT 1
  FROM demo_document_members rel
  WHERE rel.tenant_id = d.tenant_id
    AND rel.document_id = d.id
    AND rel.deleted = 0
    AND rel.subject_user_id IN (?, ?, ?)
)
```

动态 SQL 注入必须和列表分页一起验证：权限谓词参与 count SQL 和 items SQL，避免列表总数与当前页数据不一致。

## 前端列表和详情接入

业务列表页必须继续使用 Page Runtime 的后端分页：

- 请求参数使用 `runtimeListParams(state)` 转为 `page` 和 `page_size`。
- 后端响应的 `pagination.total` 传回 `ListPageRuntime` 的 `pagination-total`。
- 页面 rows 只渲染后端当前页数据，不做前端全量拉取和本地切片。
- 筛选条件可以和 `runtimeListParams(state)` 合并，但不能覆盖分页参数。

详情页、编辑页、导出、批量操作和后台触发操作必须分别调用后端已接入数据权限的接口。不要只保护列表接口后，详情或导出继续按 `tenant_id` 读取。

## 写入和管理保护

不要只校验 `tenant_id` 后直接更新或删除。应通过带数据权限的详情查询加载目标，或在仓储返回原始行后调用统一记录级 guard。

```python
existing = repo().get_document_detail(
    tenant_id=tenant_id,
    document_id=document_id,
    data_scope=data_access_for(current_user, DOCUMENT_RESOURCE).write(),
)
if not existing:
    raise DocumentNotFoundError("document not found")
```

不可访问的记录建议返回 not found 领域错误，避免泄露其他用户或其他部门记录是否存在。

## 完整中性示例

测试或新 bounded context 可以用下面的中性结构理解接入方式。示例只表达平台能力，不代表平台内置业务表。

```sql
CREATE TABLE demo_documents (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    owner_user_id BIGINT DEFAULT NULL,
    owner_department_id BIGINT DEFAULT NULL,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    title VARCHAR(200) NOT NULL
);

CREATE TABLE demo_document_members (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    document_id BIGINT NOT NULL,
    subject_user_id BIGINT DEFAULT NULL,
    subject_department_id BIGINT DEFAULT NULL,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_demo_document_members_user
    ON demo_document_members (tenant_id, subject_user_id, deleted);

CREATE INDEX idx_demo_document_members_department
    ON demo_document_members (tenant_id, subject_department_id, deleted);
```

资源配置：

```text
resource_key = demo.document
access_mode = relation_table
tenant_column = tenant_id
resource_id_column = id
relation_table = demo_document_members
relation_resource_id_column = document_id
relation_user_column = subject_user_id
relation_department_column = subject_department_id
relation_tenant_column = tenant_id
relation_deleted_column = deleted
```

列表接口：

```python
filters = ["d.deleted = 0"]
params: list[object] = []
apply_data_access(filters, params, data_scope=data_scope, resource=DOCUMENT_RESOURCE, alias="d")
where_sql = " AND ".join(filters)
total = conn.execute(f"SELECT COUNT(*) FROM demo_documents d WHERE {where_sql}", params).fetchone()[0]
items = conn.execute(
    f"SELECT d.id, d.title FROM demo_documents d WHERE {where_sql} ORDER BY d.id LIMIT ? OFFSET ?",
    [*params, page_size, offset],
).fetchall()
```

详情接口：

```python
filters = ["d.id = ?", "d.deleted = 0"]
params: list[object] = [document_id]
apply_data_access(filters, params, data_scope=data_scope, resource=DOCUMENT_RESOURCE, alias="d")
row = conn.execute(
    f"SELECT d.id, d.title FROM demo_documents d WHERE {' AND '.join(filters)}",
    params,
).fetchone()
```

同一个 `data_scope`、同一个 `DOCUMENT_RESOURCE`、同一个 `apply_data_access` 机制同时用于 count、items 和 detail，才能保证列表可见与详情可见一致。

## 导入、树、选项和聚合

导入、树、选项、聚合接口都需要明确决策：

- 暴露业务行数据：应用数据权限。
- 暴露租户级系统参考数据：保留租户过滤，并在代码或文档中说明为什么不应用资源级数据权限。
- 更新已有业务行：逐行检查 `write` 或 `manage` 权限后再修改。

不要假设列表接口已经受控，其他读写入口就天然安全。

## 排查清单

1. 页面看不到数据：确认当前用户已进入租户上下文，资源 key 与后端 `ResourceDescriptor` 一致。
2. 列表总数不对：确认 count SQL 和 items SQL 都注入了同一份数据权限谓词。
3. `self` 范围为空：检查 `owner_columns.owner_user_column` 或 `relation_table.relation_user_column` 是否配置正确。
4. 部门范围为空：检查用户主部门、部门树、`owner_department_column` 或 `relation_department_column`。
5. 关系表模式无效：检查 `relation_table`、`relation_resource_id_column`、关系表租户字段和 `deleted` 条件。
6. 动态 SQL 注入失败：先确认 SQLGlot 能解析原 SQL，再确认资源表别名是否唯一。
7. 翻页丢数据或重复：确认前端使用 Page Runtime 后端分页，后端排序字段稳定，并且权限谓词参与分页前的过滤。
8. 保存资源配置后未生效：确认授权 seed 或配置已初始化到当前开发数据库，运行时不会自动补种。

## 测试要求

接入数据权限的模块至少补充这些回归测试：

1. `self` 范围列表只返回本人归属数据。
2. 详情读取无法加载其他用户记录。
3. `write` 无法更新无权记录。
4. `manage` 无法删除、发布、启停、触发、归档或重建无权记录。
5. `relation_table` 模式下，关系表存在匹配关系才可读取。
6. 租户管理员在预期场景下仍可访问租户范围数据。

测试可安装小型 data access provider，并在 `tearDown` 中恢复为默认 provider。
