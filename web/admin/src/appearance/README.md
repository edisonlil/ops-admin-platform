# Appearance Studio

Appearance Studio 是后台壳层的运行时外观系统。它负责把可编辑的外观 token 转换为 Naive UI `themeOverrides`、根节点 CSS variables、布局配置和少量兜底 skin class。

它不是低代码搭建器，也不负责业务页面结构。第一阶段重点覆盖后台高频壳层和通用组件：Button、Form、Input、Select、DataTable、Pagination、Dropdown、Tag、Card、Modal、Drawer、Menu、Tooltip、LoadingBar 以及布局宽高、间距和密度。

## Token 模型

Token 分为四层：

- `primitive`：基础色阶、字号、圆角、间距、阴影、边框等原子值。
- `semantic`：业务语义值，例如主色、成功色、页面背景、表面背景、基础边框、基础圆角。
- `component`：组件级外观值，例如按钮高度、输入框边框、表格表头背景、菜单选中背景。
- `layout`：布局配置，例如菜单宽度、顶部高度、内容间距、页面最大宽度、表格密度。

`semantic` 和 `component` 可以使用 `{tokenName}` 引用其他 token。解析由 `resolver.ts` 负责，解析失败会返回 `TokenValidationError`，不会让页面崩溃。

## Preset 编写

Preset 位于 `presets/`，每个 preset 需要导出完整的 `AppearancePreset`：

```ts
export const customPreset: AppearancePreset = {
  id: 'custom',
  name: '自定义风格',
  description: '用于说明这个 preset 的视觉目标。',
  skinClass: 'skin-custom',
  tokens: {
    primitive,
    semantic,
    component,
    layout,
  },
};
```

新增 preset 后，在 `presets/index.ts` 注册。建议基于 `defaultPreset.tokens` 做增量覆盖，避免遗漏组件 token。

## Adapter 扩展

Adapter 是外观系统和运行时 UI 的边界：

- `naiveAdapter.ts`：输出 `GlobalThemeOverrides`，只放 Naive UI 能直接消费的覆盖项。
- `cssVarAdapter.ts`：输出根节点 CSS variables，供布局和项目样式消费。
- `layoutAdapter.ts`：输出布局组件可读的布局配置。

新增组件 token 时，需要同时判断它应该进入 `naiveAdapter`、`cssVarAdapter` 还是 skin class。优先使用 Naive UI theme token；只有 theme token 表达不了的壳层差异才使用 CSS variables 或 skin class。

## 新增组件 Token

新增组件 token 的步骤：

1. 在 `types.ts` 中补充组件 token 类型。
2. 在 `tokens/component.ts` 中给出默认值，优先引用 semantic token。
3. 在 preset 中按需覆盖。
4. 在 `naiveAdapter.ts` 或 `cssVarAdapter.ts` 中消费。
5. 在 `components/AppearanceStudio/ComponentPanel.vue` 中暴露可编辑字段。
6. 在 `scripts/appearance-tests.ts` 中补充 adapter 输出断言。

## 新增 Skin

Skin class 只用于少量无法通过 token 表达的差异。新增时：

1. 在 `styles/skins/` 下新增 less 文件。
2. 在 `styles/skins/index.less` 中引入。
3. 在 preset 的 `skinClass` 中声明类名。
4. 控制选择器深度，避免把业务页面样式硬编码进 skin。

## 持久化和租户隔离

Pinia store 位于 `src/store/modules/appearance.ts`。本地存储 key 为：

```text
naive-ui-admin:appearance:{tenantKey}:{username}
```

同一用户切换租户后会重新读取对应租户的配置，避免不同租户之间串样式。

## 验证

外观核心测试：

```bash
cd web/admin
pnpm run test:appearance
```

前端构建：

```bash
cd web/admin
pnpm run build
```

涉及后端菜单、权限或种子数据时，还需要从仓库根目录运行后端测试。
