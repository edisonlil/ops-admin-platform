# Page Runtime

`page-runtime` 是后台页面协议层。新列表页和详情页默认从这里开始，而不是在业务页面里自由拼装 header、search、toolbar、collection 和 pagination。

## 允许

- 使用 `defineListPage()` / `ListPageRuntime` 创建基础列表、卡片列表、商品列表、双栏列表、表格、看板、日历、树、时间线等页面。
- 使用 `defineDetailPage()` / `DetailPageRuntime` 创建 profile、form、workspace 及其业务子类详情页。
- 通过命名 slot 扩展协议允许的位置，例如 `filters`、`toolbar-left`、`toolbar-right` 和 collection cell slots。
- 新增 collection view 时先注册 view type，再实现 adapter。

## 禁止

- 新页面直接使用 `.n-layout-page-header`。
- 在列表页里让 table/card 自己拥有页面标题、页面搜索区或全局 toolbar。
- 使用 card 套 card 制造页面结构。
- 在业务页面局部 CSS 覆盖协议 spacing、filter gap、toolbar layout 或 pagination placement。
- 新增任意布局 DSL 或拖拽页面搭建能力。
