# Task 0.2 主题与布局入口清单

状态：已完成

## 目标

梳理当前项目中主题、布局、组件注册和样式硬编码的主要入口，明确 Appearance Studio 后续应该接入哪里，以及哪些样式应逐步迁移到 CSS variables。

## 主题入口

| 入口 | 当前职责 | 后续处理 |
| --- | --- | --- |
| `web/admin/src/App.vue` | 使用 `NConfigProvider` 绑定 `theme`、`theme-overrides`、locale；当前根据 `designSettingStore.appTheme` 生成 `common.primaryColor` 等少量 overrides | 改为读取 `appearanceStore.themeOverrides`；根容器绑定 `appearanceStore.cssVars` 和 `appearanceStore.skinClass` |
| `web/admin/src/store/modules/designSetting.ts` | 管理 `darkTheme`、`appTheme`、`appThemeList` | 第一阶段保留 `darkTheme`；`appTheme` 后续迁移为 `semantic.primaryColor` |
| `web/admin/src/settings/designSetting.ts` | 当前主题色列表和默认暗色开关 | 后续由 Appearance preset 和 token 替代主题色列表 |
| `web/admin/src/utils/index.ts` | 提供 `lighten`，当前用于主色 hover/pressed 派生 | 可继续复用，或在 appearance adapter 中集中提供颜色派生函数 |

## Store 与布局配置入口

| 入口 | 当前职责 | 后续处理 |
| --- | --- | --- |
| `web/admin/src/store/modules/projectSetting.ts` | 管理 `navMode`、`navTheme`、`headerSetting`、`menuSetting`、`multiTabsSetting`、`crumbsSetting`、页面动画等 | 第一阶段桥接，不直接移除；外观相关字段逐步由 `appearanceStore.layoutConfig` 接管 |
| `web/admin/src/settings/projectSetting.ts` | 提供布局默认值，例如菜单宽度、Header 固定、Tabs 固定、移动端断点 | 后续拆分行为配置和外观配置；宽度、高度、间距类迁移到 layout token |
| `web/admin/src/hooks/setting/useProjectSetting.ts` | 读取 project setting | 后续可按需增加 appearance layout hook，避免业务直接读 token |
| `web/admin/src/hooks/setting/useDesignSetting.ts` | 读取 darkTheme 和 appTheme | 后续 appTheme 迁移后减少使用 |

## Layout 入口

| 入口 | 当前职责 | 外观关注点 |
| --- | --- | --- |
| `web/admin/src/layout/index.vue` | 主框架：Sider、Drawer、Header、Content、TabsView、MainView | 页面背景、content margin/padding、Header padding-top、menu width、sider shadow、fixed header/tabs offset |
| `web/admin/src/layout/components/Header/index.vue` | 顶栏、工具按钮、用户菜单、设置按钮 | Header 高度、背景、图标色、hover、间距、dropdown 触发区域 |
| `web/admin/src/layout/components/Header/ProjectSetting.vue` | 当前项目配置抽屉 | 可保留项目行为配置；Appearance Studio 不建议混入此文件 |
| `web/admin/src/layout/components/Menu/index.vue` | `NMenu` 菜单渲染 | Menu 选中态、hover、indent、collapsed width、深浅模式 |
| `web/admin/src/layout/components/TagsView/index.vue` | 多标签页栏，含自定义 tab 样式和 dropdown | TabsView 背景、tab item 边框、active 色、close icon、间距、高度 |
| `web/admin/src/layout/components/Logo/index.vue` | 侧边栏 logo | logo 区高度、背景、文字颜色 |
| `web/admin/src/layout/components/Main/index.vue` | RouterView、keep-alive、页面动画 | 主要关注动画配置，不是第一阶段样式重点 |

## 组件注册入口

| 入口 | 当前职责 | 后续处理 |
| --- | --- | --- |
| `web/admin/src/plugins/naive.ts` | 注册全局 Naive UI 组件 | 作为组件覆盖审计的基准列表 |
| `web/admin/src/plugins/naiveDiscreteApi.ts` | Naive 脱离上下文 API | 后续需确认 message/dialog/notification 是否跟随 theme |

## 二次封装组件入口

| 入口 | 当前职责 | 外观关注点 |
| --- | --- | --- |
| `web/admin/src/components/Form/src/BasicForm.vue` | 动态表单渲染，使用 Form、Grid、FormItem、Input、Select、Checkbox、Radio、Button 等 | 表单密度、label 宽度、输入控件高度、按钮间距 |
| `web/admin/src/components/Table/src/Table.vue` | 表格封装，含工具栏、密度、刷新、列设置、DataTable、Pagination | 表格密度、表头、边框、工具栏、dropdown、switch、icon |
| `web/admin/src/components/Modal/src/basicModal.vue` | Modal 封装 | 弹窗圆角、header/footer、按钮 |
| `web/admin/src/components/Upload/src/BasicUpload.vue` | Upload 和 Modal 组合 | 上传区域边框、按钮、弹窗 |

## 需要 CSS Variables 的典型样式

优先迁移这些硬编码样式：

- 页面背景：`layout-default-background` 当前为 `#f5f7f9`。
- 主内容间距：`layout-content-main` 当前为 `margin: 0 10px 10px`、`padding-top: 64px`。
- TabsView 高度、背景、active tab 样式、边框。
- Sider shadow：当前存在 `box-shadow: 2px 0 8px 0 rgb(29 35 41 / 5%)`。
- Header 内部图标、按钮、hover 区域的颜色和间距。
- Logo 区高度、背景、文字颜色。
- Table toolbar 的图标间距、title 字号。

建议第一批 CSS variables：

```css
--app-page-bg
--app-surface-bg
--app-content-margin
--app-content-padding
--app-header-height
--app-tabs-height
--app-menu-width
--app-collapsed-menu-width
--app-border-color
--app-card-radius
--app-shadow-sm
--app-icon-color
--app-icon-hover-bg
```

## 接入结论

第一阶段最小接入点是 `App.vue`、`appearanceStore`、`naiveAdapter`、`cssVarAdapter`。布局样式改造应从 `layout/index.vue` 和 `TagsView/index.vue` 开始，因为这两处最影响后台整体风格。
