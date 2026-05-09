# Appearance Studio 任务拆分

## Milestone 0：准备与边界确认

### Task 0.1 确认范围和验收标准

状态：已完成

产出文档：`docs/appearance-studio/task-0.1-scope-and-acceptance.md`

- 明确 Appearance Studio 不是低代码平台。
- 明确第一阶段只覆盖后台壳层和盘点后确认的高频组件。
- 确认第一批 preset：`default`、`primevue-like`、`compact-enterprise`。
- 第一批组件不在本任务中拍板；已由 Task 0.3 的覆盖矩阵和 Task 0.4 的范围决策确认。

产出：

- 范围说明。
- 第一阶段验收标准。

### Task 0.2 梳理现有主题与布局入口

状态：已完成

产出文档：`docs/appearance-studio/task-0.2-theme-layout-entrypoints.md`

- 阅读 `web/admin/src/App.vue` 的 `NConfigProvider` 接入。
- 阅读 `web/admin/src/store/modules/designSetting.ts`。
- 阅读 `web/admin/src/store/modules/projectSetting.ts`。
- 阅读 `web/admin/src/layout/index.vue`、Header、Menu、TabsView 的样式入口。
- 标记当前硬编码颜色、间距、高度、宽度、阴影位置。

产出：

- 现有入口清单。
- 需要替换为 CSS variables 的样式清单。

### Task 0.3 盘点现有 UI 组件使用情况

状态：已完成

产出文档：`docs/appearance-studio/appearance-component-audit.md`

目标：

- 先看清楚项目实际用了哪些 Naive UI 组件、业务封装组件和布局组件，再决定第一阶段覆盖范围。
- 避免只覆盖 Button、Input、Table 这类显眼组件，遗漏实际页面中高频出现的 Select、Tree、Upload、Pagination、Drawer、Dropdown 等组件。

盘点范围：

- `web/admin/src/layout`
- `web/admin/src/components`
- `web/admin/src/views`
- `web/admin/src/plugins/naive.ts`
- 表单、表格、弹窗、上传等二次封装组件。

盘点维度：

- 组件名称。
- 使用次数。
- 出现位置。
- 是否是 Naive UI 原生组件。
- 是否是项目二次封装组件。
- 是否影响主要视觉风格。
- 是否已有 themeOverrides 可覆盖。
- 是否需要 CSS variables 或 skin class 兜底。

建议输出格式：

```md
| 组件 | 使用次数 | 典型位置 | 视觉影响 | 覆盖方式 | MVP |
| --- | ---: | --- | --- | --- | --- |
| NButton | 42 | 表格操作、表单提交 | 高 | themeOverrides | 是 |
| NDataTable | 18 | 列表页 | 高 | themeOverrides + density | 是 |
| NDrawer | 9 | 设置面板、创建表单 | 中 | themeOverrides | 待定 |
```

产出：

- `docs/appearance-component-audit.md`
- 组件使用清单。
- 组件覆盖矩阵。
- 第一阶段候选组件列表。

验收：

- 第一阶段组件范围必须来自覆盖矩阵，而不是预设假设。
- 覆盖矩阵能说明每个组件为什么进入或暂不进入 MVP。

### Task 0.4 确认第一阶段组件覆盖范围

状态：已完成

产出文档：`docs/appearance-studio/task-0.4-mvp-component-scope.md`

前置：

- 必须完成 Task 0.3。

决策规则：

- 高频出现且影响整体 UI 气质的组件优先。
- 后台壳层组件优先，例如 Menu、Tabs、Layout、Card、DataTable。
- 表单链路组件优先，例如 Input、Select、Form、Button。
- 低频但视觉存在感强的组件进入候选，例如 Modal、Drawer、Upload。
- 很少使用或不影响风格的组件延后。

产出：

- 第一阶段必做组件列表。
- 第一阶段候选组件列表。
- 第二阶段延后组件列表。

验收：

- Task 1.4、Task 4.1、Task 7.5 的组件范围以本任务产出为准。

## Milestone 1：Token 基础设施

### Task 1.1 定义 Appearance 类型

新增：

- `web/admin/src/appearance/types.ts`

定义：

- `PrimitiveTokens`
- `SemanticTokens`
- `ComponentTokens`
- `LayoutTokens`
- `AppearanceTokens`
- `AppearancePreset`
- `ResolvedAppearance`
- `TokenValidationError`

验收：

- 类型能表达三层 token。
- Component token 不直接强绑定 Naive UI 全量字段。

### Task 1.2 定义默认 Primitive Token

新增：

- `web/admin/src/appearance/tokens/primitive.ts`

包含：

- 品牌色阶。
- 灰阶。
- 成功、警告、错误、信息色。
- 字号。
- 圆角。
- 间距。
- 阴影。
- 边框基础值。

验收：

- 能支撑 default preset 和 primevue-like preset。

### Task 1.3 定义默认 Semantic Token

新增：

- `web/admin/src/appearance/tokens/semantic.ts`

包含：

- `primaryColor`
- `successColor`
- `warningColor`
- `errorColor`
- `infoColor`
- `textColorBase`
- `textColorSecondary`
- `pageBgColor`
- `surfaceColor`
- `borderColorBase`
- `borderRadiusBase`
- `fontSizeBase`

验收：

- Semantic token 使用 `{tokenName}` 引用 Primitive。

### Task 1.4 定义默认 Component Token

新增：

- `web/admin/src/appearance/tokens/component.ts`

覆盖范围：

- 以 Task 0.4 输出的第一阶段必做组件列表为准。
- 默认至少需要覆盖后台壳层组件、表单链路组件、列表页高频组件。
- 未进入第一阶段的组件需要在文件中保留扩展位，而不是临时散落新增。

验收：

- 每个组件至少具备颜色、圆角、边框或密度相关 token。
- Component token 范围能追溯到 `docs/appearance-component-audit.md` 的覆盖矩阵。

### Task 1.5 定义 Layout Token

新增：

- `web/admin/src/appearance/tokens/layout.ts`

包含：

- `density`
- `headerHeight`
- `menuWidth`
- `collapsedMenuWidth`
- `contentPadding`
- `pageMaxWidth`
- `cardStyle`
- `tableDensity`

验收：

- 能覆盖现有 `projectSetting` 中主要外观参数。

## Milestone 2：Resolver 与校验

### Task 2.1 实现 token resolver

新增：

- `web/admin/src/appearance/resolver.ts`

能力：

- 解析 `{tokenName}`。
- 递归解析对象。
- 支持 Primitive、Semantic、Component、Layout 多层引用。
- 检测循环引用。
- 找不到引用时返回错误。

验收：

- `{primaryColor}` 能解析到真实 hex。
- `Button.primaryBg = '{primaryColor}'` 能解析到真实 hex。
- 循环引用不会导致页面崩溃。

### Task 2.2 实现 validators

新增：

- `web/admin/src/appearance/validators.ts`

校验：

- hex 色值。
- px/rem 数值。
- 数字范围。
- 枚举值。
- 空值。

验收：

- 非法输入能被识别。
- 校验错误可供 UI 展示。

### Task 2.3 为 resolver 增加单元测试

新增或扩展前端测试配置。

测试场景：

- 正常引用。
- 嵌套引用。
- 缺失 token。
- 循环引用。
- Component token 引用 Semantic token。

验收：

- resolver 行为稳定。

## Milestone 3：Preset 系统

### Task 3.1 实现 default preset

新增：

- `web/admin/src/appearance/presets/default.ts`

目标：

- 尽量保持当前 Naive UI Admin 风格。
- 初始品牌色兼容当前 `designSetting.appTheme`。

验收：

- 应用 default preset 后视觉不出现明显回退。

### Task 3.2 实现 primevue-like preset

新增：

- `web/admin/src/appearance/presets/primevueLike.ts`

视觉目标：

- 白色 surface。
- 浅灰页面背景。
- 清晰边框。
- 6px 左右中等圆角。
- Button 扁平实色。
- Input focus 主色边框。
- Table 浅灰表头。
- Menu 浅色选中态。

验收：

- 切换后 Button、Input、Table、Menu、Card 明显呈现 PrimeVue-like 气质。

### Task 3.3 实现 compact-enterprise preset

新增：

- `web/admin/src/appearance/presets/compact.ts`

视觉目标：

- 紧凑高度。
- 小圆角。
- 弱阴影。
- 表格和表单密度更高。

验收：

- 适合高频后台操作页面。

### Task 3.4 实现 preset registry

新增：

- `web/admin/src/appearance/presets/index.ts`

能力：

- 导出 preset list。
- 按 id 获取 preset。
- fallback 到 default。

验收：

- store 能通过 preset id 获取完整 tokens。

## Milestone 4：Adapter 输出

### Task 4.1 实现 naiveAdapter

新增：

- `web/admin/src/appearance/naiveAdapter.ts`

输出：

- `GlobalThemeOverrides`

覆盖：

- `common` 必须覆盖。
- 组件覆盖范围以 Task 0.4 输出的第一阶段必做组件列表为准。
- `LoadingBar` 作为全局反馈组件建议第一阶段覆盖。
- 未进入第一阶段的组件需要登记到覆盖矩阵的延后列表。

验收：

- 修改 `primaryColor` 后，第一阶段必做组件中的主色相关状态同步变化。
- 修改 `borderRadiusBase` 后，第一阶段必做组件中的圆角相关状态同步变化。
- adapter 覆盖项能追溯到 `docs/appearance-component-audit.md` 的覆盖矩阵。

### Task 4.2 实现 cssVarAdapter

新增：

- `web/admin/src/appearance/cssVarAdapter.ts`

输出：

- Vue 可绑定 style object。

包含：

- `--app-page-bg`
- `--app-surface-bg`
- `--app-content-padding`
- `--app-header-height`
- `--app-menu-width`
- `--app-collapsed-menu-width`
- `--app-border-color`
- `--app-card-radius`
- `--app-shadow-sm`

验收：

- 根节点绑定后 CSS variables 可在页面样式中使用。

### Task 4.3 实现 layoutAdapter

新增：

- `web/admin/src/appearance/layoutAdapter.ts`

能力：

- 将 layout token 转成 layout 组件可消费的数据。
- 桥接现有 `projectSettingStore`。

验收：

- menuWidth、headerHeight、contentPadding 能被 layout 消费。

### Task 4.4 为 adapter 增加测试

测试：

- default preset 输出合法 `GlobalThemeOverrides`。
- primevue-like 输出包含关键组件覆盖。
- css variables 输出格式正确。

验收：

- adapter 输出稳定。

## Milestone 5：Pinia Store

### Task 5.1 实现 appearance store

新增：

- `web/admin/src/store/modules/appearance.ts`

状态：

- `version`
- `presetId`
- `tokenOverrides`
- `layoutOverrides`
- `skinClass`

getter：

- `activePreset`
- `mergedTokens`
- `resolvedTokens`
- `themeOverrides`
- `cssVars`
- `layoutConfig`
- `validationErrors`

action：

- `applyPreset`
- `updatePrimitiveToken`
- `updateSemanticToken`
- `updateComponentToken`
- `updateLayoutToken`
- `resetToPreset`
- `resetAll`
- `exportThemeOverridesJSON`
- `exportAppearanceJSON`
- `importAppearanceJSON`

多租户要求：

- 从 `userStore.info.current_tenant` 读取当前租户。
- 提供 `currentTenantKey`、`currentUsername`、`storageKey`。
- 提供 `reloadForCurrentTenant()` 或等价方法，供租户切换后调用。
- 禁止使用全局 appearance 状态污染不同租户。
- 详细要求见 `docs/appearance-studio/multi-tenant-impact.md`。

验收：

- store 能独立完成 preset 切换、token 更新、导入导出。
- 同一用户切换租户后能加载对应租户的 appearance 配置。

### Task 5.2 实现 localStorage 持久化

存储 key：

- `naive-ui-admin:appearance:{tenantKey}:{username}`

存储内容：

- preset id。
- 用户 overrides。
- version。

验收：

- 刷新后恢复当前风格。
- 旧 version 数据有 fallback。
- 不同租户使用不同 localStorage key。
- logout 后不泄漏上一个用户的 appearance 到新用户。

### Task 5.3 处理与 designSettingStore 的关系

策略：

- 第一阶段保留 `darkTheme`。
- `appTheme` 逐步迁移为 `semantic.primaryColor`。
- 避免 `App.vue` 同时从两个 store 计算 theme overrides。

验收：

- 主题主色只有一个最终来源。
- 现有项目配置抽屉不破坏。

## Milestone 6：App 与布局接入

### Task 6.1 接入 App.vue

修改：

- `web/admin/src/App.vue`

目标：

- `NConfigProvider.themeOverrides` 使用 `appearanceStore.themeOverrides`。
- 根容器绑定 `appearanceStore.cssVars`。
- 根容器绑定 `appearanceStore.skinClass`。
- 保留锁屏逻辑和暗色主题逻辑。

验收：

- 应用启动正常。
- 切换 token 后实时预览。
- 登录、获取用户信息、切换租户后 appearance 能按当前租户重新计算。

### Task 6.2 改造 layout CSS variables

修改：

- `web/admin/src/layout/index.vue`
- Header 相关组件。
- Menu 相关组件。
- TabsView 相关组件。

目标：

- 替换硬编码背景、间距、高度、宽度、阴影。

验收：

- content padding、menu width、page background 能由 token 控制。

### Task 6.3 增加 skin class 兜底样式

新增：

- `web/admin/src/styles/skins/primevue-like.less`
- `web/admin/src/styles/skins/index.less`

目标：

- 只处理 Naive token 和 CSS variables 难以表达的少量差异。

验收：

- 不出现大量脆弱深层选择器。

## Milestone 7：Appearance Studio UI

本里程碑后续实现必须遵守 `docs/appearance-studio-plan.md` 的“10. 编辑器交互设计”规范：

- 工作台采用“左侧层级导航 + 中间单对象配置页 + 右侧最终效果预览”。
- 左侧一级层级暂定为 `全局样式`、`组件样式`、`界面布局`、`导入导出`。
- 组件样式必须按具体组件拆页，不能把按钮、表单、表格、状态、壳层全部折叠在同一个配置面板里。
- 预览区必须跟当前配置对象一致。设置字体就看字体，设置按钮就看按钮，设置布局就看布局示意。
- 预览区是主视觉判断区，应比单个配置列更宽，减少说明性边框和卡片套卡片。

### Task 7.1 新建 AppearanceStudio 容器

新增：

- `web/admin/src/components/AppearanceStudio/index.vue`

能力：

- 浮动按钮打开 `NDrawer`。
- 使用 `NTabs` 分组。
- 展示 validation errors。

验收：

- 可以打开/关闭编辑器。

### Task 7.2 实现 PresetPanel

新增：

- `PresetPanel.vue`

能力：

- 展示 preset list。
- 切换 preset。
- 重置到当前 preset。

验收：

- 切换 preset 后实时生效。

### Task 7.3 实现 Colors 面板

新增：

- `PrimitivePanel.vue`
- `SemanticPanel.vue`
- `TokenColorRow.vue`

能力：

- `input type="color"` + `NInput` 双向同步。
- 编辑 primitive 和 semantic 颜色。
- 显示引用值和解析值。

验收：

- 修改 primaryColor 后重点组件同步变化。

### Task 7.4 实现 Radius、Shadow、Typography 面板

新增或扩展：

- `TokenNumberRow.vue`
- `TokenSelectRow.vue`

能力：

- 编辑圆角、字号、阴影、间距。

验收：

- 修改圆角和字号后 Button、Input、Card 等组件同步变化。

### Task 7.5 实现 ComponentPanel

新增：

- `ComponentPanel.vue`

优先组件：

- 以 Task 0.4 输出的第一阶段必做组件列表为准。
- UI 面板按覆盖矩阵中的视觉影响级别排序。
- 高频但暂不支持编辑的组件需要在面板中标注为后续扩展项，避免范围不透明。

验收：

- 能独立调整重点组件的外观字段。
- 面板中的组件范围与覆盖矩阵一致。

### Task 7.6 实现 LayoutPanel

新增：

- `LayoutPanel.vue`

能力：

- 调整 density。
- 调整 menu width。
- 调整 header height。
- 调整 content padding。
- 调整 page max width。
- 调整 card style。

验收：

- 后台壳层布局外观实时变化。

### Task 7.7 实现 PreviewPanel

新增：

- `PreviewPanel.vue`

展示：

- Button variants。
- Input / Select。
- Table sample。
- Card。
- Tag。
- Tabs。
- Menu sample。

验收：

- 用户无需跳转业务页面也能预览主要效果。

### Task 7.8 实现 ImportExportPanel

新增：

- `ImportExportPanel.vue`

能力：

- 导出 `GlobalThemeOverrides JSON`。
- 导出完整 `Appearance JSON`。
- 导入 `Appearance JSON`。
- 一键复制。
- 一键重置。
- 展示当前租户上下文。
- 明确导入只影响当前租户当前用户的本地配置。

验收：

- 导出的 `themeOverrides` 可直接给 `NConfigProvider`。
- 导出的 appearance JSON 可再次导入恢复。
- 导入 appearance JSON 不会影响其他租户。

## Milestone 8：验证与质量

### Task 8.1 前端构建验证

命令：

```bash
cd web/admin
pnpm run build
```

验收：

- 构建通过。

### Task 8.2 浏览器人工验证

验证：

- default preset。
- primevue-like preset。
- compact-enterprise preset。
- 刷新恢复。
- 导入导出。
- 暗色主题。
- 移动端 layout。

验收：

- 无明显布局错乱。
- 无明显文字溢出。
- 无控制台关键错误。

### Task 8.3 回归现有 ProjectSetting

验证：

- 导航模式切换。
- 暗色主题切换。
- 菜单折叠。
- Tabs 显示隐藏。
- 面包屑显示隐藏。

验收：

- 现有项目配置功能不被破坏。

### Task 8.4 补充文档

新增或更新：

- `web/admin/src/appearance/README.md`

内容：

- token 模型。
- preset 编写方式。
- adapter 扩展方式。
- 如何新增组件 token。
- 如何新增 skin。

验收：

- 后续维护者能按文档扩展新风格。

## Milestone 9：组件级外观设计二期

目标：

- 将 Appearance Studio 从基础主题变量扩展为组件级设计系统。
- 优先完善后台高频业务组件，尤其是表格、状态、操作按钮、筛选区和批量操作。
- 通过稳定 token 与共享组件承载外观能力，避免页面直接写散落样式或任意 CSS。

### 当前已 Token 化组件

状态：阶段性完成

| 组件 / 模式 | 覆盖状态 | 说明 |
| --- | --- | --- |
| Button | 已覆盖 | 支持主要、默认、弱按钮等基础变量。 |
| Form | 部分覆盖 | 已有基础字段密度与控件外观，复杂筛选表单待补。 |
| Input / InputNumber | 已覆盖基础项 | 覆盖边框、背景、字号、圆角等基础项。 |
| Select | 已覆盖基础项 | 基础控件已覆盖，下拉面板联动仍需和弹层 token 统一。 |
| Switch / Checkbox / Radio | 已覆盖基础项 | 常规状态已覆盖，复杂尺寸和禁用态可继续补齐。 |
| DataTable | 已完成第一阶段 | 表头、行、边框、斑马纹、hover、选中、密度等已进入 Appearance Studio。 |
| StatusTag | 已完成第一阶段 | 已抽取状态标签 token，并迁移部分业务状态显示。 |
| TableAction | 已完成第一阶段 | 已抽取表格操作按钮 token，并迁移部分表格操作列。 |
| Pagination | 部分覆盖 | 基础 PrimeVue 映射已有，业务分页布局和对齐待统一。 |
| Dropdown | 已覆盖基础项 | 菜单项和浮层表现仍需和 Popover / Menu token 对齐。 |
| Tag | 已覆盖基础项 | 普通 Tag 已覆盖，语义状态 Tag 已由 StatusTag 承载。 |
| Card | 已覆盖基础项 | 主题卡片已接入 Appearance Studio，通用业务卡片仍需规范迁移。 |
| Modal / Drawer | 已覆盖基础项 | 基础变量已覆盖，复杂页脚、表单布局和暗色细节可继续补。 |
| Menu | 已覆盖核心项 | 侧边栏亮色 / 深色菜单已接入主题变量。 |
| Tooltip | 已覆盖基础项 | 复杂 Popover / Popconfirm 还未进入组件级 token。 |
| LoadingBar | 已覆盖基础项 | 顶部加载条已接入基础主题色。 |

### 当前未完整 Token 化组件清单

状态：待规划实施

| 组件 / 模式 | 当前缺口 | 建议优先级 | 建议方案 |
| --- | --- | --- | --- |
| TableToolbar / SearchForm / FilterBar | 查询区、筛选区、按钮组、折叠筛选没有统一外观入口。 | 高 | 抽取 `TableToolbarTokens`、`TableSearchTokens`，并提供 `AppTableToolbar`。 |
| DataTable 扩展状态 | 固定列阴影、空状态、加载态、展开行、批量操作栏还未完整 token 化。 | 高 | 扩展 `DataTableTokens`，沉淀 `AppDataTable` 作为业务表格入口。 |
| Table 选择列 | 勾选列宽度、选择态、批量栏联动还不完整。 | 高 | 将 selection column 与 batch action bar 纳入表格 token。 |
| Table 操作列 | 操作按钮组已完成第一阶段，但确认操作、危险操作、更多菜单还需统一。 | 高 | 扩展 `TableActionTokens`，增加 `AppConfirmAction` 和更多操作变体。 |
| DatePicker / TimePicker / RangePicker | 输入框和弹出面板尚未进入组件编辑面板。 | 高 | 基于 PrimeVue themeOverrides + popup token 抽取时间选择类变量。 |
| Upload / BasicUpload | 拖拽区、文件列表、进度、错误状态没有外观入口。 | 高 | 抽取 Upload 组件 token，覆盖 dropzone、file item、progress、error。 |
| Tree / TreeSelect | 节点高度、缩进、hover、选中、展开图标、线条未统一。 | 高 | Tree 与 TreeSelect 共享 Tree tokens，TreeSelect 额外复用 Select tokens。 |
| Tabs | 页签高度、激活线、间距、卡片式 tabs 未完整覆盖。 | 中高 | 抽取 Tabs tokens，并迁移多页签和内容区 tabs 的差异项。 |
| Steps | 步骤点、连接线、完成态、错误态未覆盖。 | 中 | 抽取 Steps tokens，优先服务流程类页面。 |
| Descriptions | label/value 对齐、边框、背景、密度未覆盖。 | 中 | 抽取 Descriptions tokens，统一详情页展示。 |
| Alert / Result / Empty | 反馈类组件样式仍主要依赖默认主题。 | 中 | 抽取反馈组件 tokens，并补齐空状态和结果页预览。 |
| Skeleton / Spin / Progress | 加载与进度样式未进入 Studio。 | 中 | 抽取 LoadingFeedback tokens，统一占位、加载、进度颜色和尺寸。 |
| Badge / Avatar | 小型展示组件未完整覆盖。 | 中低 | 作为展示组件批次处理。 |
| Breadcrumb | 顶栏面包屑目前更多受布局样式影响，未组件化配置。 | 中低 | 纳入导航类 token，和 Header tokens 对齐。 |
| Popover / Popconfirm | 弹层背景、阴影、箭头、按钮区未覆盖。 | 中高 | 抽取 Overlay tokens，与 Tooltip、Dropdown、Select popup 统一。 |
| List / Thing | 列表项、媒体块、分隔线、密度未覆盖。 | 中低 | 在详情与列表类组件阶段处理。 |

### Task 9.1 表格体系二期

状态：进行中

内容：

- 抽取 `TableToolbarTokens`：工具栏高度、背景、边框、内边距、按钮间距、左右区对齐。
- 抽取 `TableSearchTokens`：筛选字段间距、标签宽度、输入宽度、行间距、折叠控制、查询 / 重置按钮样式。
- 扩展 `DataTableTokens`：选择列、固定列阴影、空状态、加载态、展开行、批量操作栏。
- 沉淀 `AppDataTable` 与 `AppTableToolbar`，让新业务表格默认走统一组件。
- Appearance Studio 预览区补充查询栏、勾选列、批量操作栏、空状态、加载态和固定操作列示例。

当前进展：

- 已新增 `TableToolbarTokens`、`TableSearchTokens`、`TableBatchActionTokens`，并扩展 `DataTableTokens` 的选择列、固定列阴影、空状态、加载态、展开行字段。
- 已新增 `AppTableToolbar` 与 `AppDataTable`，作为新业务表格的统一入口。
- 已让旧 `BasicTable` 工具栏消费表格 token 变量，降低历史页面迁移成本。
- Appearance Studio 已新增“表格工具栏”配置页与查询栏、批量栏、选择列预览。
- 已迁移租户管理、成员管理与用户管理页面的主要列表到 `AppDataTable`、`AppStatusTag`、`AppTableActions`。

验收：

- 成员管理、租户管理、角色管理、菜单权限等高频页面可逐步迁移到 `AppDataTable`。
- 表格查询区、表格主体、操作列、状态列可以通过 Appearance Studio 调整。
- 切换亮色 / 暗色主题后，表格、工具栏和批量操作栏不会出现明显对比度问题。

### Task 9.2 状态与操作体系完善

状态：进行中

内容：

- 扩展 `TableActionTokens`，覆盖默认、主要、危险、禁用、更多菜单、图标按钮。
- 新增 `AppConfirmAction`，统一二次确认类操作，如撤销、删除、停用。
- 新增 `AppStatusGroup`，用于多个状态标签并排展示。
- 建立业务状态语义字典，例如 enabled、disabled、draft、published、revoked、matched、pendingReview。

当前进展：

- 已扩展 `TableActionTokens` 的默认、主要、危险、禁用和确认层外观字段。
- 已新增 `AppConfirmAction`，并让 `AppTableActions` 支持确认操作。
- 已将租户停用 / 启用、用户禁用 / 启用、API Key 撤销接入统一确认入口。
- 已新增状态语义字典和 `AppStatusGroup`，支持 enabled、disabled、draft、published、revoked、matched、pendingReview、system、platform、tenant 等业务状态。
- 已迁移角色权限页到 `AppDataTable`、`AppStatusGroup`、`AppTableActions` 与统一删除确认入口。
- Appearance Studio “状态与操作”预览已补充主要、危险和禁用操作按钮状态。

验收：

- 表格操作列不再由页面零散拼接按钮样式。
- 状态标签的语义、颜色和边框可以统一由 Appearance Studio 管理。
- 危险操作在亮色 / 暗色主题下都有明确但不过度刺眼的视觉表达。

### Task 9.3 表单选择类组件

状态：待开始

内容：

- 覆盖 DatePicker、TimePicker、RangePicker、AutoComplete、Cascader、TreeSelect。
- 将输入框外观复用现有 Field tokens。
- 抽取 Popup Panel tokens：弹层背景、边框、阴影、圆角、选中项、hover 项、禁用项。
- Appearance Studio 预览区增加日期范围、时间选择、树选择和级联选择样例。

验收：

- 选择类控件的输入态与弹出面板风格一致。
- 暗色主题下弹层和页面背景边界清晰。
- 页面不需要通过局部 CSS 修补 DatePicker / TreeSelect 的弹层样式。

### Task 9.4 Upload 与 Tree

状态：待开始

内容：

- Upload 覆盖拖拽区、文件列表、上传进度、错误提示、删除按钮、禁用态。
- Tree 覆盖节点高度、缩进、图标大小、hover、selected、expanded、disabled、连接线。
- TreeSelect 复用 Tree tokens，并和 Select / Popup tokens 对齐。

验收：

- 上传组件在普通表单和独立上传区都可以保持统一外观。
- Tree 与 TreeSelect 的节点样式一致。
- 大节点文本、长文件名、错误提示不会破坏布局。

### Task 9.5 反馈与展示组件

状态：待开始

内容：

- 覆盖 Alert、Result、Empty、Skeleton、Spin、Progress。
- 统一 success、warning、danger、info、neutral 等语义状态。
- Appearance Studio 预览区增加空状态、错误状态、加载态和进度态。

验收：

- 空页面、错误页、加载页的颜色、间距、图标区域可由主题管理。
- 暗色主题下反馈组件不会出现低对比度文本或过亮背景。
- 反馈组件可被业务页面复用，不需要页面单独写视觉样式。

### Task 9.6 详情与导航组件

状态：待开始

内容：

- 覆盖 Descriptions、Steps、Tabs、List、Thing、Breadcrumb、Badge、Avatar、Popover、Popconfirm。
- 区分导航型 Tabs、多页签 Tabs、内容区 Tabs 的 token。
- 将 Breadcrumb 与 Header tokens 对齐，避免顶栏局部样式漂移。

验收：

- 详情页、流程页和导航区域的视觉密度可统一配置。
- Popconfirm 的确认区按钮、危险态和浮层边界能随主题切换。
- 多页面使用同类组件时不再出现明显样式漂移。

### Task 9.7 高频页面迁移

状态：待开始

内容：

- 优先迁移成员管理、租户管理、角色管理、菜单权限、模型配置、功能点库等高频后台页面。
- 表格页统一使用 `AppDataTable`、`AppStatusTag`、`AppTableActions`、`AppTableToolbar`。
- 保留页面业务逻辑，减少只为样式存在的局部 CSS。

验收：

- 高频页面在亮色 / 暗色主题、不同租户主题、平台默认主题下视觉一致。
- 页面局部样式减少，新增页面可直接复用组件级 token。
- Appearance Studio 的预览结果与真实业务页面表现基本一致。

## 推荐第一阶段最小闭环

第一阶段建议只做以下任务，形成可演示 MVP：

1. Task 1.1 至 Task 1.5：Token 类型和默认 token。
2. Task 2.1 至 Task 2.2：Resolver 和 validators。
3. Task 3.1 至 Task 3.2：default 和 primevue-like preset。
4. Task 4.1 至 Task 4.2：naiveAdapter 和 cssVarAdapter。
5. Task 5.1 至 Task 5.2：appearance store 和 localStorage。
6. Task 6.1：接入 App.vue。
7. Task 7.1 至 Task 7.3：编辑器容器、preset、颜色面板。
8. Task 7.8：导出、导入、重置。
9. Task 8.1：前端 build。

MVP 验收标准：

- 可以切换 default 和 primevue-like。
- 修改 primaryColor 实时影响 Button、Tag、Menu、LoadingBar。
- 修改 borderRadiusBase 实时影响 Button、Input、Card。
- 刷新后恢复当前配置。
- 可以导出可用的 `GlobalThemeOverrides JSON`。
- 可以导出和导入完整 appearance JSON。
- 用户在租户 A 和租户 B 的 appearance localStorage 配置互不污染。
