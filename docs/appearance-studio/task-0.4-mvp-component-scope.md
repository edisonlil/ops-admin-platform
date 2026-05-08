# Task 0.4 第一阶段组件覆盖范围

状态：已完成

## 前置依据

本决策基于：

- Task 0.1 的范围边界。
- Task 0.2 的主题与布局入口清单。
- Task 0.3 的组件使用审计与覆盖矩阵。

## 决策原则

- 高频出现且影响整体 UI 气质的组件进入 MVP。
- 后台壳层优先，因为它决定用户对整套 UI 风格的第一感知。
- 表单链路优先，因为后台系统大量操作集中在筛选、创建、编辑。
- 表格链路优先，因为列表页是后台系统主场景。
- Appearance Studio 自身会使用的组件优先，避免编辑器与目标风格脱节。
- 低频但视觉存在感强的组件可以进入 MVP，例如 Modal、Drawer。
- 展示类、加载类、低频反馈类组件延后。

## 第一阶段必做范围

### 全局与壳层

| 范围 | 覆盖方式 | 必做原因 |
| --- | --- | --- |
| `common` | `themeOverrides.common` | 全局主色、文字、边框、圆角、字号基础 |
| Layout shell | CSS variables + layout token | 页面背景、内容间距、sider、header、menu width |
| Header | CSS variables + Dropdown/Avatar 部分继承 | 顶栏是后台第一视觉层 |
| Menu / `NMenu` | `themeOverrides.Menu` + layout token | 侧边导航决定 PrimeVue-like 是否成立 |
| TabsView | CSS variables + Dropdown token | 项目自定义标签页，不由 Naive Tabs 完全控制 |

### 表单链路

| 组件 | 覆盖方式 | 必做原因 |
| --- | --- | --- |
| `NForm` | `themeOverrides.Form` + density token | label、feedback、表单密度 |
| `NFormItem` | `themeOverrides.Form` | 高频表单结构 |
| `NInput` | `themeOverrides.Input` | 高频输入控件，PrimeVue-like 边框/focus 关键 |
| `NInputNumber` | `themeOverrides.InputNumber` | 业务表单和 Appearance Studio 自身会使用 |
| `NSelect` | `themeOverrides.Select` | 高频筛选与表单控件 |
| `NSwitch` | `themeOverrides.Switch` | 设置项和动态表单高频 |
| `NCheckbox` / `NCheckboxGroup` | `themeOverrides.Checkbox` | 表单链路完整性 |
| `NRadio` / `NRadioGroup` | `themeOverrides.Radio` | 表单链路完整性 |

### 表格与操作链路

| 组件 | 覆盖方式 | 必做原因 |
| --- | --- | --- |
| `NDataTable` | `themeOverrides.DataTable` + density token | 后台列表页核心 |
| `NPagination` | `themeOverrides.Pagination` | DataTable 分页体验需要同步 |
| `NButton` | `themeOverrides.Button` | 操作入口最高频 |
| `NDropdown` | `themeOverrides.Dropdown` | Header、TabsView、TableAction、表格工具栏均使用 |
| `NTag` | `themeOverrides.Tag` | 状态展示和表格列常用 |

### 容器与弹层

| 组件 | 覆盖方式 | 必做原因 |
| --- | --- | --- |
| `NCard` | `themeOverrides.Card` + CSS variables | 页面 surface、边框、阴影核心 |
| `NModal` | `themeOverrides.Modal` | 业务编辑、上传预览、封装弹窗 |
| `NDrawer` | `themeOverrides.Drawer` | ProjectSetting、移动端菜单、Appearance Studio 自身 |

### 反馈与基础可用性

| 组件 | 覆盖方式 | 必做原因 |
| --- | --- | --- |
| `NLoadingBar` | `themeOverrides.LoadingBar` | 全局加载反馈需跟随主色 |
| `NTooltip` | `themeOverrides.Tooltip` | 工具栏和表单提示高频，成本低 |

## 第一阶段候选范围

这些组件不阻塞 MVP，但如果 adapter 覆盖成本低，可以顺手补齐：

| 组件 | 原因 |
| --- | --- |
| `NAlert` | 状态色反馈，出现 13 次，适合第二批或顺手覆盖 |
| `NSkeleton` | 加载态出现 15 次，但不决定主风格 |
| `NTree` | RBAC 页面重要，但全局频率较低 |
| `NUpload` | 低频，但边框和按钮风格明显 |
| `NDatePicker` / `NTimePicker` | 动态表单会用，第二阶段应补齐 |
| `NTabs` / `NTabPane` | Naive Tabs 使用少，项目主要 TabsView 是自定义实现 |

## 第一阶段延后范围

| 组件 | 延后原因 |
| --- | --- |
| `NDescriptions` / `NDescriptionsItem` | 详情展示类，不影响 MVP 主链路 |
| `NList` / `NListItem` / `NThing` | 局部展示类，后续按页面需要覆盖 |
| `NAvatar` | 可继承圆角策略，暂不单独暴露 token |
| `NBadge` | 状态点类，后续统一状态色时覆盖 |
| `NResult` | 低频结果页 |
| `NProgress` | 低频局部进度 |
| `NBackTop` | 单点辅助组件 |
| `NGrid` / `NGridItem` / `NGi` / `NSpace` | 优先用 density 和 spacing token 控制，不做组件级深度定制 |

## 对后续任务的约束

Task 1.4 `component.ts` 必须至少定义以下组件 token：

- `Button`
- `Form`
- `Input`
- `InputNumber`
- `Select`
- `Switch`
- `Checkbox`
- `Radio`
- `DataTable`
- `Pagination`
- `Dropdown`
- `Tag`
- `Card`
- `Modal`
- `Drawer`
- `Menu`
- `Tooltip`
- `LoadingBar`

Task 4.1 `naiveAdapter.ts` 必须至少输出以下 Naive overrides：

- `common`
- `Button`
- `Form`
- `Input`
- `InputNumber`
- `Select`
- `Switch`
- `Checkbox`
- `Radio`
- `DataTable`
- `Pagination`
- `Dropdown`
- `Tag`
- `Card`
- `Modal`
- `Drawer`
- `Menu`
- `Tooltip`
- `LoadingBar`

Task 7.5 `ComponentPanel.vue` 第一阶段不需要暴露所有必做组件的全部字段。建议面板优先排序：

1. Button
2. Input / InputNumber / Select
3. Form density
4. DataTable / Pagination
5. Menu
6. Card
7. Modal / Drawer
8. Tag / Dropdown / Tooltip
9. Switch / Checkbox / Radio

## MVP 验收补充

- PrimeVue-like preset 切换后，Layout、Header、Menu、TabsView、Card、Form、Input、Select、Button、DataTable 的变化必须肉眼可见。
- 表单链路中的 Input、Select、Switch、Checkbox、Radio 风格必须一致。
- 表格链路中的 DataTable、Pagination、Button、Dropdown、Tag 风格必须一致。
- Modal 和 Drawer 的圆角、背景、边框或阴影必须跟随 preset。
- 延后组件如果视觉明显不协调，需要记录到后续任务，而不是临时扩大 MVP。
