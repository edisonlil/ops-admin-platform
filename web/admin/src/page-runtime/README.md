# Page Runtime

## Pagination Contract

业务列表必须使用后端分页。请求统一使用 `page` 和 `page_size` 查询参数，其中 `page` 从 1 开始，`page_size` 默认 20，并由后端按接口上限限制。响应统一放在 envelope 的 `data.items` 和 `data.pagination` 下：

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 0
  }
}
```

页面刷新时必须把 Runtime 状态传给接口：

```ts
const payload = await listApi(runtimeListParams(state));
rows.value = payload.items || [];
paginationTotal.value = payload.pagination?.total || 0;
```

`ListPageRuntime` 默认按远程分页处理：翻页和修改每页条数会触发 `refresh(state)`，并直接渲染后端返回的当前页 `rows`，不会再对业务数据做前端切片。业务页面必须通过 `:pagination-total="paginationTotal"` 传入后端总数。只有小型静态面板或非业务本地集合可以显式使用 `pagination: false` 或 `pagination: { remote: false }`。

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

## Runtime Ownership

列表页、表格页和数据视图页必须由 Page Runtime 管理页面结构。业务页面只声明 schema、rows、loading、actions 和必要 slot 内容，不应手写页面级列表布局。

后续如果出现新的列表或数据视图形态，应该先把它建模为正式的 `CollectionViewType` 或 `ListPageRuntime` 视图协议，再由 Runtime 统一渲染。不要因为页面需要 tab、分栏、主从、看板、树、图库、时间线、地图或多表格区域，就在业务页绕过 `ListPageRuntime` 自己组合 `n-tabs`、`n-data-table`、分页、工具条和标题区域。

Runtime 负责保持这些跨页面能力一致：

- 页面标题、说明和 header actions；
- filter、toolbar、collection 和 pagination 的相对位置；
- 表格工具区、刷新、高度铺满、行高密度、列宽拖拽、冻结列；
- 空状态、loading、分页样式和容器边界；
- 不同数据视图之间的密度、间距、圆角和主题变量接入。

业务页可以提供业务动作、字段列定义、卡片 item slot 或详情抽屉，但不能复制 Runtime 的结构性职责。需要新增结构性能力时，扩展 Runtime，而不是在单个页面做局部实现。

## Filter Bar

列表筛选区由 `ListPageRuntime` 和 `AppFilterBar` 统一渲染。业务页只在 `#filters` slot 内放筛选字段，不应手写筛选区外壳、边框、背景、页面级 padding、按钮顺序或字段宽度 CSS。

常规筛选页在 schema 中声明统一动作：

```ts
const listPage = defineListPage<Row>({
  id: 'module.resource',
  title: '资源',
  view: { type: 'table', columns },
  filterBar: {
    showSubmit: true,
    showReset: true,
  },
});
```

业务字段通过 slot 提供，查询和重置动作由 Runtime 负责：

```vue
<ListPageRuntime
  :schema="listPage"
  :rows="rows"
  :loading="loading"
  :pagination-total="paginationTotal"
  @refresh="reload"
  @filter-reset="resetFilters"
>
  <template #filters="{ submit }">
    <n-input v-model:value="filters.keyword" clearable placeholder="搜索名称" @keyup.enter="submit" />
    <n-select v-model:value="filters.status" clearable placeholder="状态" :options="statusOptions" @update:value="submit" />
  </template>
</ListPageRuntime>
```

筛选区规范：

- 查询按钮始终在重置按钮之前，由 `filterBar.showSubmit` / `filterBar.showReset` 控制，不在业务页直接写按钮。
- 查询和重置都会回到第一页，并继续通过 `runtimeListParams(state)` 把 `page`、`page_size` 和排序状态传给后端。
- 业务页的 `@filter-reset` 只负责清空筛选状态，不负责再次调用接口；Runtime 会在清空后统一刷新。
- 输入框的回车查询、选择器的自动查询应调用 slot 暴露的 `submit`，不要直接调用 `reload()` 绕过 Runtime。
- 字段宽度默认使用 Runtime token；需要较宽字段时使用 `filterBar.fieldSize: 'large'`，不要在页面里写 `.xxx__filter { width: ... }`。
- 业务列表筛选必须后端生效。不要先拉取当前页或全量数据再在前端本地过滤来模拟业务筛选。
- 产品可见 placeholder、按钮、字段、状态等文案必须使用中文；遇到乱码先恢复中文。

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
  // 默认不设置 minWidth，让用户拖动列宽时不受统一最小宽度限制。
  // 只有业务列确实需要保护可读性时才显式设置 minWidth。
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
  heightMode: 'fill',
  rowDensity: 'medium',
  maxHeight: 520,
  headerHeight: 44,
  minRowHeight: 48,
  rowHeight: 48,
  tableLayout: 'fixed',
}
```

`rowHeight` 可以是固定数字，也可以是 `(row, index) => number`。

表格列表默认在右侧工具区提供高度铺满和行高密度控件：

- 高度铺满：表格区域使用固定视口高度，内部滚动；
- 不铺满：表格按内容自然高度展开，页面到底部滚动；
- 行高密度：`default` / `medium` / `compact`。

普通业务页不需要自己实现这组工具；只有需要初始状态时才在 `tableLayout` 里声明。

表格工具必须渲染在 CollectionView 容器内部，和表头、表体共用同一个列表边界；不要在筛选区和表格之间单独放置悬浮工具条。

### 分页

所有 Runtime 分页默认支持页大小下拉：

```ts
pagination: {
  pageSize: 20,
  pageSizes: [20, 50, 100],
  showSizePicker: true,
}
```

业务页可以继续传入 Naive UI 的 `PaginationProps` 覆盖当前页、总数等状态，但页大小选项必须保持 `20 / 50 / 100`。

表格内置分页默认应关闭，分页由 `ListPageRuntime` 外置渲染。这样表格边界和分页边界在所有页面中保持一致，避免在表格内部出现额外白底、重复边框或不一致的底部留白。

### Escape Hatch

`tableProps` 用于透传 Naive UI 的低频能力，但不建议绕过 Runtime 重建表格结构。

## Collection Views

当前集合视图包括：

- `table`
- `tabbed-list`
- `basic-list`
- `card-list`
- `product-list`
- `split-list`
- `kanban`
- `calendar`
- `tree`
- `timeline`
- `gallery`
- `map`

### 多列表和多数据视图

同一页面内存在多个同级列表时，使用 `tabbed-list` 或新增等价 Runtime view type。每个 tab/pane 声明自己的 `label`、`count`、`title`、`description`、`rows`、`loading`、`primaryAction`、`view` 和 `pagination`，由 `ListPageRuntime` 统一渲染 tab、pane header、CollectionView、表格工具和外置分页。

不同业务数据视图也应保持同一原则：

- 多 tab 表格：使用 `tabbed-list`；
- 卡片网格：使用 `card-list` 或业务专用 card view；
- 商品/资源图文列表：使用 `product-list` 或扩展专用 view；
- 左右主从：使用 `split-list` 或扩展 master-detail list view；
- 状态流转：使用 `kanban`；
- 层级数据：使用 `tree`；
- 日程数据：使用 `calendar`；
- 事件流：使用 `timeline`；
- 媒体资源：使用 `gallery`；
- 空间资源：使用 `map`。

如果现有 view type 只能显示占位，不要在业务页临时拼装完整 UI；应优先补 Runtime adapter 或新增 view type，再让业务页迁回 schema。

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
- 筛选区字段、查询、重置必须通过 `filterBar` 和 `#filters` slot 接入，业务页不得复制筛选容器样式、按钮顺序或字段宽度；
- 新的列表、表格和数据视图形态必须扩展 Page Runtime 协议，不能在业务页绕过 Runtime 手写同类结构；
- 表格列表默认具备多选列，除非业务明确禁用；
- 普通列冻结由表头锁交互完成，不在业务页写死左侧冻结；
- 表格分页由 Runtime 外置管理，业务页不要开启 `n-data-table` 内置分页来模拟页面分页；
- 主题、CSS 变量和 Appearance System 仍由现有 Theme Runtime 管理。
