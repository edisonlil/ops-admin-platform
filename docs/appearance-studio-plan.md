# Appearance Studio 可视化 UI 风格定制系统方案

## 1. 目标定位

Appearance Studio 的目标是为 `web/admin` 提供一套运行时可视化 UI 风格定制能力。它不是低代码平台，不做任意页面拖拽搭建，而是通过设计 token、预设风格、组件库适配和布局变量，让后台系统可以快速切换或定义一套新的 UI 风格。

典型目标包括：

- 快速切换 UI 风格预设，例如 Naive 默认风、PrimeVue-like、紧凑企业风。
- 修改品牌色、文字色、背景色、边框色、圆角、阴影、字号、密度。
- 修改重点组件风格，例如 Button、Input、Select、Table、Card、Menu、Tabs、Tag、Modal、Form。
- 修改后台壳层布局外观，例如菜单宽度、Header 高度、内容区间距、页面宽度模式。
- 实时预览并作用到当前应用。
- 支持 localStorage 持久化、导入、导出、一键重置。

明确不做：

- 不做任意页面低代码搭建。
- 不做任意组件 DOM 重组。
- 不做每个业务页面的完全自由布局编辑。
- 不承诺 100% 复刻 PrimeVue 内部实现，只追求视觉语言接近。

## 2. 核心模型

系统采用三层 token 模型：

```txt
Primitive -> Semantic -> Component -> Adapter -> Runtime Output
```

### 2.1 Primitive Token

Primitive 是最底层的原始设计值，不直接表达业务语义。

示例：

```ts
{
  blue500: '#1677ff',
  gray50: '#f8fafc',
  gray100: '#f1f5f9',
  gray900: '#0f172a',
  radiusSm: '4px',
  radiusMd: '6px',
  radiusLg: '8px',
  fontSizeSm: '13px',
  fontSizeMd: '14px',
  spacingMd: '16px',
  shadowSm: '0 1px 2px rgb(15 23 42 / 8%)'
}
```

### 2.2 Semantic Token

Semantic 是语义层，引用 Primitive 并表达产品语义。

引用语法使用 `{tokenName}`：

```ts
{
  primaryColor: '{blue500}',
  pageBgColor: '{gray50}',
  surfaceColor: '#ffffff',
  textColorBase: '{gray900}',
  borderRadiusBase: '{radiusMd}',
  contentPadding: '{spacingMd}'
}
```

### 2.3 Component Token

Component 是组件语义层，引用 Semantic 或 Primitive，描述组件风格意图。

不建议直接把 Component token 设计成 Naive UI 全量字段名，而是使用更稳定的组件设计语义，再由 adapter 转成 Naive UI `GlobalThemeOverrides`。

示例：

```ts
{
  Button: {
    radius: '{borderRadiusBase}',
    primaryBg: '{primaryColor}',
    primaryText: '#ffffff'
  },
  Input: {
    radius: '{borderRadiusBase}',
    borderColor: '{borderColorBase}',
    focusBorderColor: '{primaryColor}'
  },
  Table: {
    headerBg: '{gray50}',
    borderColor: '{borderColorBase}',
    rowHoverBg: '{gray50}'
  }
}
```

## 3. Runtime 输出

解析后的 token 会输出三类运行时结果：

```txt
resolvedTokens -> naiveThemeOverrides -> NConfigProvider
resolvedTokens -> cssVariables        -> app shell / pages
layoutConfig   -> layout components   -> menu/header/tabs/content
```

### 3.1 Naive UI Theme Overrides

用于覆盖 Naive UI 组件：

```ts
GlobalThemeOverrides
```

优先覆盖：

- `common`
- `Button`
- `Input`
- `Select`
- `DataTable`
- `Card`
- `Menu`
- `Tabs`
- `Tag`
- `Modal`
- `Form`
- `Dropdown`
- `Pagination`
- `LoadingBar`

### 3.2 CSS Variables

用于覆盖项目壳层和非 Naive UI 直接控制的样式：

```css
--app-page-bg: #f8fafc;
--app-surface-bg: #ffffff;
--app-content-padding: 16px;
--app-header-height: 64px;
--app-menu-width: 200px;
--app-card-radius: 6px;
--app-border-color: #dfe3ea;
```

这些变量会逐步替换 layout、Header、Menu、TabsView、页面容器中的硬编码 Less 值。

### 3.3 Layout Config

用于控制后台壳层布局行为：

```ts
{
  density: 'default',
  headerHeight: 64,
  menuWidth: 200,
  contentPadding: 16,
  pageMaxWidth: 'none',
  cardStyle: 'bordered'
}
```

布局配置不负责页面低代码搭建，只负责后台框架级的布局参数。

## 4. 建议目录结构

```txt
web/admin/src/appearance/
  tokens/
    primitive.ts
    semantic.ts
    component.ts
    layout.ts
  presets/
    default.ts
    primevueLike.ts
    compact.ts
  resolver.ts
  validators.ts
  naiveAdapter.ts
  cssVarAdapter.ts
  layoutAdapter.ts
  types.ts

web/admin/src/store/modules/appearance.ts

web/admin/src/components/AppearanceStudio/
  index.vue
  PresetPanel.vue
  PrimitivePanel.vue
  SemanticPanel.vue
  ComponentPanel.vue
  LayoutPanel.vue
  PreviewPanel.vue
  ImportExportPanel.vue
  TokenColorRow.vue
  TokenNumberRow.vue
  TokenSelectRow.vue
```

项目当前 store 目录是 `web/admin/src/store/modules`，因此新 store 应放在该目录下，而不是新增 `src/stores`。

## 5. Store 设计

新增 `useAppearanceStore`，负责管理 appearance 状态。

核心状态：

```ts
{
  version: 1,
  presetId: 'default',
  tokenOverrides: {},
  layoutOverrides: {},
  skinClass: ''
}
```

多租户约束：

- Store 必须从 `userStore.info.current_tenant` 读取当前租户信息。
- localStorage key 必须带 `tenantKey` 和 `username`，禁止使用全局 `naive-ui-admin:appearance`。
- 切换租户后必须重新加载当前租户对应的 appearance，不能沿用上一个租户的 `themeOverrides`、`cssVars`、`layoutConfig`。
- 详细约束见 `docs/appearance-studio/multi-tenant-impact.md`。

核心 getter：

- `resolvedTokens`
- `themeOverrides`
- `cssVars`
- `layoutConfig`
- `validationErrors`

核心 action：

- `applyPreset(presetId)`
- `updatePrimitiveToken(key, value)`
- `updateSemanticToken(key, value)`
- `updateComponentToken(component, key, value)`
- `updateLayoutToken(key, value)`
- `resetToPreset()`
- `resetAll()`
- `exportThemeOverridesJSON()`
- `exportAppearanceJSON()`
- `importAppearanceJSON(payload)`

localStorage 只保存用户输入、preset id 和版本信息，不保存 computed 结果，避免后续 adapter 升级后旧数据污染运行结果。保存时必须按租户和用户隔离。

## 6. Resolver 规则

`resolver.ts` 负责解析 `{tokenName}` 引用。

必须支持：

- Primitive 被 Semantic 引用。
- Semantic 被 Component 引用。
- Layout token 可引用 Primitive 或 Semantic。
- 嵌套对象递归解析。
- 数组值透传或递归解析。
- 找不到引用时返回 fallback，并记录错误。
- 循环引用检测，例如 `a -> b -> a`。
- 非法颜色、非法数字、非法单位由 validators 提供错误信息。

建议 resolver 不直接抛出导致页面崩溃的异常，而是返回：

```ts
{
  tokens,
  errors
}
```

## 7. Adapter 设计

### 7.1 naiveAdapter

输入解析后的 tokens，输出 `GlobalThemeOverrides`。

职责：

- 把自定义 component token 映射到 Naive UI 字段。
- 生成 hover、pressed、focus 等状态色。
- 统一处理暗色主题和亮色主题差异。
- 避免业务组件直接知道 Naive UI token 字段。

### 7.2 cssVarAdapter

输入解析后的 tokens，输出可绑定到根节点的 style object。

示例：

```ts
{
  '--app-page-bg': tokens.semantic.pageBgColor,
  '--app-surface-bg': tokens.semantic.surfaceColor,
  '--app-content-padding': `${tokens.layout.contentPadding}px`
}
```

### 7.3 layoutAdapter

输入 layout tokens，输出现有 layout 可消费的结构。

它可以逐步替代现有 `projectSettingStore` 中与外观相关的字段。第一阶段可以先桥接，不需要一次性移除旧 store。

## 8. App 接入方式

当前 `App.vue` 已经存在 `NConfigProvider` 和 `theme-overrides` 接入点。改造后建议由 `appearanceStore` 统一输出：

```vue
<NConfigProvider
  :locale="zhCN"
  :theme="getDarkTheme"
  :theme-overrides="appearanceStore.themeOverrides"
  :date-locale="dateZhCN"
>
  <div :class="appearanceStore.skinClass" :style="appearanceStore.cssVars">
    <AppProvider>
      <RouterView />
      <AppearanceStudio />
    </AppProvider>
  </div>
</NConfigProvider>
```

现有 `designSettingStore.darkTheme` 可以先保留。`designSettingStore.appTheme` 建议后续迁移为 appearance token，避免两个 store 同时控制主色。

## 9. PrimeVue-like 风格策略

PrimeVue-like 不等于引入 PrimeVue，也不替换 Naive UI。它通过 preset、theme overrides 和少量 skin class 实现视觉接近。

视觉特征：

- 白色 surface。
- 浅灰页面背景。
- 清晰的 1px 边框。
- 中等圆角，建议 6px。
- Button 更扁平，primary 使用实色。
- Input、Select 边框存在感更强，focus 使用主色。
- Table 表头浅灰，行 hover 轻量。
- Menu 选中态使用浅色背景 + 主色文字。
- Card 使用边框或轻阴影，不使用过重阴影。

如果 Naive UI token 无法覆盖某些细节，可以通过根 class `skin-primevue-like` 做少量 CSS 补偿。该 CSS 必须克制，避免大量深层选择器导致后续维护困难。

## 10. 编辑器交互设计

Appearance Studio 建议使用 `NDrawer`，不要混进当前 `ProjectSetting.vue`，避免项目配置面板继续膨胀。

当前实现采用主题管理页内的设计工作台，不再以 Drawer 作为唯一入口。后续如果重新引入 Drawer，只能作为轻量快速编辑入口，不能替代完整工作台。

### 10.1 设计工作台信息架构

设计工作台必须保持“层级导航 + 配置页 + 最终效果预览”的结构：

- 左侧是工作台导航，按层级组织，不把所有配置平铺成一长串。
- 一级层级暂定为：`全局样式`、`组件样式`、`界面布局`、`导入导出`。
- 每个一级层级下面展示可配置页面栏，例如全局样式下的 `风格预设`、`基础变量`、`语义变量`、`圆角`、`字体`、`阴影`。
- 组件样式必须按具体组件拆成独立页面，例如 `按钮`、`表单控件`、`数据表格`、`状态与操作`、`外壳与内容面`。
- 中间区域只展示当前页面的配置项，不在一个组件面板里折叠塞入所有组件配置。
- 顶部只保留返回、主题名称、状态、预设、校验数量、保存和发布等全局动作。

这套结构的目标是让用户先判断“我在调哪一类”，再进入“我调哪一个对象”，最后通过右侧看到“这个对象的最终效果”。

### 10.2 配置页表达规则

配置页要服务重复编辑场景，保持轻量、密集、克制：

- 一个配置页只处理一个明确对象。设置字体就只展示字体变量，设置按钮就只展示按钮变量。
- 不用为了凑面板而展示无关配置；无关对象通过左侧页面栏切换。
- 配置项标题使用业务可理解名称，token path 作为辅助信息，不反客为主。
- 引用值和解析值要保留，方便判断 `{primaryColor}` 这类引用最终落到什么值。
- `NCollapse` 只能用于同一对象内部的次级分组，不能作为组件列表导航的替代。
- 组件范围必须继续追溯到覆盖矩阵，不能随手新增无来源组件。

编辑控件：

- 颜色：`input type="color"` + `NInput`
- 数值：`NSlider` + `NInputNumber`
- 枚举：`NSelect` 或 `NSegmented`
- 布尔：`NSwitch`
- 同一对象内分组：`NCollapse`

组件面板优先暴露产品化字段，不直接展示 Naive UI 的全部 token 字段。

### 10.3 预览区规则

预览区是给用户判断最终效果的主视觉区域，不能退化成说明卡片或调试信息：

- 预览区应比单个配置列更宽，在 1366px 桌面宽度下仍能展示清晰样例。
- 外层容器减少边框和卡片堆叠，避免“卡片套卡片”。必要边框只保留在真实组件边界上，例如输入框、表格、按钮、标签。
- 预览内容必须跟当前配置对象一致：设置字体只展示字体层级效果，设置按钮只展示按钮状态，设置布局只展示布局比例示意。
- 不需要复刻完整后台页面。组件配置看组件最终状态，布局配置看结构示意，全局样式看高频组合效果。
- 预览标题使用用户视角，例如“组件最终效果”“全局视觉效果”“颜色落地效果”，避免把实现术语当主标题。
- 预览样例要体现真实后台场景：按钮状态、表单控件、数据表格、状态标签、导航壳层、内容面和布局留白。
- 预览必须跟随当前 draft token 实时变化，用户无需保存或跳转业务页面即可判断效果。
- 窄屏下预览可以下移，但不能隐藏核心预览，也不能遮挡保存和发布动作。

### 10.4 视觉边界

Appearance Studio 是运营后台的工作台，不是营销页：

- 避免大 hero、装饰渐变、视觉噪声和过重阴影。
- 避免过多描边。用间距、分组标题、轻量分隔线和状态色建立层级。
- 颜色只用于状态、当前选中项和关键动作，不做装饰性铺色。
- 左侧导航选中态应克制，使用主色文字、浅底和细边标识即可。
- 预览窗口是重点区域，配置区和导航区不能抢视觉主导权。

## 11. 组件覆盖策略

组件覆盖范围不能只按经验预设。实施前必须先对项目实际组件使用情况做盘点，并产出覆盖矩阵。

覆盖矩阵至少包含：

- 组件名称。
- 使用次数。
- 典型出现位置。
- 是否为 Naive UI 原生组件。
- 是否为项目二次封装组件。
- 对整体 UI 气质的影响级别。
- 可用覆盖方式：`themeOverrides`、CSS variables、skin class。
- 是否进入 MVP。
- 延后原因。

优先级规则：

- 高频出现且影响整体 UI 气质的组件优先。
- 后台壳层组件优先，例如 Layout、Menu、Tabs、Header、Card。
- 表单链路组件优先，例如 Button、Input、Select、Form。
- 列表页组件优先，例如 DataTable、Pagination、Tag。
- 低频但视觉存在感强的组件进入候选，例如 Modal、Drawer、Upload。
- 很少使用或不影响风格的组件延后。

这样可以避免第一阶段只覆盖显眼组件，后续发现页面里大量未覆盖组件导致 PrimeVue-like 风格不完整。

## 12. 验收标准

第一阶段验收：

- 切换 `PrimeVue Like` 后，Button、Input、Table、Menu、Card 风格明显变化。
- 修改品牌色后 Button、Tag、Link、Menu 选中态同步变化。
- 修改圆角后 Button、Input、Card、Modal 同步变化。
- 修改密度后 Button、Input、Table、Form 高度变化。
- 刷新后恢复当前 preset 和自定义 token。
- 导出的 `themeOverrides` 可直接给 `NConfigProvider` 使用。
- 导出的 appearance JSON 可再次导入并恢复完整风格。
- 不影响现有业务接口和页面数据结构。
- 切换租户后不会沿用上一个租户的本地 appearance 配置。
- 同一用户切回原租户后，可以恢复该租户下的本地 appearance 配置。

## 13. 风险与控制

### 风险 1：Naive UI token 覆盖范围有限

控制方式：

- 先覆盖高频组件。
- 使用 adapter 集中维护映射。
- 对少量 token 无法覆盖的视觉差异使用 skin class 兜底。

### 风险 2：样式覆盖变得脆弱

控制方式：

- 优先使用 `themeOverrides` 和 CSS variables。
- 限制深层 CSS selector。
- 每个 skin class 只处理 adapter 无法表达的差异。

### 风险 3：两个主题 store 冲突

控制方式：

- 第一阶段桥接现有 `designSettingStore`。
- 第二阶段将 `appTheme` 迁移到 `appearanceStore`。
- 暗色主题开关可以继续复用原有设置，也可以后续归并。

### 风险 4：Token 数量失控

控制方式：

- 对普通用户只暴露 preset 和关键旋钮。
- 高级 token 编辑放到高级区域。
- Component token 只覆盖重点组件，不追求一次性全量覆盖。

### 风险 5：组件覆盖范围判断失真

控制方式：

- 实施前先做组件使用盘点。
- 用覆盖矩阵决定第一阶段组件范围。
- 每个未覆盖组件必须记录延后原因。
- 后续新增业务组件时同步更新覆盖矩阵。

### 风险 6：多租户主题污染

控制方式：

- 第一阶段就使用 tenant-aware appearance store。
- localStorage key 必须包含租户和用户。
- `switchTenant` 后必须重新加载 appearance。
- 导入 appearance JSON 默认只影响当前租户当前用户。

## 14. 推荐实施策略

推荐先做“Preset 驱动 + 关键视觉旋钮 + 高级 token 编辑”的 MVP。

不要第一阶段就追求所有 Naive UI 组件全覆盖，也不要做页面低代码布局。先让一个 `PrimeVue-like` preset 跑通，并覆盖后台系统 80% 高频视觉区域，再逐步扩展。
