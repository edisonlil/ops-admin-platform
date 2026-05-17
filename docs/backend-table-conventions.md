# 后端建表规范

## 基础字段

所有后端业务表必须使用单列 `id` 主键，并包含以下基础字段：

```sql
id           BIGINT/INTEGER PRIMARY KEY
tenant_id    BIGINT/INTEGER NOT NULL
lock_version BIGINT/INTEGER NOT NULL DEFAULT 0
deleted      BOOLEAN/INTEGER NOT NULL DEFAULT 0
create_time  TEXT/DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
creator      TEXT/VARCHAR(64) DEFAULT NULL
creator_id   BIGINT/INTEGER DEFAULT NULL
update_time  TEXT/DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
editor       TEXT/VARCHAR(64) DEFAULT NULL
editor_id    BIGINT/INTEGER DEFAULT NULL
```

`create_time/update_time` 是唯一标准时间字段；不要再新增或返回 `created_at/updated_at`。

## 租户字段

`tenant_id` 必须非空。租户级业务数据写入当前租户 ID，平台级或全局配置数据归属租户模块中的 platform tenant。

查询业务数据时默认按当前租户过滤；确实需要跨租户读取的管理能力，必须在应用服务中显式说明授权边界。

## 审计与版本

新增数据时统一初始化 `create_time/creator/creator_id/update_time/editor/editor_id`，更新数据时统一刷新 `update_time/editor/editor_id` 并递增 `lock_version`。

系统初始化、seed、后台任务等没有用户主体的写入可以使用 `creator/editor='system'`，`creator_id/editor_id` 可为空。

## 逻辑删除

逻辑删除统一使用 `deleted` 字段。删除时设置 `deleted=1`，并更新 `update_time/editor/editor_id`；不额外增加 `delete_time/deleter/deleter_id`。

业务查询默认只读取 `deleted=0` 数据。物理删除只允许用于内部关系重建或初始化清理，不作为业务删除接口语义。

## 关联表

关联表也必须有 `id` 单主键。业务关系唯一性用组合唯一索引表达，例如：

```sql
UNIQUE (tenant_id, user_id, role_id)
```

`tenant_memberships`、`user_roles`、`role_permissions`、`role_menus` 均遵循该规则。

关系关联表默认使用物理删除，适用于角色授权、菜单授权、配置项成员等只表达“当前关系集合”的中间表。编辑关系集合时可先删除旧关系再写入新关系，历史审计应由业务操作日志或上层实体承担。

只有具备审计、恢复、权限追溯价值的关系表允许使用逻辑删除，例如用户部门归属、数据权限策略。逻辑删除关系表必须增加可空的 `active_marker` 字段：

```sql
active_marker INTEGER DEFAULT 1
```

当前有效关系写入 `active_marker=1`，逻辑删除时同时设置 `deleted=1, active_marker=NULL`。这类表的业务唯一索引必须使用 `active_marker` 表达“当前有效唯一性”，禁止使用 `UNIQUE (..., deleted)`，例如：

```sql
UNIQUE (tenant_id, user_id, department_id, active_marker)
```

需要恢复历史关系时应插入新的当前有效行，保留旧逻辑删除行作为历史记录。
