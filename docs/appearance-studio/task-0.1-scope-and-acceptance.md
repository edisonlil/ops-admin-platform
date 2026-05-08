# Task 0.1 范围和验收标准

状态：已完成

## 目标

Appearance Studio 是 `web/admin` 的运行时外观定制系统，目标是让后台应用可以快速切换或定义新的 UI 风格，例如当前默认风、PrimeVue-like、紧凑企业风。

本阶段只做外观系统的第一阶段闭环，不做低代码页面搭建。

## 明确范围

第一阶段包含：

- 三层 token 模型：Primitive、Semantic、Component。
- Preset 机制：`default`、`primevue-like`、`compact-enterprise`。
- Naive UI `GlobalThemeOverrides` 输出。
- CSS variables 输出，用于项目壳层样式。
- Pinia store 管理当前外观状态。
- localStorage 持久化。
- 导入、导出、重置。
- 可视化编辑入口。
- 基于组件覆盖矩阵确认的 MVP 组件范围。

第一阶段不包含：

- 任意页面拖拽搭建。
- 业务页面低代码 schema 设计器。
- 任意 DOM 结构重排。
- 100% 复刻 PrimeVue 组件内部实现。
- 一次性覆盖所有 Naive UI 组件。

## 关键架构边界

Appearance Studio 输出三类运行时结果：

```txt
resolvedTokens -> naiveThemeOverrides -> NConfigProvider
resolvedTokens -> cssVariables        -> layout/pages
layoutConfig   -> layout components   -> shell behavior
```

Naive UI 组件优先通过 `themeOverrides` 覆盖。项目 layout、TabsView、Header、Sidebar、页面容器等非组件库直接控制的样式，通过 CSS variables 覆盖。少量 adapter 和 CSS variables 无法表达的风格差异，可以通过 skin class 兜底。

## 第一阶段 preset

第一阶段确认三个 preset：

- `default`：尽量保持当前 Naive UI Admin 的视觉风格。
- `primevue-like`：清晰边框、浅灰背景、白色 surface、中等圆角、规整表格、浅色菜单选中态。
- `compact-enterprise`：紧凑高度、小圆角、弱阴影、高信息密度。

## 第一阶段验收标准

- 可以切换 `default`、`primevue-like`、`compact-enterprise`。
- 切换 `primevue-like` 后，MVP 必做组件的整体视觉气质明显变化。
- 修改 `primaryColor` 后，MVP 必做组件中的主色、hover、focus、选中态同步变化。
- 修改 `borderRadiusBase` 后，MVP 必做组件中的圆角同步变化。
- 修改密度后，表单链路、按钮、表格等高频区域高度或间距同步变化。
- 刷新页面后恢复当前 preset 和用户覆盖项。
- 可以导出可直接传给 `NConfigProvider` 的 `GlobalThemeOverrides JSON`。
- 可以导出完整 Appearance JSON，并再次导入恢复完整风格。
- 现有 `ProjectSetting` 的导航模式、暗色主题、菜单折叠、Tabs 显示隐藏不被破坏。

## 决策

第一阶段组件范围不在本任务中固定，必须基于 Task 0.3 的组件审计结果和 Task 0.4 的覆盖决策确定。
