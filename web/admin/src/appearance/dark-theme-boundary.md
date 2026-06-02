# 暗色主题边界

Appearance preset 支持亮色和暗色两套运行时覆盖。暗色模式不只覆盖语义 token，也可以覆盖少量必须与背景同调的组件 token，例如状态标签、告警和表格操作。

## 运行时合并顺序

1. preset 的 `tokens`
2. 用户的 `tokenOverrides`
3. 用户的 `layoutOverrides`
4. 如果当前是暗色主题，再覆盖 preset 的 `darkSemantic`
5. 如果当前是暗色主题，再覆盖用户的 `tokenOverrides.darkSemantic`
6. 如果当前是暗色主题，再覆盖 preset 的 `darkComponent`
7. 最后再次覆盖用户的 `tokenOverrides.component`

组件 token 应优先引用 `semantic` token。只有状态标签、告警、普通 Tag 这类在亮色和暗色中需要不同色阶的组件，才放入 `darkComponent`。

## 编辑规则

语义变量面板会根据当前主题模式写入不同配置：

- 亮色模式：写入 `tokenOverrides.semantic`
- 暗色模式：写入 `tokenOverrides.darkSemantic`

组件变量仍写入 `tokenOverrides.component`，并且在暗色模式下优先级高于 preset 的 `darkComponent`。这样用户手动调过的组件外观不会被暗色默认值覆盖。

## 仍然共享

以下内容在亮色和暗色之间仍然共享：

- primitive token
- layout token
- page token
- skin class

如果后续需要更细粒度的暗色控制，可以继续扩展完整的 theme-mode token set。
