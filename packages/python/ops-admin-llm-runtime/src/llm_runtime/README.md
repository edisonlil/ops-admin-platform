# llm_runtime

`llm_runtime` 是系统内统一�?LLM Gateway / Model Router bounded context。它负责管理模型供应商、模型目录、业务任务注册、路由策略、运行时调用和调用观测。业务领域不直接维护 API Key、供应商、模型名�?fallback 规则�?

## 职责边界

`llm_runtime` 负责�?

- 维护供应商连接信息，例如通义百炼、硅基流动、MiniMax�?
- 维护模型目录，包括模型名、供应商、能力标签和启用状态�?
- 维护业务 LLM 任务注册表，例如 `function_point.recommendation.rank`�?
- 维护数据库中的模型路由策略，包括优先级、fallback、温度、超时、响应格式和扩展参数�?
- 提供统一调用入口，例�?`llm_gateway.generate(...)`�?
- 记录调用日志、命中模型、耗时、token、错误和 fallback 信息�?
- 对外提供后台管理 HTTP API，所有业务响应使用统一 envelope�?

`llm_runtime` 不负责：

- 具体业务 prompt 的构造�?
- 业务结果解析和业务规则判断�?
- 直接依赖任一业务领域�?infrastructure�?
- 把模型配置长期维护在 `.json` 文件中�?

业务领域负责�?

- 声明自己需要的 LLM 任务�?
- 在业务应用服务中调用 `llm_runtime` �?application port�?
- 维护本领�?README，说明任务清单、调用方式、依赖关系和集成约束�?

## 数据库优先原�?

模型配置的权威来源是数据库。后台页面、运行时调用和测试夹具都应优先围绕数据库模型设计�?

`.json` 配置只允许作为历史兼容或本地临时调试入口，不作为长期维护方式。新增供应商、模型、任务和路由策略时，应优先增�?bounded context 自有�?DDL、repository/use case �?HTTP API�?

## 初始�?
数据库初始化是显式运维动作，业务运行期不会自动建表、迁移、补列或 seed。初始化或迁移环境时手动执行�?
```bash
python scripts/init_llm_runtime.py
```

## 核心概念

### Provider

供应商连接配置，例如�?

- `dashscope`: 通义百炼�?
- `siliconflow`: 硅基流动�?
- `minimax`: MiniMax�?

Provider 保存连接层信息：`provider_key`、展示名称、Base URL、API Key、启用状态、扩展鉴权或请求参数�?

### Model

某个供应商下可调用的模型，例如：

- `dashscope.qwen-plus`
- `siliconflow.qwen3-32b`
- `minimax.m2_7`

Model 保存模型层信息：`model_key`、`provider_key`、供应商真实模型名、能力标签、上下文长度、是否支�?JSON、是否支�?reasoning 输出、启用状态�?

### Task

业务模型任务。Task 表示“业务要完成什么”，不表示“用哪个模型”�?

命名建议使用三段或四段式�?

```text
领域.场景.任务
领域.场景.子任�?
```

示例�?

```text
function_point.recommendation.recall_plan
function_point.recommendation.rank
function_point.recommendation.evaluate
knowledge.qa.rewrite_query
knowledge.qa.answer
document.parse.extract_outline
```

业务代码应集中声�?task key，不要散写字符串�?

### Routing Policy

路由策略决定某个 task 使用哪些模型、按什么顺序尝试、每个候选模型使用什么参数�?

路由支持兜底层级�?

```text
function_point.recommendation.rank
function_point.recommendation.default
function_point.default
default
```

运行时按顺序查找第一个启用策略�?

## 建议数据模型

第一版建议实现以下表�?

### llm_providers

```text
id
provider_key
display_name
base_url
api_key
auth_type
extra_headers
extra_body
enabled
create_time
update_time
```

约束�?

- `provider_key` 唯一�?
- API Key 只在运行时配置中出现，HTTP 读取接口只能返回脱敏信息�?
- 禁用 provider 后，关联模型不可被运行时命中�?

### llm_models

```text
id
model_key
provider_key
model_name
display_name
capabilities
context_window
enabled
create_time
update_time
```

约束�?

- `model_key` 唯一�?
- `provider_key` 关联 `llm_providers.provider_key`�?
- `model_name` 是供应商真实请求模型名�?

### llm_tasks

```text
id
task_key
context_key
scene_key
task_name
display_name
description
owner_context
enabled
create_time
update_time
```

约束�?

- `task_key` 唯一�?
- Task 由业务领域声明并注册到数据库�?
- 后台页面展示 task，但不鼓励管理员临时发明业务 task�?

### llm_routing_policies

```text
id
route_key
display_name
strategy
enabled
create_time
update_time
```

约束�?

- `route_key` 唯一�?
- `route_key` 可以是精�?task，也可以是兜�?key，例�?`function_point.default`�?
- 第一版只实现 `priority` 策略�?

### llm_routing_policy_entries

```text
id
policy_id
model_key
priority
temperature
timeout_seconds
max_retries
response_format
extra_body
enabled
create_time
update_time
```

约束�?

- 同一 policy 下按 `priority ASC` 尝试�?
- 单个 entry 可禁用�?
- `response_format` 第一版支�?`text` �?`json`�?
- 只有超时、限流�?xx、供应商临时错误等可恢复错误触发 fallback�?

### llm_call_logs

```text
id
task_key
route_key
policy_id
entry_id
provider_key
model_key
model_name
status
is_fallback
elapsed_ms
prompt_tokens
completion_tokens
total_tokens
error_code
error_message
request_id
correlation_id
create_time
```

约束�?

- 日志不保存完�?prompt 和模型输出，避免敏感数据泄漏�?
- 如需调试内容，应设计单独的受�?trace 存储和脱敏策略�?

## 路由解析流程

调用�?

```python
llm_gateway.generate(
    task_key=FunctionPointLLMTask.RECOMMENDATION_RANK,
    messages=messages,
    response_format="json",
)
```

运行时流程：

```text
1. 根据 task_key 生成候�?route_key�?
2. 查找第一�?enabled �?llm_routing_policies�?
3. 读取 policy �?enabled �?entries，按 priority 排序�?
4. 对每�?entry 解析 model �?provider�?
5. 创建供应商客户端并调用模型�?
6. 成功后返�?LLMResponse�?
7. 可恢复错误时记录日志并尝试下一�?entry�?
8. 全部失败后抛出稳定的运行时错误�?
```

候�?route_key 示例�?

```text
function_point.recommendation.rank
function_point.recommendation.default
function_point.default
default
```

## 业务调用方式

业务领域不应直接实例化供应商客户端。推荐通过 application port 调用�?

```python
from llm_runtime.application.gateway import llm_gateway

response = llm_gateway.generate(
    task_key=FunctionPointLLMTask.RECOMMENDATION_RANK,
    messages=[
        {"role": "user", "content": prompt},
    ],
    response_format="json",
)
```

兼容期内，已�?`build_llm_client(role=...)` 可以保留，但新代码应逐步迁移�?Gateway。旧�?`role` 参数应映射到新的 `task_key`�?

## HTTP 管理接口建议

后台管理接口建议按资源拆分：

```text
GET    /api/llm/providers
POST   /api/llm/providers
PUT    /api/llm/providers/{provider_key}

GET    /api/llm/models
POST   /api/llm/models
PUT    /api/llm/models/{model_key}

GET    /api/llm/tasks
POST   /api/llm/tasks/register

GET    /api/llm/routing-policies
POST   /api/llm/routing-policies
PUT    /api/llm/routing-policies/{route_key}

GET    /api/llm/call-logs

GET    /api/llm/openai/v1/models
POST   /api/llm/openai/v1/chat/completions
```

管理�?HTTP 响应必须使用统一 envelope。列表接口必须把数据放在 `data.items` �?`data.pagination` 下�?

OpenAI 兼容接口用于外部系统和后台模型调试页直接调用已配置模型：

- `GET /api/llm/openai/v1/models` 返回 OpenAI 风格的模型列表，包含已启用的 `model_key` 和已启用�?`route_key`�?
- `POST /api/llm/openai/v1/chat/completions` 请求体兼�?OpenAI Chat Completions。`model` 可以传数据库中的 `model_key`/供应商真�?`model_name`，也可以�?`route_key`/业务 `task_key`�?
- �?`model` 命中模型目录时，调用该模型所�?provider；当 `model` 未命中模型目录时，按路由策略解析并支�?fallback�?
- 兼容接口需要登录态或 `X-API-Key`，但响应形状保持 OpenAI 风格，不包统一 envelope，方�?SDK 和外部调用方接入�?

示例�?

```bash
curl -X POST http://localhost:8000/api/llm/openai/v1/chat/completions \
  -H "X-API-Key: <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "function_point.recommendation.rank",
    "messages": [{"role": "user", "content": "ping"}],
    "temperature": 0.1
  }'
```

## 领域 README 约定

后续每个 bounded context 都应在根目录维护 `README.md`，说明以下内容：

- 职责范围：本领域解决什么问题，不解决什么问题�?
- 模块结构：domain、application、infrastructure、interfaces 的职责�?
- 对外能力：HTTP API、application service、事件或端口�?
- 外部依赖：依赖哪些其�?context �?application port �?domain event�?
- LLM 集成：声明哪�?task key、prompt 构造位置、返回解析位置、错误处理方式�?
- 数据库资源：本领域拥有的表、DDL �?seed 位置�?
- 测试策略：核心用例测试、架构边界测试和需要运行的命令�?

领域 README 不应暴露供应商密钥、具体线上模型选择或运维私密配置。模型选择应链接到 `llm_runtime` 的数据库路由策略�?

## function_point 集成示例

`function_point` 可以声明�?

```python
class FunctionPointLLMTask:
    RECOMMENDATION_RECALL_PLAN = "function_point.recommendation.recall_plan"
    RECOMMENDATION_RANK = "function_point.recommendation.rank"
    RECOMMENDATION_EVALUATE = "function_point.recommendation.evaluate"
```

推荐流程中：

- recall planner 调用 `function_point.recommendation.recall_plan`�?
- ranker 调用 `function_point.recommendation.rank`�?
- evaluator 调用 `function_point.recommendation.evaluate`�?

后台可以配置�?

```text
function_point.recommendation.rank
  priority 1 -> dashscope.qwen-plus
  priority 2 -> siliconflow.qwen3-32b

function_point.recommendation.default
  priority 1 -> dashscope.qwen-turbo

default
  priority 1 -> minimax.m2_7
```

## 迁移计划

第一阶段�?

- 保留现有 `/api/llm-config` �?`llm_configs`，作为默认模型兼容入口�?
- 新增 provider、model、task、routing policy 表�?
- 把现有单配置迁移�?`default` route�?

第二阶段�?

- 新增 Gateway 调用入口�?
- `function_point` �?recall/rank/eval 从旧 role 迁移�?task key�?
- 后台页面改为维护供应商、模型和路由策略�?

第三阶段�?

- 增加调用日志页面�?
- 增加 fallback 观测、禁�?entry、模型健康状态�?
- 逐步废弃 `.json` 作为运行时配置来源�?

## 实现约束

- `domain` 不依�?FastAPI、数据库客户端、HTTP 客户端或供应�?SDK�?
- `application` 定义用例、路由解析、事务边界和端口�?
- `infrastructure` 实现数据�?repository 和供应商客户端适配器�?
- `interfaces/http` 只负�?DTO、鉴权、调�?application service �?envelope 映射�?
- 跨领域调用只能依�?application port �?domain event，不直接导入其他 context �?infrastructure�?
- 新增表必须同时提�?SQLite �?PostgreSQL DDL�?
- 新增运行时行为必须补�?application use case 测试和架构边界测试�?
