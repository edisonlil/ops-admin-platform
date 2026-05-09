# Page Runtime

`page-runtime` 是后台页面协议层。它不替代 Theme Runtime，也不接管业务数据，只统一页面骨架、页面节奏、列表协议、密度和集合视图的基础交互。

## List Page

页面通过 `defineListPage()` 声明，再交给 `ListPageRuntime` 渲染：

```ts
const apiKeyListPage = defineListPage<Recordable>({
  id: 'settings.api-keys',
  title: 'API Key',
  description: '管理用于外部集成和自动化访问的 API Key。',
  variant: 'dense-data',
  density: 'compact',
  view: {
    type: 'table',
    columns,
    rowKey: (row) => Number(row.id),
    scrollX: 1000,
  },
});
```

## Table Protocol

所有表格列表默认由 `ListPageRuntime` 注入统一能力：

- 左侧多选列；
- 列宽拖拽；
- 表头锁按钮冻结列；
- 表格高度、行高和表头高度约束；
- 分页、空状态和加载状态。

### 多选列

表格默认开启多选列，业务页可以只配置固定方式：

```ts
view: {
  type: 'table',
  selectionColumn: {
    fixed: 'left',
  },
}
```

### 列宽拖拽

普通列默认开启 `resizable`。如果某些列不适合拖拽，可以通过 key 关闭：

```ts
view: {
  type: 'table',
  columnRuntime: {
    disabledResizableKeys: ['actions'],
  },
}
```

也可以统一设置默认宽度范围：

```ts
columnRuntime: {
  defaultWidth: 160,
  minWidth: 80,
  maxWidth: 360,
}
```

### 表头冻结

普通业务列通过表头锁图标冻结。用户点击列标题旁的锁图标后，该列会冻结到左侧；再次点击会取消冻结。

业务页面不应为了普通列写死 `fixed: 'left'` 或 `columnRuntime.freeze.left`，否则页面会缺少明确交互反馈。`columnRuntime.freeze` 只保留给系统级固定列，例如固定右侧的操作列：

```ts
{
  title: '操作',
  key: 'actions',
  width: 110,
  fixed: 'right',
}
```

如果某些列不允许用户冻结，可以关闭：

```ts
columnRuntime: {
  disabledFreezeKeys: ['actions'],
}
```

冻结列依赖横向滚动，表格页应配置 `scrollX`。

### 表格尺寸

表格高度和行高通过 `tableLayout` 统一：

```ts
tableLayout: {
  maxHeight: 520,
  headerHeight: 44,
  minRowHeight: 48,
  rowHeight: 48,
  tableLayout: 'fixed',
}
```

`rowHeight` 可以是固定数字，也可以是 `(row, index) => number`。

### Escape Hatch

`tableProps` 用于透传 Naive UI 的低频能力，但不建议绕过 Runtime 重建表格结构。

## Collection Views

当前集合视图包括：

- `table`
- `card-list`
- `product-list`
- `gallery`

卡片类页面仍然使用同一个 ListPage 外壳，只通过 `item` slot 定义卡片内容：

```vue
<ListPageRuntime :schema="themeListPage" :rows="themes">
  <template #item="{ row }">
    <ThemeCard :theme="row" />
  </template>
</ListPageRuntime>
```

## Constraints

- 页面必须使用 Runtime 提供的 header、filter、toolbar、collection 和 pagination 结构；
- 表格列表默认具备多选列，除非业务明确禁用；
- 普通列冻结由表头锁交互完成，不在业务页写死左侧冻结；
- 主题、CSS 变量和 Appearance System 仍由现有 Theme Runtime 管理。
