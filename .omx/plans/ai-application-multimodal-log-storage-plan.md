# AI 应用多模态日志瘦身方案

## 需求摘要

`ai_application` 在图片、音频、视频等多模态调用中，如果把 `data:image/...;base64,...` 这类大内容直接写进运行日志，会让数据库行变得很重，进而拖慢列表查询、详情查询、分页、排序和前端渲染。

当前风险点已经很明确：

- `prompt_runtime_traces` 主表直接包含 `input_variables_json`、`rendered_messages_json`、`rendered_prompt`、`answer_text` 等大字段，见 `packages/python/ops-admin-ai-applications/src/ai_applications/infrastructure/persistence/ddl.sqlite.sql:57`。
- 写入日志时会把 `input_variables`、`rendered_messages`、`rendered_prompt`、`answer` 一起插入主表，见 `packages/python/ops-admin-ai-applications/src/ai_applications/infrastructure/persistence/repositories.py:569`。
- 列表查询使用 `SELECT *`，再映射出 `input_variables` 和 `answer`，见 `packages/python/ops-admin-ai-applications/src/ai_applications/infrastructure/persistence/repositories.py:624`、`packages/python/ops-admin-ai-applications/src/ai_applications/infrastructure/persistence/repositories.py:638`、`packages/python/ops-admin-ai-applications/src/ai_applications/infrastructure/persistence/repositories.py:690`。
- 应用层列表先按 `page * page_size` 拉取再内存分页，见 `packages/python/ops-admin-ai-applications/src/ai_applications/application/services.py:449`、`packages/python/ops-admin-ai-applications/src/ai_applications/application/services.py:462`。这和项目记忆里的“业务列表必须后端分页”约束不完全一致。
- 多模态运行时会把媒体变量转换成模型消息里的 `image_url` / `input_audio` / `video_url`，当变量里包含 `data_url` 时就会进入渲染消息，见 `packages/python/framework/ops-admin-ai-runtime-core/src/ai_runtime_core/prompt_runtime.py:47`、`packages/python/framework/ops-admin-ai-runtime-core/src/ai_runtime_core/prompt_runtime.py:57`。
- 已有 `file_management` 上下文能保存对象存储引用：`file_objects` 表包含 `storage_provider`、`storage_bucket`、`storage_key`、`sha256`、`size_bytes`，见 `packages/python/ops-admin-file-management/src/file_management/infrastructure/persistence/ddl.sqlite.sql:21`。它也已有 `StoragePort`，见 `packages/python/ops-admin-file-management/src/file_management/application/ports.py:52`。但 AI 应用上下文只能通过端口/服务契约使用文件能力，不能直接依赖或耦合文件领域的内部实现、表结构或 infrastructure。

## 推荐决策

采用 B+C 组合方案：“媒体对象外置 + 日志主表瘦身 + 详情表拆分 + 数据库分页”。

调用模型时允许短暂使用 base64 或模型所需的媒体 URL，但持久化时必须做脱敏和替换：

- 原始文件通过文件能力入口完成上传，AI 运行变量只关联上传后的文件对象引用。AI 应用上下文不直接调用 `file_management.infrastructure`，也不读取 `file_objects` 表；通过 `AiMediaFilePort` 这类应用层端口获取文件元数据、预览 URL 或临时读取能力。
- 如果文件上传能力不可用、上传失败或当前租户没有可用存储配置，则运行仍可继续，但日志不保存原文件、不保存 base64，只保存文件名、mime、大小、变量名和 `storage_status=unavailable` / `redacted=true` 标记。
- 日志主表只保存轻量元数据：文件 ID、对象 key、mime、size、sha256、变量名、预览类型、是否已脱敏。
- `rendered_messages_json` 和 `input_variables_json` 中禁止保存完整 `data_url` / base64。
- 日志列表接口默认不返回大字段，只返回摘要。
- 日志详情接口按 `trace_id` 读取详情，并可按权限生成短时预览 URL 或下载 URL。
- 所有日志列表必须使用数据库分页：SQL 层 `COUNT(*)` + `LIMIT/OFFSET` 或等价游标分页，禁止 `page * page_size` 拉多页数据后在 Python 内存切片。

## 设计原则

1. 主日志表永远轻量化：列表查询不能扫描 base64、完整消息体、大答案全文。
2. 分页必须发生在数据库：列表 SQL 使用 `LIMIT/OFFSET` 和 `COUNT(*)`，不再读取大结果集后切片。
3. 模型调用格式和持久化格式分离：运行时可以构造 provider 需要的消息，落库前必须 sanitize。
4. 文件归文件域管理：可复用 `file_management` 的上传、对象存储、配额、访问日志和预览能力，但必须通过应用层端口或服务契约协作，不能让 `ai_applications` 依赖文件领域内部实现。
5. 文件不可持久化时宁可少记，不可错记：上传不可用时只存文件名/类型/大小/脱敏标记，不保存 base64 或原始二进制。
6. 日志可审计但可控：保留文件 hash、大小、类型、引用、文本摘要，敏感/大内容按策略截断或外置。

## 方案选项

### 选项 A：仅截断 base64 后继续写同一张表

优点：改动小，迁移少。

缺点：仍然把运行详情和列表字段耦合在同一张宽表里；历史数据和未来大答案仍会影响查询；后续加预览、权限、生命周期会继续补丁化。

结论：只能做临时止血，不作为本次目标方案。

### 选项 B：媒体上传到文件管理，日志存引用

优点：根治 base64 入库问题；可通过稳定契约复用 `file_management` 上传、预览、权限、清理和审计能力。

缺点：需要定义 AI 运行变量中的媒体引用契约，并增加 AI 应用侧端口/适配器；还要明确上传不可用时的降级行为。

结论：采纳。

### 选项 C：日志主表和日志详情表拆分

优点：列表性能最稳定，详情还能保留较完整的审计内容。

缺点：需要新增表和迁移历史数据；仍要处理详情表中媒体 base64 的脱敏。

结论：采纳，并与选项 B 组合使用。主表存索引和摘要，详情表存已脱敏后的完整结构。

## 目标数据模型

### 1. `prompt_runtime_traces` 主表瘦身

保留或新增这些适合列表的字段：

- `trace_id`
- `tenant_id`
- `caller_type`
- `caller_key`
- `app_key`
- `app_version`
- `route_key`
- `model_key`
- `provider_key`
- `status`
- `input_preview`
- `answer_preview`
- `usage_json`
- `elapsed_ms`
- `media_count`
- `total_media_bytes`
- `has_redacted_media`
- `storage_status`
- `error_code`
- `error_message`
- `request_id`
- `correlation_id`
- `create_time`

主表不再作为列表来源保存完整 `input_variables_json`、`rendered_messages_json`、`rendered_prompt`、`answer_text`。为兼容迁移，可以先保留列但新写入只写 sanitized/truncated 内容，最终再评估拆除。

### 2. 新增 `prompt_runtime_trace_details`

建议字段：

- `id`
- `tenant_id`
- `trace_id`
- `input_variables_json`：已脱敏，媒体变量为引用对象。
- `rendered_messages_json`：已脱敏，`image_url.url` 不包含 base64。
- `rendered_prompt`
- `answer_text`
- `prompt_refs_json`
- `metadata_json`
- 标准审计字段。

### 3. 媒体引用格式

运行变量中的媒体推荐统一成：

```json
{
  "type": "image",
  "name": "demo.png",
  "mime_type": "image/png",
  "size": 123456,
  "file_ref": "file_42",
  "sha256": "abc...",
  "storage_provider": "minio",
  "storage_bucket": "tenant-assets",
  "storage_key": "ai-runs/tenant/trace/file.png",
  "preview_url": "/api/files/objects/42/preview"
}
```

当文件上传不可用时，引用格式降级为：

```json
{
  "type": "image",
  "name": "demo.png",
  "mime_type": "image/png",
  "size": 123456,
  "file_ref": null,
  "storage_status": "unavailable",
  "redacted": true,
  "reason": "file_upload_unavailable"
}
```

模型调用前，后端根据 provider 能力选择：

- provider 支持公网/签名 URL：传短时 URL。
- provider 只支持 base64：只在内存中读取对象并转 base64，调用结束后不入库。
- 文档类文件：优先抽取文本摘要，文件引用留在变量里。

## 实施步骤

1. 定义媒体变量持久化契约

   在 `packages/python/framework/ops-admin-ai-runtime-core/src/ai_runtime_core/prompt_runtime.py` 增加 helper：识别 `data_url`、计算是否二进制媒体、生成 sanitized media reference。现有 `contains_binary_media` 已能识别二进制媒体，可作为入口。

2. 定义 AI 应用侧文件端口

   在 `ai_applications.application` 增加 `AiMediaFilePort` 或等价契约，只表达 AI 运行需要的能力：上传结果引用、读取临时内容、生成预览 URL、获取文件元数据。端口 DTO 使用 `file_ref`、`name`、`mime_type`、`size`、`sha256` 等中性字段，不暴露 `file_management` 的 repository、表结构或 infrastructure 类型。

3. 接入文件对象上传

   前端 `web/admin/src/views/ai/studio/detail.vue` 当前已经有 image/file/audio/video 变量类型，应改成先上传文件并拿到 `file_id`/元数据，再把轻量引用放进变量，而不是把 base64 长字符串塞进 `variables`。

   降级规则：如果文件上传能力不可用，前端可以继续提交文件名、mime、大小和 `redacted=true` 的占位变量；后端日志只记录该占位信息，不记录原始文件内容。

4. 后端运行前解析媒体引用

   在 `ai_applications.application.services` 的 `prepare_single_turn_run`、`prepare_agent_run`、workflow LLM 节点执行路径中，把文件引用解析为 provider 可用的临时 URL 或内存 base64。运行消息可以包含 provider 需要的格式，但传给 `record_trace` 前必须是 sanitized 版本。

   解析必须通过 `AiMediaFilePort` 完成，禁止从 AI 应用上下文直接 import `file_management.infrastructure` 或直接查 `file_objects`。

5. 拆分日志写入

   修改 `record_trace` 和 `repositories.record_prompt_runtime_trace`：

   - 主表写摘要字段和统计字段。
   - 详情表写 sanitized 详情。
   - `answer_text` 超过阈值时主表只写 `answer_preview`，详情表保存完整或按策略截断。

6. 改造日志列表 SQL 为数据库分页

   替换 `list_prompt_runtime_traces`、`list_ai_application_run_logs`、`list_ai_capability_run_logs` 的 `SELECT *` 和应用层 `read_list` 切片。列表 SQL 只选择轻量列，并用数据库层 `COUNT(*)` + `LIMIT/OFFSET` 返回 `data.items` 和 `data.pagination`，满足项目后端分页约束。

7. 增加日志详情接口

   保留列表接口轻量；新增或强化 `GET /ai-runtime/prompt-runtime/traces/{trace_id}`，按 trace_id 读取详情表，并按租户权限返回媒体引用、预览 URL、脱敏状态。

8. 调试环境历史数据处理

   当前环境是调试环境，历史 trace 数据不做兼容治理，也不新增历史迁移脚本。处理策略二选一：

   - 直接忽略旧日志，只保证新写入不再保存 base64。
   - 在开发库中手动清空旧 `prompt_runtime_traces` 及其详情表数据，释放空间并避免旧数据影响调试。

   运行时代码不得自动清理或迁移历史数据；如需清空，由开发/运维手动执行明确 SQL 或初始化脚本。

9. 前端展示调整

   日志列表只展示输入摘要、媒体数量、耗时、状态、模型、时间。

   日志详情抽屉按需加载详情；媒体显示为文件名、大小、类型、缩略图/预览按钮，不展示 base64。

## 验收标准

- 新产生的 `prompt_runtime_traces` 行中不出现长度超过 8KB 的 base64 data URL。
- `ai_applications` 不直接 import `file_management.infrastructure`，不直接查询 `file_objects`，只通过应用层端口/服务契约使用文件能力。
- 日志列表接口不返回 `rendered_messages_json`、完整 `input_variables`、完整 `answer` 等大字段。
- 日志列表 SQL 使用数据库层 `LIMIT/OFFSET` 和 `COUNT(*)`，不再 `SELECT *` 后应用层切片，也不再用 `page * page_size` 预取多页。
- 图片分析、音频分析、普通文本调用都能成功，且 trace 详情能看到媒体文件名、大小、mime、sha256、预览入口。
- provider 需要 base64 时，base64 只存在于请求构造过程，不落库、不进入响应日志。
- 文件上传能力不可用时，运行日志只保存文件名、mime、大小、变量名、`storage_status=unavailable` 和脱敏标记，不保存原文件、不保存 base64。
- 调试环境历史数据不要求迁移；旧日志可忽略或由开发/运维手动清空。验收只关注新写入日志不再保存 base64。

## 风险与缓解

- 风险：某些模型 provider 必须接收 base64。
  缓解：在 provider adapter 层临时从对象存储读出并编码，落库前统一 sanitize。

- 风险：现有前端已依赖 `input_variables` 展示完整输入。
  缓解：列表返回 preview，详情接口按需返回 sanitized detail；前端改为详情抽屉加载。

- 风险：调试环境旧日志已经很大。
  缓解：不做历史兼容治理；开发库可手动清空旧 trace 数据，重点保证新写入路径正确。

- 风险：跨领域耦合导致后续 scaffold sync 或文件领域调整时破坏 AI 应用。
  缓解：AI 应用只定义并依赖 `AiMediaFilePort`，组合层/适配器负责桥接文件能力；架构测试禁止 `ai_applications` 直接 import `file_management.infrastructure` 或 repository。

- 风险：文件上传服务不可用影响 AI 调用。
  缓解：按业务要求降级为不持久化原文件，只记录文件名和脱敏标记；如果模型调用本身必须读取文件，则返回明确的运行错误，不把 base64 写进日志兜底。

## 验证步骤

1. 单元测试：`sanitize_trace_payload` 能替换嵌套 dict/list 中的 `data_url`、`image_url.url`、`input_audio.data`。
2. 仓储测试：插入含图片变量的 trace 后，主表行大小可控，详情表含引用不含 base64。
3. API 测试：日志列表返回 `items/pagination`，且 items 不含大字段；测试必须证明分页由 SQL `LIMIT/OFFSET` 完成。
4. 集成测试：上传图片 -> 运行 AI 应用 -> 模型收到可用图片 -> 列表不卡顿 -> 详情可预览引用。
5. 降级测试：模拟文件上传不可用 -> 运行日志只保存文件名/类型/大小/脱敏标记 -> 数据库中不出现 base64。
6. 性能测试：构造 1000 条含 2MB 图片的历史 trace，列表 p95 应稳定在可接受阈值，例如本地 SQLite 小于 300ms，生产库按实际基线设定。

## ADR

### Decision

多模态文件不再以 base64 形式持久化到 AI 应用日志主表。文件通过文件能力入口上传后与 AI 运行关联；AI 应用只通过端口/服务契约使用文件能力，不依赖或耦合文件领域内部实现。日志主表保存摘要和引用，详情表保存已脱敏的结构化运行详情。文件上传能力不可用时，不保存文件内容，只保存文件名、类型、大小和脱敏标记。日志列表必须使用数据库分页。

### Drivers

- 列表查询必须稳定，分页必须由数据库执行。
- 日志要可审计，但不能把二进制内容塞进关系库热表。
- 当前项目已有文件管理能力，应通过稳定契约复用而不是重建，也不能跨领域直接耦合。

### Alternatives Considered

- 只截断 base64：能快速止血，但没有解决宽表和列表 `SELECT *` 的结构问题。
- 只拆详情表：能改善列表，但如果详情继续存 base64，数据库仍会膨胀。
- 完全不记录输入：性能最好，但审计和问题追踪能力不足。

### Why Chosen

“文件能力端口 + 文件上传关联 + 主表摘要 + 详情按需加载 + 数据库分页”同时满足性能、审计、权限和后续扩展，且最符合现有 DDD 边界：文件由文件领域管理，AI 运行日志由 `ai_applications` 管，双方通过应用层契约协作。

### Consequences

- 需要一次 schema 迁移和前后端契约调整。
- 需要增加 AI 应用侧文件端口和组合层适配器，避免跨领域耦合。
- 调试环境不新增历史治理脚本；旧数据可忽略或手动清空。
- 未来所有 AI trace 相关列表都要区分 summary 和 detail。

### Follow-ups

- 确认生产环境对象存储和短时 URL 策略。
- 给 `trace_policy` 增加字段级保留策略，例如 `store_inputs`、`store_outputs`、`max_answer_chars`、`media_retention_days`。
- 给 `file_management` 或 AI 媒体引用增加按 trace 清理的生命周期任务。
