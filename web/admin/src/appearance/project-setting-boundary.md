# Project Setting Boundary

第一阶段迁移目标是消除用户入口上的混乱，而不是把所有项目配置都塞进 token。

## Appearance Token

由 Appearance token 负责：

- 颜色、语义色、组件色
- 字号、圆角、间距、阴影
- 菜单宽度、顶栏高度、内容间距、布局密度
- Naive UI themeOverrides、CSS variables、skin class

## Interface Behavior

由 `projectSettingStore` 继续负责，但统一放到 Appearance Studio 的“界面行为”页签中编辑：

- 导航栏模式
- 导航栏风格
- 分割菜单
- 固定顶栏
- 固定多页签
- 显示重载按钮
- 显示面包屑
- 显示面包屑图标
- 显示多页签
- 页面动画和动画类型

这些值是界面行为，不参与 token resolver。后续后端持久化时，应作为独立 `behavior` 配置保存。
