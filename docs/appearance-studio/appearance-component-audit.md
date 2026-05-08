# Task 0.3 组件使用审计与覆盖矩阵

状态：已完成

## 扫描范围

本审计覆盖：

- `web/admin/src/layout`
- `web/admin/src/components`
- `web/admin/src/views`
- `web/admin/src/plugins/naive.ts`

扫描方式：

- 静态统计 `.vue`、`.ts`、`.tsx` 中的 `<n-*>` 模板标签。
- 查看 `web/admin/src/plugins/naive.ts` 注册的全局 Naive UI 组件。
- 补充检查 `BasicForm`、`BasicTable`、`BasicModal`、`BasicUpload` 等二次封装组件。

局限：

- `BasicForm` 通过动态 `componentMap` 渲染组件，单纯模板计数会低估 Input、Select、Switch、Checkbox、DatePicker、TimePicker 的真实使用影响。
- `BasicTable` 封装了 DataTable、Pagination、Dropdown、Switch、Tooltip 等，静态页面中的 `n-data-table` 次数不能完全代表表格体系的视觉权重。
- `NMenu` 在 layout 中使用 PascalCase `<NMenu>`，不会出现在 `<n-*>` 统计中，但它是后台壳层最高优先级组件。

## 模板标签频次

| 组件标签 | 次数 | 备注 |
| --- | ---: | --- |
| `n-button` | 114 | 表单提交、表格操作、弹窗 footer、高频动作入口 |
| `n-form-item` | 112 | 表单体系核心 |
| `n-card` | 86 | 页面内容容器和示例页高频使用 |
| `n-input` | 83 | 表单和搜索高频控件 |
| `n-icon` | 74 | Header、Toolbar、Menu、按钮图标 |
| `n-space` | 65 | 间距组件，影响密度但不一定需要单独 token |
| `n-grid` | 29 | 表单和页面布局 |
| `n-descriptions-item` | 26 | 详情展示 |
| `n-form` | 25 | 表单体系核心 |
| `n-switch` | 24 | 设置、表格工具栏、表单动态组件 |
| `n-grid-item` | 22 | 布局 |
| `n-select` | 21 | 表单和筛选高频控件 |
| `n-tag` | 21 | 状态展示、表格列、标记 |
| `n-gi` | 18 | 表单布局 |
| `n-tooltip` | 18 | 工具栏、表单提示、图标提示 |
| `n-form-item-gi` | 17 | 表单布局 |
| `n-divider` | 15 | 设置面板和内容分隔 |
| `n-skeleton` | 15 | 加载态 |
| `n-alert` | 13 | 反馈提示 |
| `n-modal` | 13 | 弹窗、上传预览、业务编辑 |
| `n-data-table` | 12 | 列表页和 BasicTable 封装 |
| `n-thing` | 12 | 列表展示 |
| `n-radio` | 11 | 表单控件 |
| `n-list-item` | 10 | 列表展示 |
| `n-avatar` | 9 | Header 用户、列表展示 |
| `n-checkbox` | 9 | 表单控件 |
| `n-dropdown` | 8 | Header、TabsView、TableAction、表格工具栏 |
| `n-input-number` | 8 | 表单控件 |
| `n-tab-pane` | 7 | Tab 内容 |
| `n-radio-group` | 6 | 表单控件 |
| `n-descriptions` | 6 | 详情展示 |
| `n-badge` | 6 | 设置、状态点 |
| `n-spin` | 5 | 加载态 |
| `n-tree` | 5 | 权限、菜单、角色配置 |
| `n-drawer` | 4 | ProjectSetting、移动端菜单、业务抽屉 |
| `n-result` | 4 | 结果页 |
| `n-drawer-content` | 3 | 抽屉内容 |
| `n-date-picker` | 2 | 表单动态组件也会放大影响 |
| `n-upload` | 2 | 上传业务和封装组件 |
| `n-tabs` | 2 | 示例与设置页；TabsView 是自定义实现 |
| `n-layout` / `n-layout-sider` | 2 | 主 layout 核心 |
| `n-pagination` | 0 | 通过 DataTable pagination 或 TS 引用体现 |
| `NMenu` | 1+ | PascalCase 使用，主菜单核心 |

## 关键二次封装组件

| 封装组件 | 路径 | 内部关键组件 | 视觉影响 |
| --- | --- | --- | --- |
| BasicForm | `web/admin/src/components/Form/src/BasicForm.vue` | Form、Grid、FormItem、Input、Select、Checkbox、Radio、Button、Tooltip | 高 |
| BasicTable | `web/admin/src/components/Table/src/Table.vue` | DataTable、Dropdown、Switch、Tooltip、Icon、Pagination | 高 |
| BasicModal | `web/admin/src/components/Modal/src/basicModal.vue` | Modal、Button | 中高 |
| BasicUpload | `web/admin/src/components/Upload/src/BasicUpload.vue` | Upload、Modal、Button | 中 |
| TableAction | `web/admin/src/components/Table/src/components/TableAction.vue` | Button、Dropdown、Icon | 高 |
| ColumnSetting | `web/admin/src/components/Table/src/components/settings/ColumnSetting.vue` | Button、Dropdown、Checkbox、Tooltip | 中 |

## 覆盖矩阵

| 组件/区域 | 使用强度 | 典型位置 | 视觉影响 | 覆盖方式 | MVP | 说明 |
| --- | ---: | --- | --- | --- | --- | --- |
| `common` | 全局 | 全应用 | 高 | `themeOverrides.common` | 是 | 主色、文字色、边框、圆角、字号基础来源 |
| Layout shell | 高 | `layout/index.vue` | 高 | CSS variables + layout token | 是 | 页面背景、content 间距、sider 阴影、menu width |
| Header | 高 | `layout/components/Header` | 高 | CSS variables + `Dropdown`/`Avatar` token | 是 | 顶栏决定后台第一视觉层 |
| Menu / `NMenu` | 高 | `layout/components/Menu` | 高 | `themeOverrides.Menu` + layout token | 是 | PrimeVue-like 是否成立的关键区域 |
| TabsView | 高 | `layout/components/TagsView` | 高 | CSS variables + `Dropdown` token | 是 | 自定义实现，不能只靠 Naive `Tabs` |
| `NButton` | 114 | 表单、表格、弹窗 | 高 | `themeOverrides.Button` | 是 | 高频动作组件 |
| `NForm` / `NFormItem` | 25 / 112 | BasicForm、业务表单 | 高 | `themeOverrides.Form` + density token | 是 | 表单密度和 label 体验关键 |
| `NInput` | 83 | 表单、搜索、锁屏 | 高 | `themeOverrides.Input` | 是 | PrimeVue-like 边框/focus 关键 |
| `NSelect` | 21 + 动态表单 | 表单、筛选 | 高 | `themeOverrides.Select` | 是 | 表单链路核心 |
| `NDataTable` | 12 + BasicTable | 列表页 | 高 | `themeOverrides.DataTable` + density token | 是 | 后台页面气质核心 |
| `NCard` | 86 | 页面容器 | 高 | `themeOverrides.Card` + CSS variables | 是 | 内容 surface、边框、阴影核心 |
| `NTag` | 21 + TS render | 状态展示、表格 | 中高 | `themeOverrides.Tag` | 是 | 主色和状态色感知明显 |
| `NDropdown` | 8 + layout | Header、TabsView、TableAction | 中高 | `themeOverrides.Dropdown` | 是 | 与菜单、工具栏联动 |
| `NSwitch` | 24 + 动态表单 | 设置、表格工具栏 | 中 | `themeOverrides.Switch` | 是 | 设置类页面高频 |
| `NCheckbox` / `NCheckboxGroup` | 9 + 动态表单 | 表单、列设置 | 中 | `themeOverrides.Checkbox` | 是 | 表单链路完整性 |
| `NRadio` / `NRadioGroup` | 11 / 6 | 表单 | 中 | `themeOverrides.Radio` | 是 | 表单链路完整性 |
| `NInputNumber` | 8 + 动态表单 | 表单、未来 token editor | 中 | `themeOverrides.InputNumber` | 是 | Appearance Studio 自身会高频使用 |
| `NModal` | 13 | BasicModal、业务编辑 | 中高 | `themeOverrides.Modal` | 是 | 视觉存在感强 |
| `NDrawer` | 4 | ProjectSetting、移动端菜单、业务抽屉 | 中高 | `themeOverrides.Drawer` | 是 | Appearance Studio 自身会使用 Drawer |
| `NTooltip` | 18 | 表单提示、工具栏 | 中 | `themeOverrides.Tooltip` | 候选 | 高频但不决定主风格 |
| `NAlert` | 13 | 提示区 | 中 | `themeOverrides.Alert` | 候选 | 状态色覆盖可进入第二阶段 |
| `NSkeleton` | 15 | 加载态 | 中 | `themeOverrides.Skeleton` | 候选 | 影响加载体验，非 MVP 核心 |
| `NTree` | 5 | 权限、菜单、角色 | 中 | `themeOverrides.Tree` | 候选 | RBAC 页面重要，但非全局高频 |
| `NUpload` | 2 | 上传业务 | 中 | `themeOverrides.Upload` | 候选 | 低频但边框风格明显 |
| `NDatePicker` / `NTimePicker` | 2 + 动态表单 | 表单 | 中 | `themeOverrides.DatePicker` / `TimePicker` | 候选 | 动态表单支持，建议第二阶段补齐 |
| `NDescriptions` | 6 | 详情页 | 中 | `themeOverrides.Descriptions` | 延后 | 展示类，先不影响 MVP 主链路 |
| `NList` / `NThing` | 10 / 12 | 列表展示 | 中 | `themeOverrides.List` / `Thing` | 延后 | 页面局部使用 |
| `NAvatar` | 9 | Header、列表 | 低中 | `themeOverrides.Avatar` | 延后 | 可继承圆角策略，非 MVP 必要 |
| `NBadge` | 6 | 设置状态点 | 低中 | `themeOverrides.Badge` | 延后 | 状态色后续统一处理 |
| `NResult` | 4 | 结果页 | 低 | `themeOverrides.Result` | 延后 | 低频页面 |
| `NGrid` / `NSpace` | 29 / 65 | 布局辅助 | 中 | spacing/layout token | 延后 | 不建议深度覆盖组件本身，优先控制密度和 spacing |

## 审计结论

第一阶段不能只覆盖 Button、Input、Table。为了让 PrimeVue-like 风格完整，需要同时覆盖后台壳层、自定义 TabsView、Menu、Card、表单链路、表格链路和弹层入口。

MVP 组件范围应由 Task 0.4 固化，且后续 `component.ts`、`naiveAdapter.ts`、`ComponentPanel.vue` 都必须以该范围为准。
