# Appearance Studio 多租户影响记录

状态：已确认

## 背景

当前项目已经实现多租户能力。Appearance Studio 的 UI Token 改造必须从第一阶段开始考虑租户隔离，避免后续实现中出现跨租户主题污染。

已确认的多租户入口：

- 后端租户上下文：`system.domain.tenancy.TenantScope`
- 默认租户 key：`system.domain.tenancy.DEFAULT_TENANT_KEY`
- 登录和切换租户：`identity_access.application.tenant_service`
- HTTP 认证依赖会将当前租户写入 request scope：`identity_access.interfaces.http.dependencies`
- 前端用户状态包含 `current_tenant`、`tenant_memberships`、`is_platform_admin`：`web/admin/src/store/modules/user.ts`
- 前端 `switchTenant` 会刷新 token、用户信息、动态路由和 tabs：`web/admin/src/store/modules/user.ts`

## 核心结论

UI Token 改造不会天然破坏多租户，但 Appearance Store、localStorage、导入导出、后续后端持久化都必须支持租户维度。

第一阶段即使只做前端本地闭环，也必须做到 tenant-aware。否则用户在租户 A 设置的主题可能在租户 B 生效，造成租户品牌和配置污染。

## 配置层级

推荐长期配置层级：

```txt
system default preset
  -> tenant appearance
  -> user personal override
  -> current session draft
```

优先级：

```txt
current session draft > user personal override > tenant appearance > system default preset
```

第一阶段可以只实现：

```txt
system default preset
  -> tenant-scoped local user override
```

但数据结构和 storage key 必须为后续租户级持久化留出空间。

## 第一阶段必须遵守的约束

### 1. localStorage key 必须带租户和用户

禁止使用全局 key：

```txt
naive-ui-admin:appearance
```

建议使用：

```txt
naive-ui-admin:appearance:{tenantKey}:{username}
```

如果 `tenantKey` 不存在，fallback：

```txt
naive-ui-admin:appearance:default:{username}
```

如果 `username` 不存在，fallback：

```txt
naive-ui-admin:appearance:{tenantKey}:anonymous
```

### 2. appearanceStore 必须感知当前租户

`appearanceStore` 需要从 `userStore.info.current_tenant` 读取：

- `tenant_id`
- `tenant_key`
- `name`

并提供计算属性：

- `currentTenantKey`
- `currentUsername`
- `storageKey`

### 3. 切换租户后必须重新加载 appearance

`userStore.switchTenant` 完成后，必须触发 appearance 重新加载。

推荐行为：

- 清理当前 session draft。
- 根据新租户和当前用户计算新的 storage key。
- 从 tenant-scoped localStorage 加载 appearance。
- 如果没有配置，则使用系统默认 preset。

不能沿用切换前租户的 themeOverrides、cssVars、layoutConfig。

### 4. 导入导出 JSON 不应隐式跨租户生效

`exportAppearanceJSON` 可以导出完整 appearance 配置，但不应在导入时自动写入所有租户。

导入行为必须明确：

- 导入到当前租户当前用户的本地配置。
- 后续如果支持租户级保存，则由租户管理员显式执行“保存为租户主题”。

### 5. Draft 与 Saved 配置要区分

编辑器中正在调整的 token 是 session draft，不应立刻覆盖租户级配置。

第一阶段可以实时预览并写入当前用户当前租户 localStorage。后续租户级保存必须增加明确动作：

- 保存为我的偏好。
- 保存为当前租户主题。
- 重置为租户主题。
- 重置为系统默认。

## 后端持久化建议

第二阶段再引入后端租户级持久化。

建议新增 bounded-context 归属：

- 如果只管理租户品牌与 UI 外观，建议放入 `identity_access` 的租户管理能力下。
- 如果未来扩展为系统级运行时配置，也可以考虑新 bounded context，例如 `appearance`。但第一阶段不建议新建后端上下文。

建议表：

```sql
tenant_appearance_settings (
  tenant_id INTEGER PRIMARY KEY,
  preset_id TEXT NOT NULL,
  tokens_json TEXT NOT NULL,
  layout_json TEXT NOT NULL,
  skin_class TEXT NOT NULL DEFAULT '',
  version INTEGER NOT NULL DEFAULT 1,
  updated_by INTEGER,
  updated_at TEXT NOT NULL
)
```

建议 API：

```txt
GET /appearance/current
PUT /appearance/current
GET /tenants/{tenant_id}/appearance
PUT /tenants/{tenant_id}/appearance
```

权限建议：

- 当前租户用户：可读取当前租户 appearance。
- 租户管理员：可更新当前租户 appearance。
- 平台管理员：可管理任意租户 appearance。
- 普通用户个人覆盖是否允许，单独做产品决策。

API 响应必须遵守统一 envelope。

## 对现有 Task 的影响

### 影响 Task 5.1 appearance store

必须新增：

- tenant-aware storage key。
- 当前租户信息读取。
- 切换租户后的 reload 方法。

### 影响 Task 5.2 localStorage 持久化

必须改为租户隔离 key，禁止全局 key。

### 影响 Task 5.3 designSettingStore 关系

迁移主色时要避免旧 `appTheme` 成为跨租户全局状态。

### 影响 Task 6.1 App.vue 接入

App 接入不能只在应用启动时读取一次 appearance。登录、获取用户信息、切换租户后都要能重新计算当前 appearance。

### 影响 Task 7.8 ImportExportPanel

导入导出面板需要明确当前租户上下文，避免用户误以为导入会影响所有租户。

## 验收补充

多租户相关验收必须包括：

- 用户在租户 A 选择 `primevue-like`，切换到租户 B 后不沿用租户 A 的本地配置。
- 用户切回租户 A 后恢复租户 A 的本地配置。
- localStorage 中不同租户使用不同 key。
- logout 后不泄漏上一个用户的 appearance 到新用户。
- 导入 appearance JSON 只影响当前租户当前用户，除非后续明确执行“保存为租户主题”。

## 实现警示

Appearance Studio 后续所有实现任务都要检查是否使用了全局 appearance 状态。凡是涉及持久化、初始化、导入、导出、切换租户、重置配置的逻辑，都必须显式考虑当前租户。
