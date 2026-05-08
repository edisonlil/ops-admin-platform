# Dark Theme Boundary

第二阶段开始，Appearance preset 支持亮色和暗色两套语义变量。

## Runtime Merge

运行时合并顺序：

1. preset 的 `tokens`
2. 用户的 `tokenOverrides`
3. 用户的 `layoutOverrides`
4. 如果当前是暗色主题，再覆盖 preset 的 `darkSemantic`
5. 如果当前是暗色主题，再覆盖用户的 `tokenOverrides.darkSemantic`

组件 token 继续引用 `semantic` token，因此按钮、菜单、表格、卡片等组件会自动读取当前主题模式下的语义值。

## Editing Rule

语义变量面板会根据当前主题模式编辑不同配置：

- 亮色模式：写入 `tokenOverrides.semantic`
- 暗色模式：写入 `tokenOverrides.darkSemantic`

这可以避免在暗色模式调背景色时污染亮色主题。

## Still Shared

第一阶段暂时共享以下内容：

- primitive token
- component token
- layout token
- skin class

后续如果需要更细粒度控制，可以继续扩展为 `darkComponent` 或完整 theme-mode token set。
