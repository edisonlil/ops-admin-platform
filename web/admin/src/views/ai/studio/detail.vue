<template>
  <DetailPageRuntime :schema="detailPage">
    <n-spin :show="loading">
      <nav class="studio-workspace-nav" aria-label="AI 应用工作区">
        <button
          v-for="item in workspaceTabs"
          :key="item.key"
          class="studio-workspace-nav__item"
          :class="{ 'is-active': activeWorkspace === item.key }"
          type="button"
          @click="switchWorkspace(item.key)"
        >
          <span>{{ item.label }}</span>
          <small>{{ item.description }}</small>
        </button>
      </nav>

      <AgentChatRuntime
        v-if="activeWorkspace === 'agent' && isAgentMode && form.app_key"
        :app-key="form.app_key"
        v-model:model-value="selectedModelKey"
        :model-options="modelConfigOptions"
        :model-loading="modelConfigLoading"
        :saving="saving"
        @save-config="() => saveCurrent()"
      />

      <div v-if="activeWorkspace === 'orchestration' && isWorkflowMode" class="workflow-fullscreen">
        <main class="workflow-canvas-shell">
          <section class="workflow-canvas-toolbar">
            <div>
              <span>Workflow 编排</span>
              <small>右键画布添加节点，拖动节点连接运行路径</small>
            </div>
            <n-space size="small">
              <n-button v-if="selectedWorkflowEdgeId" size="small" secondary type="error" @click="deleteWorkflowEdge()">删除连线</n-button>
              <n-button size="small" tertiary @click="runDraft">{{ workflowRunPanelVisible ? '收起预览' : '预览运行' }}</n-button>
            </n-space>
          </section>
          <section ref="workflowCanvasPanelRef" class="workflow-canvas-panel">
            <VueFlow
              id="workflow-editor"
              v-model:nodes="workflowNodes"
              v-model:edges="workflowEdges"
              class="workflow-canvas"
              fit-view-on-init
              :default-edge-options="{ type: 'smoothstep' }"
              @connect="handleWorkflowConnect"
              @edge-click="handleWorkflowEdgeClick"
              @node-click="handleWorkflowNodeClick"
              @pane-click="handleWorkflowPaneClick"
              @pane-context-menu="handleWorkflowPaneContextMenu"
            >
              <template #node-start="{ id, data, selected }">
                <div class="workflow-node-card workflow-node-card--start" :class="workflowNodeCardClass(id, selected)">
                  <Handle type="source" :position="Position.Right" />
                  <div class="workflow-node-card__actions">
                    <button type="button" title="运行此步骤" @click.stop="runWorkflowNode(id)">▶</button>
                    <button type="button" title="节点操作" @click.stop="toggleWorkflowNodeMenu(id)">...</button>
                  </div>
                  <div class="workflow-node-card__head">
                    <span class="workflow-node-card__icon">S</span>
                    <strong>{{ data.label || '开始' }}</strong>
                  </div>
                  <p>{{ workflowStartVariableCount(data) ? `已定义 ${workflowStartVariableCount(data)} 个入口变量` : '定义运行入口变量' }}</p>
                  <div v-if="openWorkflowNodeMenuId === id" class="workflow-node-menu" @click.stop>
                    <button type="button" @click="openWorkflowNodeConfig(id)">更改节点</button>
                    <button type="button" @click="runWorkflowNode(id)">运行此步骤</button>
                    <button type="button" disabled>删除</button>
                  </div>
                </div>
              </template>

              <template #node-llm="{ id, data, selected }">
                <div class="workflow-node-card workflow-node-card--llm" :class="workflowNodeCardClass(id, selected)">
                  <Handle type="target" :position="Position.Left" />
                  <Handle type="source" :position="Position.Right" />
                  <div class="workflow-node-card__actions">
                    <button type="button" title="运行此步骤" @click.stop="runWorkflowNode(id)">▶</button>
                    <button type="button" title="节点操作" @click.stop="toggleWorkflowNodeMenu(id)">...</button>
                  </div>
                  <div class="workflow-node-card__head">
                    <span class="workflow-node-card__icon">AI</span>
                    <strong>{{ data.label || 'LLM' }}</strong>
                  </div>
                  <div class="workflow-node-card__meta">{{ data.model || '未选择模型' }}</div>
                  <p>{{ data.user_prompt_template || '调用大模型生成文本' }}</p>
                  <div v-if="openWorkflowNodeMenuId === id" class="workflow-node-menu" @click.stop>
                    <button type="button" @click="runWorkflowNode(id)">运行此步骤</button>
                    <button type="button" @click="openWorkflowNodeConfig(id)">更改节点</button>
                    <button type="button" @click="duplicateWorkflowNode(id)">复制</button>
                    <button type="button" class="is-danger" @click="deleteWorkflowNode(id)">删除</button>
                  </div>
                </div>
              </template>

              <template #node-sql_query="{ id, data, selected }">
                <div class="workflow-node-card workflow-node-card--sql" :class="workflowNodeCardClass(id, selected)">
                  <Handle type="target" :position="Position.Left" />
                  <Handle type="source" :position="Position.Right" />
                  <div class="workflow-node-card__actions">
                    <button type="button" title="运行此步骤" @click.stop="runWorkflowNode(id)">▶</button>
                    <button type="button" title="节点操作" @click.stop="toggleWorkflowNodeMenu(id)">...</button>
                  </div>
                  <div class="workflow-node-card__head">
                    <span class="workflow-node-card__icon">SQL</span>
                    <strong>{{ data.label || 'SQL 查询' }}</strong>
                  </div>
                  <div class="workflow-node-card__meta">输出：{{ data.output_key || 'records' }}</div>
                  <p class="workflow-node-card__sql-preview" :title="String(data.sql || '')">
                    {{ compactSqlPreview(data.sql) }}
                  </p>
                  <div v-if="openWorkflowNodeMenuId === id" class="workflow-node-menu" @click.stop>
                    <button type="button" @click="runWorkflowNode(id)">运行此步骤</button>
                    <button type="button" @click="openWorkflowNodeConfig(id)">更改节点</button>
                    <button type="button" @click="duplicateWorkflowNode(id)">复制</button>
                    <button type="button" class="is-danger" @click="deleteWorkflowNode(id)">删除</button>
                  </div>
                </div>
              </template>

              <template #node-condition="{ id, data, selected }">
                <div class="workflow-node-card workflow-node-card--condition" :class="workflowNodeCardClass(id, selected)">
                  <Handle type="target" :position="Position.Left" />
                  <Handle
                    id="true"
                    type="source"
                    :position="Position.Right"
                    class="workflow-node-card__branch-handle workflow-node-card__branch-handle--true"
                  />
                  <Handle
                    id="false"
                    type="source"
                    :position="Position.Right"
                    class="workflow-node-card__branch-handle workflow-node-card__branch-handle--false"
                  />
                  <div class="workflow-node-card__actions">
                    <button type="button" title="运行此步骤" @click.stop="runWorkflowNode(id)">▶</button>
                    <button type="button" title="节点操作" @click.stop="toggleWorkflowNodeMenu(id)">...</button>
                  </div>
                  <div class="workflow-node-card__head">
                    <span class="workflow-node-card__icon">IF</span>
                    <strong>{{ data.label || '条件判断' }}</strong>
                  </div>
                  <div class="workflow-node-branch">
                    <strong>是</strong>
                    <span>{{ data.left || '变量' }} {{ conditionOperatorLabel(data.operator) }} {{ data.right || '' }}</span>
                  </div>
                  <div class="workflow-node-branch">
                    <strong>否</strong>
                    <span>不满足条件时进入此分支</span>
                  </div>
                  <p>按变量结果选择后续路径</p>
                  <div v-if="openWorkflowNodeMenuId === id" class="workflow-node-menu" @click.stop>
                    <button type="button" @click="runWorkflowNode(id)">运行此步骤</button>
                    <button type="button" @click="openWorkflowNodeConfig(id)">更改节点</button>
                    <button type="button" @click="duplicateWorkflowNode(id)">复制</button>
                    <button type="button" class="is-danger" @click="deleteWorkflowNode(id)">删除</button>
                  </div>
                </div>
              </template>

              <template #node-end="{ id, data, selected }">
                <div class="workflow-node-card workflow-node-card--end" :class="workflowNodeCardClass(id, selected)">
                  <Handle type="target" :position="Position.Left" />
                  <div class="workflow-node-card__actions">
                    <button type="button" title="节点操作" @click.stop="toggleWorkflowNodeMenu(id)">...</button>
                  </div>
                  <div class="workflow-node-card__head">
                    <span class="workflow-node-card__icon">E</span>
                    <strong>{{ data.label || '结束' }}</strong>
                  </div>
                  <p>{{ data.output || '输出最终结果' }}</p>
                  <div v-if="openWorkflowNodeMenuId === id" class="workflow-node-menu" @click.stop>
                    <button type="button" @click="openWorkflowNodeConfig(id)">更改节点</button>
                    <button type="button" @click="duplicateWorkflowNode(id)">复制</button>
                    <button type="button" class="is-danger" @click="deleteWorkflowNode(id)">删除</button>
                  </div>
                </div>
              </template>

              <Background />
              <Controls />
            </VueFlow>
            <div
              v-if="workflowCanvasMenu.visible"
              class="workflow-canvas-menu"
              :style="{ left: `${workflowCanvasMenu.x}px`, top: `${workflowCanvasMenu.y}px` }"
              @click.stop
              @contextmenu.prevent
            >
              <div class="workflow-canvas-menu__title">添加节点</div>
              <button type="button" @click="addWorkflowNodeFromCanvasMenu('llm')">
                <strong>LLM</strong>
                <span>调用模型生成文本</span>
              </button>
              <button type="button" @click="addWorkflowNodeFromCanvasMenu('sql_query')">
                <strong>SQL 查询</strong>
                <span>执行只读 SQL 并输出变量</span>
              </button>
              <button type="button" @click="addWorkflowNodeFromCanvasMenu('condition')">
                <strong>条件判断</strong>
                <span>按变量选择分支</span>
              </button>
              <button type="button" @click="addWorkflowNodeFromCanvasMenu('end')">
                <strong>结束</strong>
                <span>输出最终结果</span>
              </button>
            </div>
          </section>

          <aside v-if="workflowRunPanelVisible" class="workflow-run-panel">
            <header class="workflow-run-panel__head">
              <div>
                <h3>预览</h3>
                <span>{{ running ? '正在执行 Workflow' : runResult?.trace ? '最近一次执行结果' : '填写入口变量后运行' }}</span>
              </div>
              <div class="workflow-run-panel__actions">
                <n-button size="tiny" quaternary :disabled="running" @click="resetWorkflowDebugRun">重置</n-button>
                <button type="button" class="workflow-run-panel__close" aria-label="关闭预览面板" @click="workflowRunPanelVisible = false">×</button>
              </div>
            </header>

            <section class="workflow-run-panel__section">
              <div class="workflow-run-panel__section-head">
                <strong>开始节点入口变量</strong>
                <span>{{ workflowInputVariableFields.length }} 个变量</span>
              </div>
              <div v-if="workflowInputVariableFields.length" class="workflow-run-inputs">
                <div v-for="field in workflowInputVariableFields" :key="field.key" class="workflow-run-input">
                  <label>
                    <span>{{ field.label }}</span>
                    <em v-if="field.required">*</em>
                  </label>
                  <n-select
                    v-if="field.options?.length"
                    v-model:value="runtimeVariableValues[field.key]"
                    clearable
                    :options="field.options"
                    :placeholder="field.placeholder"
                  />
                  <n-switch v-else-if="field.type === 'boolean'" v-model:value="runtimeVariableValues[field.key]" />
                  <n-input-number
                    v-else-if="field.type === 'number'"
                    v-model:value="runtimeVariableValues[field.key]"
                    clearable
                    :placeholder="field.placeholder"
                    class="runtime-variable-number"
                  />
                  <n-upload
                    v-else-if="isMediaVariableField(field)"
                    :accept="mediaVariableAccept(field)"
                    :default-upload="false"
                    :max="1"
                    @change="(options) => handleMediaVariableChange(field, options)"
                  >
                    <n-upload-dragger>
                      <div class="runtime-media-upload__title">{{ mediaVariableUploadTitle(field) }}</div>
                      <div class="runtime-media-upload__hint">{{ mediaVariableUploadHint(field) }}</div>
                    </n-upload-dragger>
                  </n-upload>
                  <n-input v-else v-model:value="runtimeVariableValues[field.key]" clearable :placeholder="field.placeholder" />
                  <div v-if="isMediaVariableField(field) && mediaVariableValue(field.key)" class="runtime-media-file">
                    <span>{{ mediaVariableValue(field.key)?.name }}</span>
                    <span>{{ formatBytes(mediaVariableValue(field.key)?.size || 0) }}</span>
                  </div>
                </div>
              </div>
              <n-empty v-else size="small" description="开始节点未定义入口变量，运行时将使用空变量对象。" />
              <n-button block type="primary" :loading="running" @click="confirmWorkflowRun">
                {{ running ? '运行中' : '运行 Workflow' }}
              </n-button>
            </section>

            <section class="workflow-run-panel__section workflow-run-panel__section--logs">
              <div class="workflow-run-panel__section-head">
                <strong>执行日志</strong>
                <span>{{ workflowTraceNodes.length ? `${workflowTraceNodes.length} 个节点` : workflowRunStatusText }}</span>
              </div>
              <div v-if="workflowTraceNodes.length" class="workflow-trace-list">
                <details
                  v-for="traceNode in workflowTraceNodes"
                  :key="`${traceNode.node_id}-${traceNode.node_type}`"
                  class="workflow-trace-item"
                  :class="`is-${workflowTraceStatus(traceNode)}`"
                  :open="traceNode.status === 'failed'"
                >
                  <summary>
                    <span class="workflow-trace-item__icon">{{ workflowTraceNodeIcon(traceNode.node_type) }}</span>
                    <span class="workflow-trace-item__title">{{ workflowTraceNodeTitle(traceNode) }}</span>
                    <span v-if="traceNode.branch" class="workflow-trace-item__branch">{{ traceNode.branch === 'true' ? '是' : '否' }}</span>
                    <span class="workflow-trace-item__elapsed">{{ formatElapsedSeconds(traceNode.elapsed_ms) }} 秒</span>
                    <span class="workflow-trace-item__status"></span>
                  </summary>
                  <div class="workflow-trace-item__body">
                    <div v-if="traceNode.error" class="workflow-trace-item__error">{{ traceNode.error }}</div>
                    <div>
                      <strong>输出</strong>
                      <pre>{{ stringifyJson(traceNode.output || {}) }}</pre>
                    </div>
                  </div>
                </details>
              </div>
              <div v-else-if="running || workflowRunStatusText !== '等待运行'" class="workflow-trace-placeholder">
                <span class="rendering-spinner"></span>
                <span>{{ workflowRunStatusText }}，节点日志会在后端返回 trace 后展开...</span>
              </div>
              <div v-else-if="workflowRunErrorText" class="workflow-trace-error">
                {{ workflowRunErrorText }}
              </div>
              <n-empty v-else size="small" description="点击上方“运行 Workflow”后展示每个节点的输入输出、耗时和状态。" />
            </section>

            <section v-if="previewAnswerText" class="workflow-run-panel__answer">
              <strong>最终输出</strong>
              <div v-html="previewRenderedOutput.kind === 'markdown' ? previewRenderedOutput.content : ''"></div>
              <pre v-if="previewRenderedOutput.kind !== 'markdown'">{{ previewRenderedOutput.rawContent || previewRenderedOutput.content }}</pre>
            </section>
          </aside>

          <section
            v-if="selectedWorkflowNode"
            class="workflow-floating-panel"
            :class="{ 'is-run-panel-open': workflowRunPanelVisible }"
          >
            <template v-if="selectedWorkflowNode">
              <header>
                <div>
                  <h3>{{ workflowNodeTitle(selectedWorkflowNode) }}</h3>
                  <span>{{ workflowNodeTypeLabel(selectedWorkflowNode.type || 'llm') }} · {{ selectedWorkflowNode.id }}</span>
                </div>
                <button type="button" aria-label="关闭节点配置" @click="selectedWorkflowNodeId = ''">×</button>
              </header>
              <n-form label-placement="top" class="studio-form">
                <n-form-item label="节点名称">
                  <n-input v-model:value="selectedWorkflowNode.data.label" />
                </n-form-item>
                <template v-if="selectedWorkflowNode.type === 'start'">
                  <section class="workflow-start-variables">
                    <div class="workflow-start-variables__head">
                      <div>
                        <h4>运行入口变量</h4>
                        <span>这些变量会同步到调试表单、访问 API 和后端变量校验。</span>
                      </div>
                      <n-button size="tiny" secondary @click="addWorkflowStartVariable(selectedWorkflowNode)">添加变量</n-button>
                    </div>
                    <div v-if="workflowStartVariables.length" class="workflow-start-variable-list">
                      <div
                        v-for="(variable, index) in workflowStartVariables"
                        :key="variable.id"
                        class="workflow-start-variable-row"
                      >
                        <n-input
                          v-model:value="variable.key"
                          size="small"
                          placeholder="变量 Key"
                          @update:value="syncWorkflowStartVariables"
                        />
                        <n-input
                          v-model:value="variable.label"
                          size="small"
                          placeholder="变量名称"
                          @update:value="syncWorkflowStartVariables"
                        />
                        <n-select
                          v-model:value="variable.type"
                          :options="variableTypeOptions"
                          size="small"
                          :consistent-menu-width="false"
                          @update:value="syncWorkflowStartVariables"
                        />
                        <n-switch
                          v-model:value="variable.required"
                          size="small"
                          @update:value="syncWorkflowStartVariables"
                        />
                        <n-input
                          v-model:value="variable.description"
                          size="small"
                          class="workflow-start-variable-row__description"
                          placeholder="说明"
                          @update:value="syncWorkflowStartVariables"
                        />
                        <n-button size="tiny" text type="error" @click="removeWorkflowStartVariable(index)">删除</n-button>
                      </div>
                    </div>
                    <div v-else class="workflow-start-variables__empty">暂无入口变量，点击“添加变量”开始定义。</div>
                  </section>
                </template>
                <template v-else-if="selectedWorkflowNode.type === 'llm'">
                  <n-form-item :label="isPlatformCapabilityRoute ? '模型路由 Key' : '模型配置'">
                    <n-input
                      v-if="isPlatformCapabilityRoute"
                      v-model:value="selectedWorkflowNode.data.model"
                      placeholder="例如：default-chat"
                    />
                    <n-select
                      v-else
                      v-model:value="selectedWorkflowNode.data.model"
                      :options="modelConfigOptions"
                      :loading="modelConfigLoading"
                      filterable
                      placeholder="选择模型或路由配置"
                    />
                  </n-form-item>
                  <n-form-item label="系统提示词">
                    <div class="workflow-prompt-asset-control">
                      <n-radio-group
                        v-if="canUsePromptAsset"
                        :value="workflowNodePromptSource(selectedWorkflowNode)"
                        size="small"
                        @update:value="(value) => updateWorkflowNodePromptSource(selectedWorkflowNode, value)"
                      >
                        <n-radio-button value="inline">手写</n-radio-button>
                        <n-radio-button value="asset">引用提示词库</n-radio-button>
                      </n-radio-group>
                      <template v-if="canUsePromptAsset && workflowNodePromptSource(selectedWorkflowNode) === 'asset'">
                        <n-select
                          :value="workflowNodePromptAssetKey(selectedWorkflowNode)"
                          :options="publishedPromptOptions"
                          :loading="publishedPromptsLoading"
                          filterable
                          clearable
                          placeholder="选择已发布的提示词"
                          @update:value="(value) => updateWorkflowNodePromptAsset(selectedWorkflowNode, value)"
                        />
                        <div class="prompt-asset-preview workflow-system-prompt-preview">
                          <div>
                            <span>{{ workflowNodePublishedPrompt(selectedWorkflowNode)?.name || '未选择提示词' }}</span>
                            <n-tag v-if="workflowNodePublishedPrompt(selectedWorkflowNode)?.resolved_version" size="small" round>
                              {{ workflowNodePublishedPrompt(selectedWorkflowNode)?.resolved_version }}
                            </n-tag>
                          </div>
                          <pre>{{ workflowNodePublishedPrompt(selectedWorkflowNode)?.system_prompt || '选择后将使用提示词库当前已发布版本的系统提示词。' }}</pre>
                        </div>
                      </template>
                      <n-input
                        v-else
                        v-model:value="selectedWorkflowNode.data.system_prompt"
                        type="textarea"
                        :autosize="{ minRows: 4, maxRows: 8 }"
                      />
                    </div>
                  </n-form-item>
                  <n-form-item label="用户提示词模板">
                    <n-input
                      v-model:value="selectedWorkflowNode.data.user_prompt_template"
                      type="textarea"
                      placeholder="例如：请总结：{{content}}"
                      :autosize="{ minRows: 5, maxRows: 10 }"
                    />
                  </n-form-item>
                  <n-form-item label="输出变量">
                    <n-input v-model:value="selectedWorkflowNode.data.output_key" placeholder="例如：summary" />
                  </n-form-item>
                  <n-form-item label="输出格式">
                    <n-select v-model:value="selectedWorkflowNode.data.response_format_type" :options="workflowLlmOutputFormatOptions" />
                  </n-form-item>
                </template>
                <template v-else-if="selectedWorkflowNode.type === 'sql_query'">
                  <n-form-item label="SQL 语句">
                    <CodePreview
                      v-model:value="selectedWorkflowNode.data.sql"
                      class="workflow-sql-editor"
                      language="sql"
                      :min-height="240"
                      :max-height="420"
                      :read-only="false"
                    />
                  </n-form-item>
                  <n-form-item label="参数 JSON">
                    <n-input
                      v-model:value="selectedWorkflowNode.data.params_text"
                      type="textarea"
                      placeholder='例如：["{{status}}"]'
                      :autosize="{ minRows: 2, maxRows: 6 }"
                    />
                  </n-form-item>
                  <n-form-item label="输出变量名">
                    <n-input v-model:value="selectedWorkflowNode.data.output_key" placeholder="例如：records" />
                    <template #feedback>{{ sqlOutputVariableHint(selectedWorkflowNode.data.output_key) }}</template>
                  </n-form-item>
                  <n-form-item label="结果形态">
                    <n-select v-model:value="selectedWorkflowNode.data.result_shape" :options="sqlResultShapeOptions" />
                  </n-form-item>
                  <n-form-item label="最大行数">
                    <n-input-number v-model:value="selectedWorkflowNode.data.max_rows" :min="1" :max="1000" />
                  </n-form-item>
                  <n-form-item label="数据权限资源 Key">
                    <n-input v-model:value="selectedWorkflowNode.data.data_access.resource_key" placeholder="例如：workflow.orders" />
                    <template #feedback>
                      SQL 执行时会默认注入当前用户的数据权限过滤，查询结果需包含 tenant_id 和数据权限字段。
                    </template>
                  </n-form-item>
                  <n-form-item label="租户过滤列（可留空）">
                    <n-input v-model:value="selectedWorkflowNode.data.data_access.tenant_column" placeholder="默认 tenant_id；不需要租户过滤可留空" />
                  </n-form-item>
                </template>
                <template v-else-if="selectedWorkflowNode.type === 'condition'">
                  <n-form-item label="左值">
                    <n-input v-model:value="selectedWorkflowNode.data.left" placeholder="例如：{{score}}" />
                  </n-form-item>
                  <n-form-item label="判断方式">
                    <n-select v-model:value="selectedWorkflowNode.data.operator" :options="conditionOperatorOptions" />
                  </n-form-item>
                  <n-form-item label="右值">
                    <n-input v-model:value="selectedWorkflowNode.data.right" placeholder="例如：90" />
                  </n-form-item>
                </template>
                <template v-else-if="selectedWorkflowNode.type === 'end'">
                  <n-form-item label="输出">
                    <n-input v-model:value="selectedWorkflowNode.data.output" placeholder="例如：{{summary}}" />
                  </n-form-item>
                </template>
              </n-form>
            </template>
          </section>
        </main>

      </div>

      <div
        v-else-if="activeWorkspace === 'orchestration'"
        ref="workbenchRef"
        class="studio-workbench"
        :class="{ 'is-preview-focus': previewFocusMode }"
        :style="workbenchStyle"
      >
        <section class="studio-builder">
          <div class="studio-section studio-section--prompt">
            <header class="studio-section__head">
              <div>
                <h3>提示词</h3>
                <span>{{ '\u5b9a\u4e49\u5355\u8f6e\u5bf9\u8bdd\u5e94\u7528\u7684\u7cfb\u7edf\u89d2\u8272\u548c\u7528\u6237\u8f93\u5165\u6a21\u677f\u3002' }}</span>
              </div>
              <n-button size="small" tertiary type="primary" @click="generatePromptHint">生成</n-button>
            </header>
            <n-form label-placement="top" class="studio-form">
              <n-form-item :label="isPlatformCapabilityRoute ? '模型路由 Key' : '模型配置'">
                <n-input
                  v-if="isPlatformCapabilityRoute"
                  v-model:value="selectedModelKey"
                  placeholder="例如：default-chat"
                />
                <n-select
                  v-else
                  v-model:value="selectedModelKey"
                  :options="modelConfigOptions"
                  :loading="modelConfigLoading"
                  filterable
                  placeholder="选择模型或路由配置"
                />
              </n-form-item>
              <n-form-item label="系统提示词">
                <div class="system-prompt-source">
                  <n-radio-group v-if="canUsePromptAsset" v-model:value="systemPromptSource" size="small">
                    <n-radio-button value="inline">手动编写</n-radio-button>
                    <n-radio-button value="asset">引用提示词库</n-radio-button>
                  </n-radio-group>
                  <n-input
                    v-if="systemPromptSource === 'inline'"
                    v-model:value="form.system_prompt"
                    type="textarea"
                    :autosize="{ minRows: 5, maxRows: 9 }"
                  />
                  <template v-else>
                    <n-select
                      v-model:value="selectedSystemPromptAssetKey"
                      :options="publishedPromptOptions"
                      :loading="publishedPromptsLoading"
                      filterable
                      clearable
                      placeholder="选择已发布的提示词"
                    />
                    <div class="prompt-asset-preview">
                      <div class="prompt-asset-preview__meta">
                        <span>{{ selectedPublishedPrompt?.name || '未选择提示词' }}</span>
                        <n-tag v-if="selectedPublishedPrompt?.resolved_version" size="small" round>
                          {{ selectedPublishedPrompt.resolved_version }}
                        </n-tag>
                      </div>
                      <pre>{{ selectedPublishedPrompt?.system_prompt || '选择后将使用提示词库当前已发布版本作为系统提示词。' }}</pre>
                    </div>
                  </template>
                </div>
              </n-form-item>
              <n-form-item label="用户提示词模板">
                <n-input
                  v-model:value="form.user_prompt_template"
                  type="textarea"
                  placeholder="例如：请总结：{{question}}"
                  :autosize="{ minRows: 8, maxRows: 16 }"
                />
              </n-form-item>
            </n-form>

            <section v-if="runtimeVariableFields.length" class="variable-schema">
              <div class="variable-schema__header">
                <div>
                  <h4>变量</h4>
                  <span>定义模板中需要注入的变量 Schema。</span>
                </div>
                <n-button size="tiny" text @click="syncRuntimeVariableValues">同步 Schema</n-button>
              </div>
              <div class="variable-schema__table">
                <div class="variable-schema__row variable-schema__row--head">
                  <span>变量 KEY</span>
                  <span>变量名</span>
                  <span>类型</span>
                  <span>可选</span>
                </div>
                <div v-for="field in runtimeVariableFields" :key="field.key" class="variable-schema__row">
                  <div class="variable-schema__key">
                    <span>{{ field.key }}</span>
                  </div>
                  <n-input
                    v-model:value="variableLabelOverrides[field.key]"
                    size="small"
                    clearable
                    placeholder="用于调试表单展示"
                    @update:value="(value) => updateVariableLabel(field.key, value)"
                  />
                  <n-select
                    v-model:value="variableTypeOverrides[field.key]"
                    :options="variableTypeOptions"
                    size="small"
                    :consistent-menu-width="false"
                    class="variable-schema__type"
                    @update:value="(value) => updateVariableType(field.key, value as RuntimeVariableType)"
                  />
                  <n-switch
                    v-model:value="variableOptionalOverrides[field.key]"
                    size="small"
                    @update:value="(value) => updateVariableOptional(field.key, value)"
                  />
                </div>
              </div>
            </section>
          </div>
        </section>

        <button
          class="studio-resizer"
          type="button"
          :aria-label="previewWidthPercent > 52 ? '收起预览面板' : '拉宽预览面板'"
          :title="previewWidthPercent > 52 ? '收起预览面板' : '拉宽预览面板'"
          @click="togglePreviewWidth"
          @pointerdown="startPreviewResize"
        >
          <span></span>
        </button>

        <aside class="studio-preview">
          <div class="preview-panel">
            <header class="preview-panel__head">
              <div>
                <h3>调试与预览</h3>
                <span>{{ form.status === 'published' ? '已发布' : '草稿' }}</span>
              </div>
              <div class="preview-panel__actions">
                <n-button size="small" tertiary @click="togglePreviewFocusMode">
                  {{ previewFocusMode ? '显示提示词' : '隐藏提示词' }}
                </n-button>
                <div v-if="runStatusText" class="preview-run-status" :class="{ 'is-running': running }">
                  <span class="preview-run-status__dot"></span>
                  <span>{{ runStatusText }}</span>
                </div>
                <n-select
                  v-model:value="selectedOutputFormat"
                  size="small"
                  :options="outputFormatOptions"
                  :consistent-menu-width="false"
                  class="preview-output-format"
                />
                <n-button :type="running ? 'warning' : 'primary'" @click="running ? cancelRunDraft() : runDraft()">
                  {{ running ? '取消' : '运行' }}
                </n-button>
              </div>
            </header>

            <section v-if="runtimeVariableFields.length" class="runtime-variables" :class="{ 'is-collapsed': runtimeVariablesCollapsed }">
              <button
                class="runtime-variables__header"
                type="button"
                :aria-expanded="!runtimeVariablesCollapsed"
                @click="toggleRuntimeVariablesCollapsed"
              >
                <span>运行变量</span>
                <span class="runtime-variables__meta">{{ runtimeVariableFields.length }} 个变量</span>
                <span class="runtime-variables__chevron" aria-hidden="true">›</span>
              </button>
              <div v-if="!runtimeVariablesCollapsed" class="runtime-variable-list">
                <div v-for="field in runtimeVariableFields" :key="field.key" class="runtime-variable-item">
                  <div class="runtime-variable-label-row">
                    <span
                      class="runtime-variable-label"
                      :title="field.label !== field.key ? `${field.label} (${field.key})` : field.key"
                    >
                      <span class="runtime-variable-name">{{ field.label }}</span>
                      <span v-if="!field.required" class="runtime-variable-optional">选填</span>
                    </span>
                    <span v-if="field.required" class="runtime-variable-required">*</span>
                  </div>
                  <n-select
                    v-if="field.options?.length"
                    v-model:value="runtimeVariableValues[field.key]"
                    clearable
                    :options="field.options"
                    :placeholder="field.placeholder"
                  />
                  <n-switch v-else-if="field.type === 'boolean'" v-model:value="runtimeVariableValues[field.key]" />
                  <n-input-number
                    v-else-if="field.type === 'number'"
                    v-model:value="runtimeVariableValues[field.key]"
                    clearable
                    :placeholder="field.placeholder"
                    class="runtime-variable-number"
                  />
                  <n-upload
                    v-else-if="isMediaVariableField(field)"
                    :accept="mediaVariableAccept(field)"
                    :default-upload="false"
                    :max="1"
                    @change="(options) => handleMediaVariableChange(field, options)"
                  >
                    <n-upload-dragger>
                      <div class="runtime-media-upload__title">{{ mediaVariableUploadTitle(field) }}</div>
                      <div class="runtime-media-upload__hint">{{ mediaVariableUploadHint(field) }}</div>
                    </n-upload-dragger>
                  </n-upload>
                  <n-input v-else v-model:value="runtimeVariableValues[field.key]" clearable :placeholder="field.placeholder" />
                  <div v-if="isMediaVariableField(field) && mediaVariableValue(field.key)" class="runtime-media-file">
                    <span>{{ mediaVariableValue(field.key)?.name }}</span>
                    <span>{{ formatBytes(mediaVariableValue(field.key)?.size || 0) }}</span>
                  </div>
                  <div v-if="field.description" class="runtime-variable-description">{{ field.description }}</div>
                </div>
              </div>
            </section>

            <div class="chat-preview">
              <div class="chat-preview__bubble">
                <n-collapse v-if="previewThinkText" class="think-collapse" arrow-placement="right">
                  <n-collapse-item name="think">
                    <template #header>
                      <span class="think-collapse__title">已生成思考过程</span>
                    </template>
                    <pre class="think-box">{{ previewThinkText }}</pre>
                  </n-collapse-item>
                </n-collapse>
                <div v-if="previewAnswerText" class="answer-renderer">
                  <template v-if="previewRenderedOutput.kind === 'html'">
                    <div class="html-preview-toolbar">
                      <span>静态预览已移除脚本，避免调试页执行模型生成代码。</span>
                      <div class="html-preview-toolbar__actions">
                        <n-button size="tiny" secondary @click="openCurrentHtmlPreviewInNewTab">新标签预览</n-button>
                        <n-switch v-model:value="allowHtmlScripts" size="small">
                          <template #checked>执行脚本</template>
                          <template #unchecked>静态</template>
                        </n-switch>
                      </div>
                    </div>
                    <iframe
                      class="html-answer-frame"
                      title="HTML 输出预览"
                      :sandbox="htmlPreviewSandbox"
                      :srcdoc="htmlPreviewSrcdoc"
                    ></iframe>
                    <details class="html-source-fallback">
                      <summary>预览为空时查看原始 HTML 源码</summary>
                      <pre>{{ previewRenderedOutput.rawContent || previewRenderedOutput.content }}</pre>
                    </details>
                  </template>
                  <div v-else-if="previewRenderedOutput.kind === 'json'" class="json-answer">
                    <CodePreview :value="previewRenderedOutput.content" language="json" :min-height="140" :max-height="520" />
                  </div>
                  <div v-else class="markdown-answer" v-html="previewRenderedOutput.content"></div>
                </div>
                <div v-else-if="running && selectedOutputFormat === 'html'" class="rendering-state">
                  <span class="rendering-spinner"></span>
                  <div>
                    <strong>{{ outputRenderingTitle }}</strong>
                    <span>{{ outputRenderingHint }}</span>
                  </div>
                </div>
                <div v-else-if="!running" class="chat-preview__empty">运行后将在这里预览模型输出。</div>
              </div>
            </div>

            <n-collapse class="preview-collapse" arrow-placement="right">
              <n-collapse-item title="Trace" name="trace">
                <dl v-if="runResult?.trace" class="trace-list">
                  <dt>Trace ID</dt>
                  <dd>{{ runResult.trace.trace_id }}</dd>
                  <dt>Model</dt>
                  <dd>{{ runResult.trace.model_key || runResult.trace.route_key }}</dd>
                  <dt>Latency</dt>
                  <dd>{{ formatElapsedSeconds(runResult.trace.elapsed_ms) }} 秒</dd>
                  <template v-if="tracePromptAsset">
                    <dt>Prompt Source</dt>
                    <dd>{{ tracePromptAsset.prompt_asset_name }} / {{ tracePromptAsset.prompt_version }}</dd>
                  </template>
                  <dt>Prompt</dt>
                  <dd><pre>{{ runResult.trace.rendered_prompt }}</pre></dd>
                </dl>
                <n-empty v-else description="运行后显示 Trace" />
              </n-collapse-item>
              <n-collapse-item title="发布 API" name="api">
                <code>POST /runtime/apps/{{ form.app_key }}/run</code>
              </n-collapse-item>
            </n-collapse>
          </div>
        </aside>
      </div>
      <section v-else-if="activeWorkspace === 'api'" class="studio-workspace-panel">
        <header class="workspace-panel__head">
          <div>
            <h3>访问 API</h3>
            <span>外部系统可通过租户 API Key 调用已发布的 AI 应用能力。</span>
          </div>
        </header>
        <div class="api-doc-layout">
          <main class="api-doc-main">
            <section class="api-doc-hero">
              <div class="api-endpoint-line">
                <span class="api-method">POST</span>
                <code>{{ apiEndpoint }}</code>
                <n-button size="tiny" quaternary @click="copyText(apiEndpoint, '调用地址')">复制</n-button>
              </div>
              <p>同步执行当前应用，返回模型输出、Trace ID 和用量信息。应用必须处于已发布状态。</p>
            </section>

            <section class="api-doc-section">
              <h4>请求体</h4>
              <div class="api-field-table">
                <div class="api-field-row api-field-row--head">
                  <span>字段</span>
                  <span>类型</span>
                  <span>必填</span>
                  <span>说明</span>
                </div>
                <div class="api-field-row">
                  <code>variables</code>
                  <span>object</span>
                  <span>是</span>
                  <span>应用运行变量，字段由下方变量表定义。</span>
                </div>
                <div class="api-field-row">
                  <code>temperature</code>
                  <span>number</span>
                  <span>否</span>
                  <span>本次调用覆盖温度参数，不传则使用应用配置。</span>
                </div>
                <div class="api-field-row">
                  <code>enable_think_output</code>
                  <span>boolean</span>
                  <span>否</span>
                  <span>是否返回模型思考过程，取决于模型能力。</span>
                </div>
              </div>
            </section>

            <section class="api-doc-section">
              <h4>运行变量</h4>
              <div v-if="apiVariableRows.length" class="api-field-table">
                <div class="api-field-row api-field-row--head">
                  <span>变量</span>
                  <span>类型</span>
                  <span>状态</span>
                  <span>说明</span>
                </div>
                <div v-for="field in apiVariableRows" :key="field.key" class="api-field-row">
                  <code>{{ field.key }}</code>
                  <span>{{ field.typeLabel }}</span>
                  <span>{{ field.required ? '必填' : '可选' }}</span>
                  <span>{{ field.description || field.label || '-' }}</span>
                </div>
              </div>
              <n-empty v-else description="当前应用未定义运行变量" />
            </section>

            <section class="api-doc-section">
              <div class="api-doc-section__head">
                <h4>请求示例</h4>
                <n-button size="tiny" quaternary @click="copyText(apiRequestExample, '请求示例')">复制</n-button>
              </div>
              <pre class="api-code-block">{{ apiRequestExample }}</pre>
            </section>

            <section class="api-doc-section">
              <div class="api-doc-section__head">
                <h4>响应示例</h4>
                <n-button size="tiny" quaternary @click="copyText(apiResponseExample, '响应示例')">复制</n-button>
              </div>
              <pre class="api-code-block">{{ apiResponseExample }}</pre>
            </section>

            <section class="api-doc-section">
              <h4>错误说明</h4>
              <div class="api-field-table api-field-table--compact">
                <div class="api-field-row api-field-row--head">
                  <span>HTTP</span>
                  <span>场景</span>
                  <span>处理建议</span>
                </div>
                <div class="api-field-row">
                  <code>401</code>
                  <span>API Key 无效或缺失</span>
                  <span>检查租户 API Key 是否正确、是否已撤销。</span>
                </div>
                <div class="api-field-row">
                  <code>409</code>
                  <span>应用未发布</span>
                  <span>先在 AI Studio 发布应用后再调用。</span>
                </div>
                <div class="api-field-row">
                  <code>422</code>
                  <span>变量或模型配置不合法</span>
                  <span>检查请求体变量、模型路由和运行配置。</span>
                </div>
                <div class="api-field-row">
                  <code>502</code>
                  <span>模型执行失败</span>
                  <span>根据返回的 Trace ID 在运行日志中排查。</span>
                </div>
              </div>
            </section>
          </main>

          <aside class="api-doc-aside">
            <section class="api-info-panel">
              <h4>接口信息</h4>
              <dl>
                <dt>状态</dt>
                <dd>{{ form.status === 'published' ? '已发布' : '未发布' }}</dd>
                <dt>认证方式</dt>
                <dd><code>X-API-Key</code></dd>
                <dt>Content-Type</dt>
                <dd><code>application/json</code></dd>
                <dt>调用模式</dt>
                <dd>同步执行</dd>
              </dl>
            </section>

            <section class="api-info-panel">
              <div class="api-doc-section__head">
                <h4>cURL</h4>
                <n-button size="tiny" quaternary @click="copyText(apiCurlExample, 'cURL 示例')">复制</n-button>
              </div>
              <pre class="api-code-block api-code-block--curl">{{ apiCurlExample }}</pre>
            </section>

            <section class="api-info-panel">
              <h4>接入提示</h4>
              <ul class="api-note-list">
                <li>API Key 需在当前租户下创建，调用时会自动使用该租户的数据范围。</li>
                <li>每次调用都会生成 Trace，可在运行日志中查看输入、输出和耗时。</li>
                <li>生产环境建议在外部系统侧设置超时与重试策略。</li>
              </ul>
            </section>
          </aside>
        </div>
      </section>

      <section v-else-if="activeWorkspace === 'logs'" class="studio-workspace-panel">
        <header class="workspace-panel__head">
          <div>
            <h3>运行日志</h3>
            <span>查看当前 AI 应用的调试运行和 API 调用记录。</span>
          </div>
          <n-button size="small" :loading="runLogsLoading" @click="loadRunLogs">刷新</n-button>
        </header>
        <div class="run-log-layout">
          <div class="run-log-list">
            <button
              v-for="item in runLogs"
              :key="item.run_id"
              class="run-log-item"
              :class="{ 'is-active': selectedRunLog?.run_id === item.run_id }"
              type="button"
              @click="selectedRunLogId = item.run_id"
            >
              <span class="run-log-item__top">
                <n-tag size="small" :type="item.status === 'success' ? 'success' : 'error'">
                  {{ item.status === 'success' ? '成功' : '失败' }}
                </n-tag>
                <span>{{ formatDateTime(item.create_time) }}</span>
              </span>
              <strong>{{ runModeLabel(item.run_mode) }}</strong>
              <span class="run-log-item__meta">
                {{ item.model || '未记录模型' }} · {{ formatElapsedSeconds(item.elapsed_ms) }} 秒
              </span>
            </button>
            <n-empty v-if="!runLogsLoading && !runLogs.length" description="暂无运行日志" />
          </div>
          <div class="run-log-detail">
            <template v-if="selectedRunLog">
              <div class="run-log-detail__summary">
                <div>
                  <span>状态</span>
                  <strong>{{ selectedRunLog.status === 'success' ? '成功' : '失败' }}</strong>
                </div>
                <div>
                  <span>耗时</span>
                  <strong>{{ formatElapsedSeconds(selectedRunLog.elapsed_ms) }} 秒</strong>
                </div>
                <div>
                  <span>模型</span>
                  <strong>{{ selectedRunLog.model || '-' }}</strong>
                </div>
              </div>
              <div v-if="selectedRunLog.error_message" class="run-log-error">
                {{ selectedRunLog.error_message }}
              </div>
              <section>
                <h4>输入变量</h4>
                <pre class="run-log-json-viewer">{{ stringifyJson(selectedRunLog.input_variables) }}</pre>
              </section>
              <section>
                <h4>输出结果</h4>
                <div v-if="selectedRunLog.answer" class="run-log-answer">
                  <n-collapse v-if="selectedRunLogOutput.think" class="think-collapse" arrow-placement="right">
                    <n-collapse-item name="think">
                      <template #header>
                        <span class="think-collapse__title">已生成思考过程</span>
                      </template>
                      <pre class="think-box">{{ selectedRunLogOutput.think }}</pre>
                    </n-collapse-item>
                  </n-collapse>
                  <div v-if="selectedRunLogOutput.answer" class="answer-renderer">
                    <template v-if="selectedRunLogRenderedOutput.kind === 'html'">
                      <iframe
                        class="html-answer-frame"
                        title="HTML 输出预览"
                        sandbox="allow-popups allow-popups-to-escape-sandbox"
                        :srcdoc="selectedRunLogRenderedOutput.content"
                      ></iframe>
                      <details class="html-source-fallback">
                        <summary>预览为空时查看 HTML 源码</summary>
                        <pre>{{ selectedRunLogRenderedOutput.content }}</pre>
                      </details>
                    </template>
                    <div v-else-if="selectedRunLogRenderedOutput.kind === 'json'" class="json-answer">
                      <CodePreview :value="selectedRunLogRenderedOutput.content" language="json" :min-height="140" :max-height="420" />
                    </div>
                    <div v-else class="markdown-answer" v-html="selectedRunLogRenderedOutput.content"></div>
                  </div>
                </div>
                <n-empty v-else description="本次运行没有输出内容" />
              </section>
              <section>
                <h4>运行信息</h4>
                <dl class="trace-list">
                  <dt>Run ID</dt>
                  <dd>{{ selectedRunLog.run_id }}</dd>
                  <dt>Trace ID</dt>
                  <dd>{{ selectedRunLog.trace_id }}</dd>
                  <dt>Request ID</dt>
                  <dd>{{ selectedRunLog.request_id || '-' }}</dd>
                  <dt>Token</dt>
                  <dd>{{ tokenUsageText(selectedRunLog.usage) }}</dd>
                </dl>
              </section>
            </template>
            <n-empty v-else description="选择一条运行日志查看详情" />
          </div>
        </div>
      </section>

      <section v-else-if="activeWorkspace === 'monitoring'" class="studio-workspace-panel">
        <header class="workspace-panel__head">
          <div>
            <h3>监测</h3>
            <span>后续这里展示调用量、成功率、耗时和 Token 用量趋势。</span>
          </div>
        </header>
        <n-empty description="监测能力将在运行日志稳定后接入" />
      </section>

      <section v-else-if="activeWorkspace === 'settings'" class="studio-workspace-panel">
        <header class="workspace-panel__head">
          <div>
            <h3>设置</h3>
            <span>维护应用基础信息，保存后会同步到 AI Studio 应用列表。</span>
          </div>
        </header>
        <div class="app-settings-layout">
          <section class="app-settings-card">
            <div class="app-settings-card__head">
              <div>
                <h4>{{ settingsTitle }}</h4>
                <span>{{ settingsHint }}</span>
              </div>
            </div>
            <n-form label-placement="top" class="app-settings-form">
              <n-form-item label="应用名称" required>
                <n-input v-model:value="form.name" maxlength="80" show-count placeholder="请输入应用名称" />
              </n-form-item>
              <n-form-item label="图标">
                <n-select v-model:value="form.icon" :options="iconOptions" />
              </n-form-item>
              <n-form-item label="描述">
                <n-input
                  v-model:value="form.description"
                  type="textarea"
                  maxlength="500"
                  show-count
                  placeholder="简要说明这个应用服务什么场景"
                  :autosize="{ minRows: 4, maxRows: 7 }"
                />
              </n-form-item>
            </n-form>
          </section>

          <aside class="app-settings-preview">
            <span class="app-settings-preview__icon">{{ selectedIconLabel.slice(0, 1) }}</span>
            <div>
              <h4>{{ form.name || '未命名应用' }}</h4>
              <p>{{ form.description || '暂无描述' }}</p>
              <small>{{ form.app_key }} · {{ form.status === 'published' ? '已发布' : '草稿' }}</small>
            </div>
          </aside>
        </div>
      </section>

      <n-modal
        v-model:show="platformPreviewModalVisible"
        preset="card"
        title="选择租户上下文试运行"
        class="platform-preview-modal"
        :style="{ width: '520px' }"
        :bordered="false"
      >
        <n-form label-placement="top">
          <n-form-item label="租户">
            <n-select
              v-model:value="platformPreviewForm.tenant_id"
              :options="platformTenantOptions"
              :loading="platformTenantsLoading"
              filterable
              clearable
              placeholder="请选择租户"
              @update:value="handlePlatformPreviewTenantChange"
            />
          </n-form-item>
          <n-form-item label="模型或路由">
            <n-select
              v-model:value="platformPreviewForm.model"
              :options="platformPreviewModelOptions"
              :loading="platformPreviewModelsLoading"
              filterable
              clearable
              placeholder="请选择该租户的模型或路由"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="platform-preview-modal__footer">
            <n-button @click="platformPreviewModalVisible = false">取消</n-button>
            <n-button type="primary" :loading="running" @click="confirmPlatformPreviewRun">运行</n-button>
          </div>
        </template>
      </n-modal>

    </n-spin>
  </DetailPageRuntime>
</template>

<script lang="ts" setup>
  import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
  import { Background } from '@vue-flow/background';
  import { Controls } from '@vue-flow/controls';
  import { Handle, Position, VueFlow, useVueFlow, type Connection, type Edge, type Node, type XYPosition } from '@vue-flow/core';
  import '@vue-flow/core/dist/style.css';
  import '@vue-flow/core/dist/theme-default.css';
  import { useRoute, useRouter } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import type { SelectOption, UploadFileInfo } from 'naive-ui';
  import MarkdownIt from 'markdown-it';
  import { getLlmModels, getLlmRoutingPolicies, getTenants } from '@/api/business';
  import { getPublishedPromptAsset, getPublishedPromptAssets, type PublishedPromptAsset, type PromptAsset } from '@/api/aiAssets';
  import { AgentChatRuntime } from '@/components/AgentChatRuntime';
  import CodePreview from '@/components/CodePreview/index.vue';
  import { defineDetailPage, DetailPageRuntime } from '@/page-runtime';
  import {
    fetchAiCapabilityStream,
    fetchAiApplicationDraftStream,
    getAiCapability,
    getAiCapabilityRunLogs,
    getPlatformAiCapability,
    getPlatformAiCapabilityRunLogs,
    getTenantAiCapabilityModelOptions,
    getAiApplication,
    getAiApplicationRunLogs,
    previewPlatformAiCapability,
    publishAiApplication,
    updateAiCapability,
    updateAiApplication,
    updatePlatformAiCapability,
    type AiCapability,
    type AiApplication,
    type AiApplicationRunLog,
    type AiRunResult,
  } from '@/api/aiStudio';
  import { uploadManagedFile } from '@/api/fileManagement';
  import { useUser } from '@/store/modules/user';

  interface RuntimeVariableField {
    key: string;
    label: string;
    placeholder: string;
    description: string;
    type: RuntimeVariableType;
    required: boolean;
    options?: SelectOption[];
  }

  interface WorkflowStartVariable {
    id: string;
    key: string;
    label: string;
    type: RuntimeVariableType;
    required: boolean;
    description: string;
  }

  interface WorkflowTraceNode {
    node_id: string;
    node_type: string;
    status?: string;
    branch?: string;
    output?: Record<string, unknown>;
    error?: string;
    elapsed_ms?: number;
    title?: string;
  }

  type SchemaRecord = Record<string, unknown>;
  type RuntimeVariableType = 'text' | 'number' | 'boolean' | 'image' | 'file' | 'audio' | 'video';
  type RuntimeVariableValue = string | number | boolean | RuntimeMediaVariableValue | null;
  type PromptSource = 'inline' | 'asset';
  type WorkspaceKey = 'orchestration' | 'agent' | 'api' | 'logs' | 'monitoring' | 'settings';
  type StudioResourceType = 'application' | 'capability';
  type WorkflowNodeType = 'start' | 'llm' | 'sql_query' | 'condition' | 'end';
  type WorkflowNode = Node<Record<string, any>, WorkflowNodeType>;
  type WorkflowEdge = Edge<Record<string, any>>;
  type OutputFormat = 'markdown' | 'html' | 'json';
  type RenderedOutput = { kind: OutputFormat; content: string; rawContent?: string };

  interface RuntimeMediaVariableValue {
    type: 'image' | 'file' | 'audio' | 'video';
    name: string;
    mime_type: string;
    size: number;
    file_ref?: string | null;
    file_id?: number | null;
    sha256?: string;
    preview_url?: string;
    storage_status?: 'stored' | 'unavailable';
    redacted?: boolean;
    reason?: string;
    text?: string;
  }

  const TEMPLATE_VARIABLE_PATTERN = /\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g;
  const RESERVED_SCHEMA_KEYS = new Set(['type', 'title', 'label', 'description', 'properties', 'required', 'default', 'example']);
  const markdownRenderer = new MarkdownIt({
    html: false,
    linkify: true,
    breaks: true,
  });
  const route = useRoute();
  const router = useRouter();
  const message = useMessage();
  const userStore = useUser();
  const loading = ref(false);
  const saving = ref(false);
  const publishing = ref(false);
  const running = ref(false);
  const activeWorkspace = ref<WorkspaceKey>('orchestration');
  const workbenchRef = ref<HTMLElement | null>(null);
  const workflowCanvasPanelRef = ref<HTMLElement | null>(null);
  const { project } = useVueFlow('workflow-editor');
  const previewWidthPercent = ref(42);
  const previewFocusMode = ref(false);
  const previewResizeDragged = ref(false);
  const runtimeVariablesCollapsed = ref(false);
  const modelConfigLoading = ref(false);
  const publishedPromptsLoading = ref(false);
  const platformPreviewModalVisible = ref(false);
  const workflowRunPanelVisible = ref(false);
  const workflowRunErrorText = ref('');
  const workflowRunStatusText = ref('等待运行');
  const platformTenantsLoading = ref(false);
  const platformPreviewModelsLoading = ref(false);
  const activeApp = ref<AiApplication | null>(null);
  const activeCapability = ref<AiCapability | null>(null);
  const models = ref<Recordable[]>([]);
  const policies = ref<Recordable[]>([]);
  const publishedPrompts = ref<PromptAsset[]>([]);
  const publishedPromptDetails = reactive<Record<string, PublishedPromptAsset>>({});
  const platformTenants = ref<Recordable[]>([]);
  const platformPreviewModels = ref<Recordable[]>([]);
  const platformPreviewPolicies = ref<Recordable[]>([]);
  const selectedModelKey = ref('');
  const systemPromptSource = ref<'inline' | 'asset'>('inline');
  const selectedSystemPromptAssetKey = ref('');
  const selectedOutputFormat = ref<OutputFormat>('markdown');
  const variablesSchemaText = ref('{\n  "type": "object",\n  "required": ["question"]\n}');
  const outputSchemaText = ref('{}');
  const runtimeVariableValues = reactive<Record<string, RuntimeVariableValue>>({});
  const variableTypeOverrides = reactive<Record<string, RuntimeVariableType>>({});
  const variableLabelOverrides = reactive<Record<string, string>>({});
  const variableOptionalOverrides = reactive<Record<string, boolean>>({});
  const workflowNodes = ref<WorkflowNode[]>([]);
  const workflowEdges = ref<WorkflowEdge[]>([]);
  const selectedWorkflowNodeId = ref('');
  const selectedWorkflowEdgeId = ref('');
  const openWorkflowNodeMenuId = ref('');
  const workflowCanvasMenu = reactive({
    visible: false,
    x: 0,
    y: 0,
    position: { x: 0, y: 0 } as XYPosition,
  });
  const runResult = ref<AiRunResult | null>(null);
  const runLogs = ref<AiApplicationRunLog[]>([]);
  const runLogsLoading = ref(false);
  const selectedRunLogId = ref('');
  const streamThinkText = ref('');
  const allowHtmlScripts = ref(false);
  const runningElapsedMs = ref(0);
  const lastRunElapsedMs = ref(0);
  let runStopwatchTimer: number | null = null;
  let htmlPreviewObjectUrl = '';
  let runAbortController: AbortController | null = null;
  const form = reactive({
    app_key: '',
    name: '',
    icon: 'robot',
    description: '',
    app_type: 'single_turn_generation',
    status: 'draft',
    endpoint_slug: '',
    system_prompt: '',
    developer_prompt: '',
    user_prompt_template: '',
  });

  const modelConfigOptions = computed<SelectOption[]>(() => {
    const options: SelectOption[] = [];
    const seen = new Set<string>();
    const push = (value: string, label: string) => {
      if (!value || seen.has(value)) return;
      seen.add(value);
      options.push({ value, label });
    };
    policies.value
      .filter((item) => item.enabled !== false)
      .forEach((item) => {
        const routeKey = String(item.route_key || '').trim();
        push(routeKey, `路由：${item.display_name || routeKey} (${routeKey})`);
      });
    models.value
      .filter((item) => item.enabled !== false)
      .forEach((item) => {
        const modelKey = String(item.model_key || '').trim();
        push(modelKey, `模型：${item.display_name || item.model_name || modelKey} (${modelKey})`);
      });
    return options;
  });
  const platformTenantOptions = computed<SelectOption[]>(() =>
    platformTenants.value.map((item) => ({
      label: `${item.name || item.tenant_key || item.key} (${item.tenant_key || item.key || item.id})`,
      value: Number(item.id),
    }))
  );
  const platformPreviewModelOptions = computed<SelectOption[]>(() =>
    buildModelConfigOptions(platformPreviewModels.value, platformPreviewPolicies.value)
  );
  const variableTypeOptions: SelectOption[] = [
    { label: '文本', value: 'text' },
    { label: '数字', value: 'number' },
    { label: '开关', value: 'boolean' },
    { label: '图片', value: 'image' },
    { label: '音频', value: 'audio' },
    { label: '视频', value: 'video' },
    { label: '文件', value: 'file' },
  ];
  const iconOptions: SelectOption[] = [
    { label: '助手', value: 'robot' },
    { label: '对话', value: 'chat' },
    { label: '流程', value: 'workflow' },
    { label: '实验', value: 'experiment' },
    { label: '接口', value: 'api' },
  ];
  const outputFormatOptions: SelectOption[] = [
    { label: 'Markdown', value: 'markdown' },
    { label: 'HTML', value: 'html' },
    { label: 'JSON', value: 'json' },
  ];
  const platformPreviewForm = reactive({
    tenant_id: null as number | null,
    model: '',
  });
  const baseWorkspaceTabs: Array<{ key: WorkspaceKey; label: string; description: string }> = [
    { key: 'orchestration', label: '\u5355\u8f6e\u5bf9\u8bdd', description: '\u5355\u6b21\u8fd0\u884c' },
    { key: 'api', label: '\u5f00\u653e API', description: '\u63a5\u5165\u65b9\u5f0f' },
    { key: 'logs', label: '\u8fd0\u884c\u65e5\u5fd7', description: '\u8c03\u7528\u8bb0\u5f55' },
    { key: 'monitoring', label: '\u76d1\u63a7', description: '\u8d28\u91cf\u4e0e\u8017\u7528' },
    { key: 'settings', label: '\u8bbe\u7f6e', description: '\u57fa\u7840\u914d\u7f6e' },
  ];
  const isWorkflowMode = computed(() => form.app_type === 'workflow');
  const isAgentMode = computed(() => form.app_type === 'agent');
  const workspaceTabs = computed(() => {
    if (isAgentMode.value && !isCapability.value) {
      return [
        { key: 'agent' as WorkspaceKey, label: 'Agent', description: '\u591a\u8f6e\u5bf9\u8bdd' },
        { key: 'settings' as WorkspaceKey, label: '\u8bbe\u7f6e', description: '\u57fa\u7840\u914d\u7f6e' },
        { key: 'logs' as WorkspaceKey, label: '\u8fd0\u884c\u65e5\u5fd7', description: '\u8c03\u7528\u8bb0\u5f55' },
        { key: 'monitoring' as WorkspaceKey, label: '\u76d1\u63a7', description: '\u8d28\u91cf\u4e0e\u8017\u7528' },
      ];
    }
    const tabs = baseWorkspaceTabs.filter((item) => !isCapability.value || item.key !== 'api');
    return isWorkflowMode.value
      ? tabs.map((item) => (item.key === 'orchestration' ? { ...item, label: 'Workflow', description: '\u6d41\u7a0b\u7f16\u6392' } : item))
      : tabs;
  });
  const selectedWorkflowNode = computed(() => workflowNodes.value.find((node) => node.id === selectedWorkflowNodeId.value) || null);

  const parsedVariablesSchema = computed(() => parseJsonObjectSilently(variablesSchemaText.value));
  const workflowStartNode = computed(() => workflowNodes.value.find((node) => node.type === 'start') || null);
  const workflowStartVariables = computed<WorkflowStartVariable[]>(() =>
    Array.isArray(workflowStartNode.value?.data?.variables) ? (workflowStartNode.value?.data?.variables as WorkflowStartVariable[]) : []
  );
  const workflowStartVariableMap = computed(
    () => new Map(validWorkflowStartVariables(workflowStartVariables.value).map((variable) => [normalizeWorkflowVariableKey(variable.key), variable]))
  );
  const workflowStartVariableKeys = computed(() =>
    validWorkflowStartVariables(workflowStartVariables.value).map((variable) => normalizeWorkflowVariableKey(variable.key))
  );
  const workflowTemplateVariableKeys = computed(() => {
    if (!isWorkflowMode.value) return [];
    return [
      ...new Set(
        workflowNodes.value.flatMap((node) =>
          [node.data?.system_prompt, node.data?.developer_prompt, node.data?.user_prompt_template, node.data?.left, node.data?.right, node.data?.output]
            .map((value) => String(value || ''))
            .flatMap(extractTemplateVariableKeys)
        )
      ),
    ];
  });
  const templateVariableKeys = computed(() =>
    isWorkflowMode.value
      ? [...new Set([...workflowStartVariableKeys.value, ...workflowTemplateVariableKeys.value])]
      : extractTemplateVariableKeys(form.user_prompt_template || '')
  );
  const runtimeVariableKeys = computed(() => (isWorkflowMode.value ? workflowStartVariableKeys.value : templateVariableKeys.value));
  const savedInputVariableKeys = computed(() => (isWorkflowMode.value ? workflowStartVariableKeys.value : templateVariableKeys.value));
  const runtimeVariableFields = computed<RuntimeVariableField[]>(() =>
    buildRuntimeVariableFields(parsedVariablesSchema.value, runtimeVariableKeys.value)
  );
  const workflowInputVariableFields = computed<RuntimeVariableField[]>(() =>
    isWorkflowMode.value ? buildRuntimeVariableFields(parsedVariablesSchema.value, workflowStartVariableKeys.value) : []
  );
  const publishedPromptOptions = computed<SelectOption[]>(() =>
    publishedPrompts.value.map((item) => ({
      label: `${item.name} (${item.prompt_key})`,
      value: item.prompt_key,
    }))
  );
  const selectedPublishedPrompt = computed(() => {
    const key = selectedSystemPromptAssetKey.value;
    return key ? publishedPromptDetails[key] : null;
  });
  const tracePromptAsset = computed(() => {
    const messages = runResult.value?.trace?.rendered_messages || [];
    const systemMessage = messages.find((item) => item.role === 'system' && item.prompt_source === 'prompt_asset');
    return systemMessage || null;
  });
  const workflowTracePayload = computed(() => {
    const trace = asSchemaRecord(runResult.value?.trace);
    const directWorkflow = asSchemaRecord(trace?.workflow);
    if (directWorkflow) return { workflow: directWorkflow };
    const messages = runResult.value?.trace?.rendered_messages || [];
    const workflowMessage = messages.find((item) => item.role === 'workflow_trace');
    const workflowContent = asSchemaRecord(workflowMessage?.content);
    if (workflowContent) return workflowContent;
    return asSchemaRecord((runResult.value as unknown as SchemaRecord | null)?.workflow_trace);
  });
  const workflowTraceNodes = computed<WorkflowTraceNode[]>(() => {
    const workflow = asSchemaRecord(workflowTracePayload.value?.workflow);
    const nodes = Array.isArray(workflow?.nodes) ? workflow.nodes : [];
    return nodes
      .map((item) => {
        const record = asSchemaRecord(item);
        if (!record) return null;
        const nodeId = String(record.node_id || '');
        if (!nodeId) return null;
        return {
          node_id: nodeId,
          node_type: String(record.node_type || ''),
          status: String(record.status || 'success'),
          branch: typeof record.branch === 'string' ? record.branch : undefined,
          output: asSchemaRecord(record.output) || {},
          error: typeof record.error === 'string' ? record.error : undefined,
          elapsed_ms: typeof record.elapsed_ms === 'number' ? record.elapsed_ms : Number(record.elapsed_ms || 0),
        };
      })
      .filter(Boolean) as WorkflowTraceNode[];
  });
  const workflowExecutedNodeIds = computed(() => new Set(workflowTraceNodes.value.map((node) => node.node_id)));
  const workflowFailedNodeIds = computed(
    () => new Set(workflowTraceNodes.value.filter((node) => node.status === 'failed').map((node) => node.node_id))
  );
  const workflowExecutedEdgeIds = computed(() => {
    const edgeIds = new Set<string>();
    workflowTraceNodes.value.slice(0, -1).forEach((node, index) => {
      const next = workflowTraceNodes.value[index + 1];
      const edge = workflowEdges.value.find((item) => {
        const branchMatches = node.branch ? String(item.sourceHandle || '') === node.branch : true;
        return item.source === node.node_id && item.target === next.node_id && branchMatches;
      });
      if (edge?.id) edgeIds.add(edge.id);
    });
    return edgeIds;
  });
  const parsedPreviewOutput = computed(() => splitThinkContent(runResult.value?.answer || ''));
  const previewThinkText = computed(() => streamThinkText.value || parsedPreviewOutput.value.think);
  const previewAnswerText = computed(() => parsedPreviewOutput.value.answer);
  const previewRenderedOutput = computed(() => renderAnswer(previewAnswerText.value, selectedOutputFormat.value));
  const htmlPreviewSrcdoc = computed(() =>
    allowHtmlScripts.value ? previewRenderedOutput.value.rawContent || previewRenderedOutput.value.content : previewRenderedOutput.value.content
  );
  const htmlPreviewSandbox = computed(() =>
    allowHtmlScripts.value
      ? 'allow-scripts allow-popups allow-popups-to-escape-sandbox'
      : 'allow-popups allow-popups-to-escape-sandbox'
  );
  const selectedRunLog = computed(() => runLogs.value.find((item) => item.run_id === selectedRunLogId.value) || runLogs.value[0] || null);
  const selectedRunLogOutput = computed(() => splitThinkContent(selectedRunLog.value?.answer || ''));
  const selectedRunLogRenderedOutput = computed(() => renderAnswer(selectedRunLogOutput.value.answer, selectedOutputFormat.value));
  const selectedIconLabel = computed(() => String(iconOptions.find((item) => item.value === form.icon)?.label || '助手'));
  const isPlatformCapabilityRoute = computed(() => route.name === 'ai-platform-capability-detail');
  const resourceType = computed<StudioResourceType>(() =>
    route.name === 'ai-studio-capability-detail' || isPlatformCapabilityRoute.value ? 'capability' : 'application'
  );
  const isCapability = computed(() => resourceType.value === 'capability');
  const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);
  const editingPlatformCapability = computed(() => isCapability.value && activeCapability.value?.scope === 'platform' && isPlatformAdmin.value);
  const canUsePromptAsset = computed(() => !isPlatformCapabilityRoute.value);
  const resourceLabel = computed(() => {
    if (isPlatformCapabilityRoute.value) return '平台AI能力';
    return isCapability.value ? 'AI 能力' : 'AI 应用';
  });
  const resourceFallbackDescription = computed(() => {
    if (isPlatformCapabilityRoute.value) return '维护平台内置 AI 能力，租户可直接启用或覆盖配置。';
    return `配置${resourceLabel.value}运行时并在 Playground 调试。`;
  });
  const settingsTitle = computed(() => (isCapability.value ? '能力信息' : '应用信息'));
  const settingsHint = computed(() =>
    isCapability.value
      ? '这些信息用于 AI Studio 能力列表和内部调用识别，不影响 Prompt Runtime 执行逻辑。'
      : '这些信息用于应用列表、导航和外部识别，不影响 Prompt Runtime 执行逻辑。'
  );
  const apiEndpoint = computed(() => `/runtime/apps/${form.app_key || '{app_key}'}/run`);
  const apiVariableRows = computed(() =>
    runtimeVariableFields.value.map((field) => ({
      ...field,
      typeLabel: variableTypeOptions.find((option) => option.value === field.type)?.label || field.type,
    }))
  );
  const apiRequestExample = computed(() => stringifyJson({ variables: sampleRuntimeVariables() }));
  const apiResponseExample = computed(() =>
    stringifyJson({
      answer: '模型输出内容',
      trace_id: 'trace_xxx',
      usage: {
        prompt_tokens: 128,
        completion_tokens: 256,
        total_tokens: 384,
      },
    })
  );
  const apiCurlExample = computed(
    () =>
      `curl -X POST "${apiEndpoint.value}" \\\n  -H "Content-Type: application/json" \\\n  -H "X-API-Key: $AI_STUDIO_API_KEY" \\\n  -d '${apiRequestExample.value.replace(/'/g, "'\\''")}'`
  );
  const runElapsedSeconds = computed(() => {
    const elapsedMs = Number(runResult.value?.trace?.elapsed_ms || 0);
    return elapsedMs > 0 ? formatElapsedSeconds(elapsedMs) : '';
  });
  const fallbackRunElapsedSeconds = computed(() =>
    !runElapsedSeconds.value && lastRunElapsedMs.value > 0 ? formatElapsedSeconds(lastRunElapsedMs.value) : ''
  );
  const runStatusText = computed(() => {
    if (running.value) {
      return `运行中 · ${formatStopwatchSeconds(runningElapsedMs.value)} 秒`;
    }
    const elapsedSeconds = runElapsedSeconds.value || fallbackRunElapsedSeconds.value;
    return elapsedSeconds ? `执行耗时 ${elapsedSeconds} 秒` : '';
  });
  const outputRenderingTitle = computed(() => '正在生成 HTML 输出');
  const outputRenderingHint = computed(() => '收到内容后会进入隔离预览并保留源码兜底。');
  const workbenchStyle = computed(() => ({
    '--studio-preview-width': `${previewWidthPercent.value}%`,
  }));
  const conditionOperatorOptions: SelectOption[] = [
    { label: '存在', value: 'exists' },
    { label: '为空', value: 'empty' },
    { label: '等于', value: 'equals' },
    { label: '不等于', value: 'not_equals' },
    { label: '包含', value: 'contains' },
    { label: '不包含', value: 'not_contains' },
    { label: '大于', value: 'gt' },
    { label: '大于等于', value: 'gte' },
    { label: '小于', value: 'lt' },
    { label: '小于等于', value: 'lte' },
  ];

  const sqlResultShapeOptions: SelectOption[] = [
    { label: '列表', value: 'rows' },
    { label: '首行', value: 'first' },
    { label: '标量', value: 'scalar' },
  ];
  const workflowLlmOutputFormatOptions: SelectOption[] = [
    { label: '文本', value: 'text' },
    { label: 'JSON 对象', value: 'json_object' },
  ];

  const detailPage = computed(() =>
    defineDetailPage<AiApplication | AiCapability>({
      id: 'ai.studio.detail',
      title: form.name || `${resourceLabel.value}配置`,
      description: form.app_key
        ? `${form.app_key} · ${isCapability.value ? '内部调用' : form.status === 'published' ? '已发布' : '草稿'}`
        : resourceFallbackDescription.value,
      kind: 'workspace-detail',
      variant: 'dense-data',
      density: 'compact',
      actions: [
        {
          key: 'back',
          label: '返回',
          onClick: () => router.push({ name: isPlatformCapabilityRoute.value ? 'ai-platform-capabilities' : 'ai-studio' }),
        },
        {
          key: 'save',
          label: '保存',
          loading: saving.value,
          onClick: saveCurrent,
        },
        ...(isCapability.value
          ? []
          : [
              {
                key: 'publish',
                label: '发布',
                type: 'primary',
                disabled: activeApp.value?.status === 'published',
                loading: publishing.value,
                onClick: publishCurrent,
              },
            ]),
      ],
    })
  );

  watch(runtimeVariableFields, syncRuntimeVariableValues, { immediate: true });
  watch(templateVariableKeys, syncVariablesSchemaFromTemplate);
  watch(workflowNodes, syncVariablesSchemaFromTemplate, { deep: true });
  watch(workflowExecutedEdgeIds, applyWorkflowExecutionEdgeClasses, { immediate: true });
  watch(selectedWorkflowNode, syncWorkflowSelectedStartNode, { immediate: true });
  watch(selectedWorkflowNode, syncSelectedWorkflowPromptAssets, { immediate: true });
  watch(activeWorkspace, (value) => {
    if (value === 'logs') void loadRunLogs();
  });
  watch(
    () => form.app_type,
    () => ensureWorkspaceMatchesAppType(),
    { immediate: true }
  );
  onBeforeUnmount(() => {
    cancelRunDraft({ silent: true });
    stopRunStopwatch();
    revokeHtmlPreviewObjectUrl();
  });

  async function reload() {
    const key = String(isCapability.value ? route.params.capabilityKey || '' : route.params.appKey || '');
    if (!key) {
      message.error(`${resourceLabel.value} Key 缺失`);
      return;
    }
    loading.value = true;
    try {
      if (isCapability.value) {
        const [capability] = await Promise.all([
          isPlatformCapabilityRoute.value ? getPlatformAiCapability(key) : getAiCapability(key),
          loadModelConfigs(),
          canUsePromptAsset.value ? loadPublishedPrompts() : Promise.resolve(),
        ]);
        selectCapability(capability);
      } else {
        const [app] = await Promise.all([getAiApplication(key), loadModelConfigs(), loadPublishedPrompts()]);
        selectApp(app);
      }
    } finally {
      loading.value = false;
    }
  }
  async function loadModelConfigs() {
    modelConfigLoading.value = true;
    try {
      const [modelPayload, policyPayload] = await Promise.all([getLlmModels(), getLlmRoutingPolicies()]);
      models.value = modelPayload.items || [];
      policies.value = policyPayload.items || [];
    } finally {
      modelConfigLoading.value = false;
    }
  }

  async function loadPublishedPrompts() {
    publishedPromptsLoading.value = true;
    try {
      const payload = await getPublishedPromptAssets({ page: 1, page_size: 100 });
      publishedPrompts.value = payload.items || [];
    } finally {
      publishedPromptsLoading.value = false;
    }
  }

  async function loadPublishedPromptDetail(promptKey: string) {
    if (!promptKey || publishedPromptDetails[promptKey]) return;
    publishedPromptDetails[promptKey] = await getPublishedPromptAsset(promptKey);
  }

  async function loadPlatformTenants() {
    if (platformTenants.value.length) return;
    platformTenantsLoading.value = true;
    try {
      const payload = await getTenants();
      platformTenants.value = (payload as { items?: Recordable[] }).items || [];
    } finally {
      platformTenantsLoading.value = false;
    }
  }

  async function loadPlatformPreviewModelOptions(tenantId: number) {
    platformPreviewModelsLoading.value = true;
    try {
      const payload = await getTenantAiCapabilityModelOptions(tenantId);
      platformPreviewModels.value = payload.models || [];
      platformPreviewPolicies.value = payload.routing_policies || [];
      if (!platformPreviewModelOptions.value.some((item) => item.value === platformPreviewForm.model)) {
        platformPreviewForm.model = String(platformPreviewModelOptions.value[0]?.value || '');
      }
    } finally {
      platformPreviewModelsLoading.value = false;
    }
  }

  async function loadRunLogs() {
    if (!form.app_key) return;
    runLogsLoading.value = true;
    try {
      const payload = isCapability.value
        ? isPlatformCapabilityRoute.value
          ? await getPlatformAiCapabilityRunLogs(form.app_key, 50)
          : await getAiCapabilityRunLogs(form.app_key, 50)
        : await getAiApplicationRunLogs(form.app_key, 50);
      runLogs.value = payload.items || [];
      if (!runLogs.value.some((item) => item.run_id === selectedRunLogId.value)) {
        selectedRunLogId.value = runLogs.value[0]?.run_id || '';
      }
    } finally {
      runLogsLoading.value = false;
    }
  }

  function switchWorkspace(key: WorkspaceKey) {
    if (isCapability.value && key === 'api') {
      activeWorkspace.value = 'orchestration';
      return;
    }
    if (key === 'agent' && !isAgentMode.value) {
      activeWorkspace.value = 'orchestration';
      return;
    }
    activeWorkspace.value = key;
  }

  function ensureWorkspaceMatchesAppType() {
    if (isAgentMode.value && !isCapability.value) {
      if (!workspaceTabs.value.some((item) => item.key === activeWorkspace.value)) {
        activeWorkspace.value = 'agent';
      }
      return;
    }
    if (activeWorkspace.value === 'agent') {
      activeWorkspace.value = 'orchestration';
    }
  }

  function selectApp(app: AiApplication) {
    Object.keys(variableTypeOverrides).forEach((key) => delete variableTypeOverrides[key]);
    Object.keys(variableLabelOverrides).forEach((key) => delete variableLabelOverrides[key]);
    Object.keys(variableOptionalOverrides).forEach((key) => delete variableOptionalOverrides[key]);
    Object.keys(runtimeVariableValues).forEach((key) => delete runtimeVariableValues[key]);
    activeApp.value = app;
    form.app_key = app.app_key;
    form.name = app.name;
    form.icon = String(app.runtime_config?.icon || 'robot');
    form.description = app.description || '';
    form.app_type = app.app_type;
    form.status = app.status;
    form.endpoint_slug = app.endpoint_slug || app.app_key;
    form.system_prompt = app.system_prompt || '';
    form.developer_prompt = app.developer_prompt || '';
    form.user_prompt_template = app.user_prompt_template || '';
    variablesSchemaText.value = stringifyJson(app.variables_schema || {});
    outputSchemaText.value = stringifyJson(app.output_schema || {});
    loadWorkflowDefinition(app.runtime_config?.workflow);
    systemPromptSource.value = app.runtime_config?.system_prompt_source === 'asset' ? 'asset' : 'inline';
    selectedSystemPromptAssetKey.value = String(app.runtime_config?.system_prompt_asset_key || '');
    selectedOutputFormat.value = normalizeOutputFormat(app.runtime_config?.output_format);
    if (selectedSystemPromptAssetKey.value) {
      void loadPublishedPromptDetail(selectedSystemPromptAssetKey.value);
    }
    selectedModelKey.value = String(app.model_preferences?.model || app.model_preferences?.route_key || '');
    runResult.value = null;
    runLogs.value = [];
    selectedRunLogId.value = '';
    streamThinkText.value = '';
    syncRuntimeVariableValues();
    ensureWorkspaceMatchesAppType();
  }

  function selectCapability(capability: AiCapability) {
    Object.keys(variableTypeOverrides).forEach((key) => delete variableTypeOverrides[key]);
    Object.keys(variableLabelOverrides).forEach((key) => delete variableLabelOverrides[key]);
    Object.keys(variableOptionalOverrides).forEach((key) => delete variableOptionalOverrides[key]);
    Object.keys(runtimeVariableValues).forEach((key) => delete runtimeVariableValues[key]);
    activeCapability.value = capability;
    activeApp.value = null;
    form.app_key = capability.capability_key;
    form.name = capability.name;
    form.icon = String(capability.runtime_config?.icon || 'api');
    form.description = capability.description || '';
    form.app_type = capability.binding_type === 'workflow_runtime' ? 'workflow' : 'single_turn_generation';
    form.status = capability.enabled ? 'published' : 'draft';
    form.endpoint_slug = capability.capability_key;
    form.system_prompt = capability.system_prompt || '';
    form.developer_prompt = capability.developer_prompt || '';
    form.user_prompt_template = capability.user_prompt_template || '';
    variablesSchemaText.value = stringifyJson(capability.input_schema || {});
    outputSchemaText.value = stringifyJson(capability.output_schema || {});
    loadWorkflowDefinition(capability.runtime_config?.workflow);
    systemPromptSource.value = canUsePromptAsset.value && capability.runtime_config?.system_prompt_source === 'asset' ? 'asset' : 'inline';
    selectedSystemPromptAssetKey.value = canUsePromptAsset.value ? String(capability.runtime_config?.system_prompt_asset_key || '') : '';
    selectedOutputFormat.value = normalizeOutputFormat(capability.runtime_config?.output_format);
    if (selectedSystemPromptAssetKey.value) {
      void loadPublishedPromptDetail(selectedSystemPromptAssetKey.value);
    }
    selectedModelKey.value = String(capability.model_preferences?.model || capability.model_preferences?.route_key || '');
    runResult.value = null;
    runLogs.value = [];
    selectedRunLogId.value = '';
    streamThinkText.value = '';
    syncRuntimeVariableValues();
    ensureWorkspaceMatchesAppType();
  }

  async function saveCurrent(options: { silent?: boolean; refresh?: boolean } = {}) {
    if (!form.app_key || !form.name) {
      message.warning(`${resourceLabel.value} Key 和名称不能为空`);
      return null;
    }
    if (!isWorkflowMode.value && !selectedModelKey.value) {
      message.warning(isPlatformCapabilityRoute.value ? '请填写模型路由 Key' : '请选择模型配置');
      return null;
    }
    if (!isWorkflowMode.value && systemPromptSource.value === 'asset' && !selectedSystemPromptAssetKey.value) {
      message.warning('请选择已发布的提示词');
      return null;
    }
    if (!options.silent) saving.value = true;
    try {
      const saved = isCapability.value
        ? await saveCapabilityPayload()
        : await updateAiApplication(form.app_key, buildPayload());
      if (!options.silent) message.success(`${resourceLabel.value}已保存`);
      if (options.refresh !== false) {
        if (isCapability.value) selectCapability(saved as AiCapability);
        else selectApp(saved as AiApplication);
      } else {
        if (isCapability.value) activeCapability.value = saved as AiCapability;
        else activeApp.value = saved as AiApplication;
      }
      return saved as AiApplication | AiCapability;
    } finally {
      if (!options.silent) saving.value = false;
    }
  }
  async function publishCurrent() {
    publishing.value = true;
    try {
      const saved = await saveCurrent({ silent: true });
      if (!saved) return;
      const published = await publishAiApplication(form.app_key);
      message.success('AI 应用已发布');
      selectApp(published as AiApplication);
    } finally {
      publishing.value = false;
    }
  }

  async function runDraft() {
    if (running.value) return;
    if (isAgentMode.value) {
      activeWorkspace.value = 'agent';
      return;
    }
    if (isWorkflowMode.value) {
      openWorkflowRunPanel();
      return;
    }
    if (isPlatformCapabilityRoute.value) {
      await openPlatformPreviewModal();
      return;
    }
    await executeDraftRun();
  }

  function openWorkflowRunPanel() {
    syncRuntimeVariableValues();
    workflowRunPanelVisible.value = !workflowRunPanelVisible.value;
  }

  async function confirmWorkflowRun() {
    if (running.value) return;
    if (isPlatformCapabilityRoute.value) {
      workflowRunPanelVisible.value = true;
      await openPlatformPreviewModal();
      return;
    }
    const missingRequired = findUnfilledRequiredVariables(workflowInputVariableFields.value);
    if (missingRequired.length) {
      message.warning(`请填写运行变量：${missingRequired.join('、')}`);
      return;
    }
    workflowRunPanelVisible.value = true;
    await executeDraftRun();
  }

  async function executeDraftRun() {
    const missingRequired = findUnfilledRequiredVariables(isWorkflowMode.value ? workflowInputVariableFields.value : runtimeVariableFields.value);
    if (missingRequired.length) {
      message.warning(`请填写运行变量：${missingRequired.join('、')}`);
      return;
    }
    running.value = true;
    if (isWorkflowMode.value) {
      workflowRunErrorText.value = '';
      workflowRunStatusText.value = '准备运行';
    }
    runAbortController = new AbortController();
    startRunStopwatch();
    try {
      if (isWorkflowMode.value) workflowRunStatusText.value = '保存草稿';
      const saved = await saveCurrent({ silent: true, refresh: false });
      if (!saved) {
        if (isWorkflowMode.value) {
          workflowRunStatusText.value = '执行失败';
          workflowRunErrorText.value = "保存草稿失败，请检查必填配置。";
        }
        return;
      }
      if (isWorkflowMode.value) {
        workflowRunStatusText.value = '保存完成';
        workflowRunPanelVisible.value = true;
      }
      runResult.value = { answer: '', trace_id: '', usage: {} };
      streamThinkText.value = '';
      if (isWorkflowMode.value) workflowRunStatusText.value = '请求后端执行';
      await runDraftStream({
        variables: buildRuntimeVariables(),
        ...runOutputFormatPayload(),
      }, runAbortController.signal);
      if (isWorkflowMode.value) workflowRunStatusText.value = '执行完成';
      if (activeWorkspace.value === 'logs') {
        await loadRunLogs();
      }
    } catch (error) {
      if (isAbortError(error)) {
        message.info('已取消本次运行');
        return;
      }
      const text = runtimeErrorMessage(error);
      if (isWorkflowMode.value) {
        workflowRunStatusText.value = '执行失败';
        workflowRunErrorText.value = text;
      }
      message.error(text);
    } finally {
      finishRunStopwatch();
      running.value = false;
      runAbortController = null;
    }
  }

  async function openPlatformPreviewModal() {
    platformPreviewForm.model = selectedModelKey.value || platformPreviewForm.model;
    platformPreviewModalVisible.value = true;
    await loadPlatformTenants();
    if (!platformPreviewForm.tenant_id && platformTenantOptions.value.length) {
      platformPreviewForm.tenant_id = Number(platformTenantOptions.value[0].value);
    }
    if (platformPreviewForm.tenant_id) {
      await loadPlatformPreviewModelOptions(Number(platformPreviewForm.tenant_id));
    }
  }

  async function handlePlatformPreviewTenantChange(value: number | null) {
    platformPreviewForm.model = '';
    platformPreviewModels.value = [];
    platformPreviewPolicies.value = [];
    if (value) {
      await loadPlatformPreviewModelOptions(Number(value));
    }
  }

  async function confirmPlatformPreviewRun() {
    if (running.value) return;
    if (!platformPreviewForm.tenant_id) {
      message.warning('请选择租户');
      return;
    }
    if (!platformPreviewForm.model) {
      message.warning('请选择租户模型或路由');
      return;
    }
    const missingRequired = findUnfilledRequiredVariables(isWorkflowMode.value ? workflowInputVariableFields.value : runtimeVariableFields.value);
    if (missingRequired.length) {
      message.warning(`请填写运行变量：${missingRequired.join('、')}`);
      return;
    }
    running.value = true;
    platformPreviewModalVisible.value = false;
    startRunStopwatch();
    try {
      const saved = await saveCurrent({ silent: true, refresh: false });
      if (!saved) return;
      runResult.value = { answer: '', trace_id: '', usage: {} };
      streamThinkText.value = '';
      const result = await previewPlatformAiCapability(form.app_key, {
        tenant_id: Number(platformPreviewForm.tenant_id),
        model: platformPreviewForm.model,
        variables: buildRuntimeVariables(),
        ...runOutputFormatPayload(),
      });
      runResult.value = result;
      if (activeWorkspace.value === 'logs') {
        await loadRunLogs();
      }
    } finally {
      finishRunStopwatch();
      running.value = false;
    }
  }

  function cancelRunDraft(options: { silent?: boolean } = {}) {
    if (!runAbortController) return;
    runAbortController.abort();
    if (!options.silent) message.info('正在取消运行');
  }

  function loadWorkflowDefinition(definition: unknown) {
    const workflow = asSchemaRecord(definition) || defaultWorkflowDefinition();
    const nodes = Array.isArray(workflow.nodes) ? workflow.nodes : defaultWorkflowDefinition().nodes;
    const edges = Array.isArray(workflow.edges) ? workflow.edges : defaultWorkflowDefinition().edges;
    workflowNodes.value = nodes.map((node, index) => normalizeWorkflowNode(node, index));
    ensureWorkflowStartVariablesFromSchema();
    workflowEdges.value = edges.map((edge, index) => normalizeWorkflowEdge(edge, index));
    selectedWorkflowNodeId.value = workflowNodes.value[0]?.id || '';
    selectedWorkflowEdgeId.value = '';
    openWorkflowNodeMenuId.value = '';
  }

  function normalizeWorkflowNode(node: unknown, index: number): WorkflowNode {
    const record = asSchemaRecord(node) || {};
    const data = asSchemaRecord(record.data) || {};
    const type = String(record.type || 'llm') as WorkflowNodeType;
    const sqlData =
      type === 'sql_query'
        ? {
            params_text: stringifyJson(Array.isArray(data.params) ? data.params : []),
            result_shape: String(data.result_shape || 'rows'),
            max_rows: Number(data.max_rows || 100),
            data_access: asSchemaRecord(data.data_access) || { resource_key: 'ai_applications.workflow_sql', tenant_column: 'tenant_id' },
          }
        : {};
    const llmData =
      type === 'llm'
        ? {
            response_format_type: workflowLlmResponseFormatType(data.response_format),
          }
        : {};
    return {
      id: String(record.id || `${type}_${index + 1}`),
      type,
      label: String(data.label || workflowNodeTypeLabel(type)),
      position: asWorkflowPosition(record.position, index),
      data: {
        label: String(data.label || workflowNodeTypeLabel(type)),
        ...data,
        ...(type === 'start' ? { variables: normalizeWorkflowStartVariables(data.variables) } : {}),
        ...llmData,
        ...sqlData,
      },
    };
  }

  function normalizeWorkflowEdge(edge: unknown, index: number): WorkflowEdge {
    const record = asSchemaRecord(edge) || {};
    const source = String(record.source || '');
    const target = String(record.target || '');
    return {
      id: String(record.id || `${source}-${target}-${index}`),
      source,
      target,
      sourceHandle: String(record.sourceHandle || record.source_handle || '') || undefined,
      targetHandle: String(record.targetHandle || record.target_handle || '') || undefined,
      type: String(record.type || 'smoothstep'),
      label: workflowEdgeLabel(String(record.sourceHandle || record.source_handle || '')),
    };
  }

  function asWorkflowPosition(value: unknown, index: number) {
    const record = asSchemaRecord(value);
    if (record && typeof record.x === 'number' && typeof record.y === 'number') {
      return { x: record.x, y: record.y };
    }
    return { x: 80 + index * 260, y: index % 2 ? 90 : 180 };
  }

  function workflowDefinitionPayload() {
    return {
      nodes: workflowNodes.value.map((node) => ({
        id: node.id,
        type: node.type,
        position: node.position,
        data: workflowNodeDataPayload(node),
      })),
      edges: workflowEdges.value.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        ...(edge.sourceHandle ? { sourceHandle: edge.sourceHandle } : {}),
        ...(edge.targetHandle ? { targetHandle: edge.targetHandle } : {}),
      })),
    };
  }

  function workflowNodeDataPayload(node: WorkflowNode) {
    const data = { ...(node.data || {}), label: node.data?.label || workflowNodeTypeLabel(node.type as WorkflowNodeType) };
    if (node.type === 'start') {
      data.variables = normalizeWorkflowStartVariables(data.variables, { stripInternalId: true });
    }
    if (node.type === 'sql_query') {
      data.params = parseJsonArraySilently(String(data.params_text || '')) || [];
      delete data.params_text;
      data.result_shape = data.result_shape || 'rows';
      data.max_rows = Math.max(1, Math.min(1000, Number(data.max_rows || 100)));
      data.data_access = asSchemaRecord(data.data_access) || { resource_key: 'ai_applications.workflow_sql', tenant_column: 'tenant_id' };
    }
    if (node.type === 'llm') {
      data.response_format =
        data.response_format_type === 'json_object' ? { type: 'json_object' } : undefined;
      delete data.response_format_type;
    }
    return data;
  }

  function defaultWorkflowDefinition() {
    return {
      nodes: [
        {
          id: 'start',
          type: 'start',
          position: { x: 80, y: 160 },
          data: {
            label: '开始',
            variables: [
              {
                id: createWorkflowStartVariableId(),
                key: 'question',
                label: '我的问题',
                type: 'text',
                required: true,
                description: 'Workflow 运行时输入的问题',
              },
            ],
          },
        },
        {
          id: 'llm_1',
          type: 'llm',
          position: { x: 360, y: 120 },
          data: {
            label: 'LLM',
            model: selectedModelKey.value || 'dashscope.qwen-plus',
            system_prompt: '你是一个专业、简洁的助手。',
            user_prompt_template: '请回答：{{question}}',
            output_key: 'answer',
            response_format_type: 'text',
          },
        },
        { id: 'end', type: 'end', position: { x: 660, y: 160 }, data: { label: '结束', output: '{{answer}}' } },
      ],
      edges: [
        { id: 'start-llm_1', source: 'start', target: 'llm_1' },
        { id: 'llm_1-end', source: 'llm_1', target: 'end' },
      ],
    };
  }

  function addWorkflowNode(type: Exclude<WorkflowNodeType, 'start'>, position?: XYPosition) {
    const count = workflowNodes.value.filter((node) => node.type === type).length + 1;
    const id = `${type}_${Date.now().toString(36)}`;
    const data: Record<string, any> = { label: `${workflowNodeTypeLabel(type)} ${count}` };
    if (type === 'llm') {
      data.model = selectedModelKey.value || modelConfigOptions.value[0]?.value || '';
      data.system_prompt_source = 'inline';
      data.system_prompt_asset_key = '';
      data.system_prompt = '你是一个专业、简洁的助手。';
      data.user_prompt_template = '请处理：{{input}}';
      data.output_key = `llm_${count}_output`;
      data.response_format_type = 'text';
    }
    if (type === 'sql_query') {
      data.sql = 'SELECT tenant_id, description, product_line, primary_component FROM workbench_function_points';
      data.params_text = '[]';
      data.output_key = count === 1 ? 'records' : `records_${count}`;
      data.result_shape = 'rows';
      data.max_rows = 100;
      data.data_access = { resource_key: 'ai_applications.workflow_sql', tenant_column: 'tenant_id' };
    }
    if (type === 'condition') {
      data.left = '{{input}}';
      data.operator = 'exists';
      data.right = '';
    }
    if (type === 'end') {
      data.output = '{{last.answer}}';
    }
    workflowNodes.value.push({
      id,
      type,
      label: data.label,
      position: position || { x: 260 + count * 80, y: 120 + count * 40 },
      data,
    });
    selectedWorkflowNodeId.value = id;
    selectedWorkflowEdgeId.value = '';
    openWorkflowNodeMenuId.value = '';
    closeWorkflowCanvasMenu();
  }

  function handleWorkflowNodeClick(event: { node: WorkflowNode }) {
    selectedWorkflowNodeId.value = event.node.id;
    selectedWorkflowEdgeId.value = '';
    closeWorkflowCanvasMenu();
  }

  function handleWorkflowEdgeClick(event: { edge: WorkflowEdge }) {
    selectedWorkflowEdgeId.value = event.edge.id;
    selectedWorkflowNodeId.value = '';
    openWorkflowNodeMenuId.value = '';
    closeWorkflowCanvasMenu();
  }

  function handleWorkflowPaneClick() {
    selectedWorkflowNodeId.value = '';
    selectedWorkflowEdgeId.value = '';
    openWorkflowNodeMenuId.value = '';
    closeWorkflowCanvasMenu();
  }

  function handleWorkflowPaneContextMenu(event: MouseEvent) {
    event.preventDefault();
    selectedWorkflowNodeId.value = '';
    selectedWorkflowEdgeId.value = '';
    openWorkflowNodeMenuId.value = '';
    const panelRect = workflowCanvasPanelRef.value?.getBoundingClientRect();
    const menuWidth = 220;
    const menuHeight = 252;
    const rawX = panelRect ? event.clientX - panelRect.left : event.clientX;
    const rawY = panelRect ? event.clientY - panelRect.top : event.clientY;
    workflowCanvasMenu.x = Math.max(8, Math.min(rawX, (panelRect?.width || rawX + menuWidth) - menuWidth - 8));
    workflowCanvasMenu.y = Math.max(8, Math.min(rawY, (panelRect?.height || rawY + menuHeight) - menuHeight - 8));
    workflowCanvasMenu.position = project({ x: event.clientX, y: event.clientY });
    workflowCanvasMenu.visible = true;
  }

  function addWorkflowNodeFromCanvasMenu(type: Exclude<WorkflowNodeType, 'start'>) {
    addWorkflowNode(type, {
      x: Math.round(workflowCanvasMenu.position.x),
      y: Math.round(workflowCanvasMenu.position.y),
    });
  }

  function closeWorkflowCanvasMenu() {
    workflowCanvasMenu.visible = false;
  }

  function handleWorkflowConnect(connection: Connection) {
    if (!connection.source || !connection.target || connection.source === connection.target) return;
    closeWorkflowCanvasMenu();
    const exists = workflowEdges.value.some(
      (edge) =>
        edge.source === connection.source &&
        edge.target === connection.target &&
        (edge.sourceHandle || '') === (connection.sourceHandle || '') &&
        (edge.targetHandle || '') === (connection.targetHandle || '')
    );
    if (exists) return;
    workflowEdges.value.push({
      id: `edge_${connection.source}_${connection.target}_${Date.now().toString(36)}`,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle || undefined,
      targetHandle: connection.targetHandle || undefined,
      type: 'smoothstep',
      label: workflowEdgeLabel(connection.sourceHandle || ''),
    });
    selectedWorkflowEdgeId.value = workflowEdges.value[workflowEdges.value.length - 1]?.id || '';
    selectedWorkflowNodeId.value = '';
  }

  function toggleWorkflowNodeMenu(nodeId: string) {
    openWorkflowNodeMenuId.value = openWorkflowNodeMenuId.value === nodeId ? '' : nodeId;
    selectedWorkflowNodeId.value = nodeId;
    selectedWorkflowEdgeId.value = '';
    closeWorkflowCanvasMenu();
  }

  function openWorkflowNodeConfig(nodeId: string) {
    selectedWorkflowNodeId.value = nodeId;
    selectedWorkflowEdgeId.value = '';
    openWorkflowNodeMenuId.value = '';
    closeWorkflowCanvasMenu();
  }

  function runWorkflowNode(nodeId: string) {
    openWorkflowNodeConfig(nodeId);
    message.info('节点单步运行将在 Workflow Runtime 执行链路接入后启用');
  }

  function workflowNodePromptSource(node: WorkflowNode): PromptSource {
    return canUsePromptAsset.value && node.data?.system_prompt_source === 'asset' ? 'asset' : 'inline';
  }

  function workflowNodePromptAssetKey(node: WorkflowNode) {
    return String(node.data?.system_prompt_asset_key || '');
  }

  function workflowNodePublishedPrompt(node: WorkflowNode) {
    const key = workflowNodePromptAssetKey(node);
    return key ? publishedPromptDetails[key] : null;
  }

  function updateWorkflowNodePromptSource(node: WorkflowNode, value: string | number | boolean | null) {
    const source: PromptSource = value === 'asset' ? 'asset' : 'inline';
    node.data.system_prompt_source = source;
    if (source === 'asset') {
      const assetKey = workflowNodePromptAssetKey(node);
      if (assetKey) void applyWorkflowNodePromptAsset(node, assetKey);
    }
  }

  function updateWorkflowNodePromptAsset(node: WorkflowNode, value: string | number | null) {
    const assetKey = String(value || '');
    node.data.system_prompt_asset_key = assetKey;
    node.data.system_prompt_source = assetKey ? 'asset' : 'inline';
    if (assetKey) void applyWorkflowNodePromptAsset(node, assetKey);
  }

  async function applyWorkflowNodePromptAsset(node: WorkflowNode, assetKey: string) {
    await loadPublishedPromptDetail(assetKey);
    const prompt = publishedPromptDetails[assetKey];
    if (!prompt) return;
    node.data.system_prompt = prompt.system_prompt || '';
  }

  function syncSelectedWorkflowPromptAssets() {
    const node = selectedWorkflowNode.value;
    if (!node || node.type !== 'llm' || !canUsePromptAsset.value) return;
    const assetKey = workflowNodePromptAssetKey(node);
    if (workflowNodePromptSource(node) === 'asset' && assetKey) {
      void applyWorkflowNodePromptAsset(node, assetKey);
    }
  }

  function syncWorkflowSelectedStartNode() {
    if (selectedWorkflowNode.value?.type !== 'start') return;
    selectedWorkflowNode.value.data.variables = normalizeWorkflowStartVariables(selectedWorkflowNode.value.data.variables, {
      keepEmptyKeys: true,
    });
  }

  function addWorkflowStartVariable(node: WorkflowNode) {
    const existingKeys = new Set(validWorkflowStartVariables(node.data.variables).map((variable) => variable.key));
    let index = existingKeys.size + 1;
    let key = `input_${index}`;
    while (existingKeys.has(key)) {
      index += 1;
      key = `input_${index}`;
    }
    node.data.variables = [
      ...normalizeWorkflowStartVariables(node.data.variables, { keepEmptyKeys: true }),
      {
        id: createWorkflowStartVariableId(),
        key,
        label: `输入变量 ${index}`,
        type: 'text',
        required: true,
        description: '',
      },
    ];
    syncWorkflowStartVariables();
  }

  function removeWorkflowStartVariable(index: number) {
    const node = workflowStartNode.value;
    if (!node) return;
    node.data.variables = normalizeWorkflowStartVariables(node.data.variables, { keepEmptyKeys: true }).filter((_, itemIndex) => itemIndex !== index);
    syncWorkflowStartVariables();
  }

  function syncWorkflowStartVariables() {
    const node = workflowStartNode.value;
    if (!node) return;
    node.data.variables = normalizeWorkflowStartVariables(node.data.variables, {
      keepEmptyKeys: true,
      preserveDraftKeys: true,
    });
    syncVariablesSchemaFromTemplate();
  }

  function normalizeWorkflowStartVariables(
    value: unknown,
    options: { keepEmptyKeys?: boolean; preserveDraftKeys?: boolean; stripInternalId?: boolean } = {}
  ): WorkflowStartVariable[] {
    const rows = Array.isArray(value) ? value : [];
    const seen = new Set<string>();
    return rows
      .map((item) => {
        const record = asSchemaRecord(item);
        if (!record) return null;
        const key = options.preserveDraftKeys ? String(record.key || record.name || '').trim() : normalizeWorkflowVariableKey(record.key || record.name);
        const id = String(record.id || createWorkflowStartVariableId());
        const dedupeKey = key ? `key:${key}` : `id:${id}`;
        if ((!key && !options.keepEmptyKeys) || seen.has(dedupeKey)) return null;
        seen.add(dedupeKey);
        const variable = {
          id,
          key,
          label: typeof record.label === 'undefined' ? String(record.title || '') : String(record.label || ''),
          type: resolveRuntimeVariableType(String(record.type || '')),
          required: record.required !== false,
          description: String(record.description || record.help || ''),
        };
        if (options.stripInternalId) {
          delete (variable as Partial<WorkflowStartVariable>).id;
        }
        return variable;
      })
      .filter(Boolean) as WorkflowStartVariable[];
  }

  function validWorkflowStartVariables(value: unknown): WorkflowStartVariable[] {
    return normalizeWorkflowStartVariables(value).filter((variable) => !!normalizeWorkflowVariableKey(variable.key));
  }

  function createWorkflowStartVariableId() {
    return `start_var_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
  }

  function normalizeWorkflowVariableKey(value: unknown) {
    return String(value || '')
      .trim()
      .replace(/\s+/g, '_')
      .replace(/[^a-zA-Z0-9_.-]/g, '');
  }

  function workflowStartVariableCount(data: Record<string, any>) {
    return Array.isArray(data?.variables)
      ? data.variables.filter((item: unknown) => {
          const record = asSchemaRecord(item);
          return !!normalizeWorkflowVariableKey(record?.key || record?.name);
        }).length
      : 0;
  }

  function ensureWorkflowStartVariablesFromSchema() {
    const node = workflowNodes.value.find((item) => item.type === 'start');
    if (!node) return;
    const current = normalizeWorkflowStartVariables(node.data.variables);
    if (current.length) {
      node.data.variables = current;
      return;
    }
    node.data.variables = workflowStartVariablesFromSchema(parsedVariablesSchema.value);
  }

  function workflowStartVariablesFromSchema(schema: SchemaRecord | null): WorkflowStartVariable[] {
    const { entries, requiredKeys } = collectSchemaEntries(schema || undefined);
    return [...entries.entries()]
      .map(([key, raw]) => {
        const node = asSchemaRecord(raw);
        const label = String(node?.label || node?.title || node?.name || (typeof raw === 'string' ? raw : '') || key);
        return {
          id: createWorkflowStartVariableId(),
          key,
          label,
          type: resolveRuntimeVariableType(String(node?.type || '')),
          required: node?.required === false ? false : requiredKeys.has(key) || node?.required === true,
          description: String(node?.description || node?.help || ''),
        };
      })
      .filter((variable) => !!variable.key);
  }

  function duplicateWorkflowNode(nodeId: string) {
    const source = workflowNodes.value.find((node) => node.id === nodeId);
    if (!source || source.type === 'start') return;
    const id = `${source.type}_${Date.now().toString(36)}`;
    const data = { ...(source.data || {}), label: `${workflowNodeTitle(source)} 副本` };
    workflowNodes.value.push({
      id,
      type: source.type,
      label: data.label,
      position: {
        x: Number(source.position?.x || 0) + 44,
        y: Number(source.position?.y || 0) + 44,
      },
      data,
    });
    selectedWorkflowNodeId.value = id;
    selectedWorkflowEdgeId.value = '';
    openWorkflowNodeMenuId.value = '';
  }

  function deleteWorkflowNode(nodeId: string) {
    const node = workflowNodes.value.find((item) => item.id === nodeId);
    if (!node) return;
    if (node.type === 'start') {
      message.warning('开始节点不能删除');
      return;
    }
    workflowNodes.value = workflowNodes.value.filter((item) => item.id !== nodeId);
    workflowEdges.value = workflowEdges.value.filter((edge) => edge.source !== nodeId && edge.target !== nodeId);
    if (selectedWorkflowNodeId.value === nodeId) selectedWorkflowNodeId.value = '';
    selectedWorkflowEdgeId.value = '';
    openWorkflowNodeMenuId.value = '';
  }

  function deleteWorkflowEdge(edgeId = selectedWorkflowEdgeId.value) {
    if (!edgeId) return;
    workflowEdges.value = workflowEdges.value.filter((edge) => edge.id !== edgeId);
    if (selectedWorkflowEdgeId.value === edgeId) selectedWorkflowEdgeId.value = '';
  }

  function workflowEdgeLabel(sourceHandle?: string) {
    if (sourceHandle === 'true') return '是';
    if (sourceHandle === 'false') return '否';
    return undefined;
  }

  function workflowNodeTitle(node: WorkflowNode) {
    return String(node.data?.label || workflowNodeTypeLabel(node.type as WorkflowNodeType));
  }

  function applyWorkflowExecutionEdgeClasses() {
    const activeEdgeIds = workflowExecutedEdgeIds.value;
    let changed = false;
    const nextEdges = workflowEdges.value.map((edge) => {
      const className = activeEdgeIds.has(edge.id) ? 'is-workflow-executed-edge' : '';
      if (String((edge as WorkflowEdge & { class?: string }).class || '') === className) return edge;
      changed = true;
      return { ...edge, class: className };
    });
    if (changed) workflowEdges.value = nextEdges;
  }

  function workflowNodeCardClass(nodeId: string, selected: boolean) {
    return {
      'is-selected': selected,
      'is-executed': workflowExecutedNodeIds.value.has(nodeId),
      'is-failed': workflowFailedNodeIds.value.has(nodeId),
    };
  }

  function workflowTraceNodeTitle(traceNode: WorkflowTraceNode) {
    if (traceNode.title) return traceNode.title;
    const node = workflowNodes.value.find((item) => item.id === traceNode.node_id);
    return node ? workflowNodeTitle(node) : traceNode.node_id;
  }

  function workflowTraceNodeIcon(type: string) {
    if (type === 'start') return 'S';
    if (type === 'llm') return 'AI';
    if (type === 'sql_query' || type === 'sql') return 'SQL';
    if (type === 'condition') return 'IF';
    if (type === 'end') return 'E';
    return type.slice(0, 2).toUpperCase();
  }

  function workflowTraceStatus(traceNode: WorkflowTraceNode) {
    return traceNode.status === 'failed' ? 'failed' : traceNode.status === 'running' ? 'running' : 'success';
  }

  function resetWorkflowDebugRun() {
    runResult.value = null;
    workflowRunErrorText.value = '';
    workflowRunStatusText.value = '等待运行';
    streamThinkText.value = '';
    lastRunElapsedMs.value = 0;
    runningElapsedMs.value = 0;
  }

  function runtimeErrorMessage(error: unknown) {
    if (error instanceof Error) {
      const parsed = parseRuntimeErrorPayload(error.message);
      return parsed || error.message || '运行失败';
    }
    return String(error || '运行失败');
  }

  function parseRuntimeErrorPayload(value: string) {
    const text = String(value || '').trim();
    if (!text) return '';
    try {
      const payload = JSON.parse(text);
      return extractRuntimeErrorMessage(payload);
    } catch {
      return text;
    }
  }

  function extractRuntimeErrorMessage(payload: unknown): string {
    if (!payload || typeof payload !== 'object') return '';
    const record = payload as Record<string, any>;
    const detail = record.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object') {
      const message = (detail as Record<string, any>).message;
      if (message) return String(message);
    }
    if (record.message) return String(record.message);
    if (record.error) return String(record.error);
    return '';
  }

  function conditionOperatorLabel(operator: unknown) {
    return String(conditionOperatorOptions.find((item) => item.value === operator)?.label || operator || '存在');
  }

  function sqlOutputVariableHint(value: unknown) {
    const key = String(value || 'records').trim() || 'records';
    return `后续节点可用 {{${key}.rows}}、{{${key}.first.xxx}}、{{${key}.scalar}} 引用。`;
  }

  function compactSqlPreview(value: unknown) {
    const text = String(value || '').replace(/\s+/g, ' ').trim();
    if (!text) return '执行只读 SQL，并将结果写入输出变量';
    return text.length > 120 ? `${text.slice(0, 120)}...` : text;
  }

  function workflowLlmResponseFormatType(value: unknown) {
    const responseFormat = asSchemaRecord(value);
    return responseFormat?.type === 'json_object' ? 'json_object' : 'text';
  }

  function workflowNodeTypeLabel(type: WorkflowNodeType | string) {
    if (type === 'start') return '开始';
    if (type === 'llm') return 'LLM';
    if (type === 'sql_query') return 'SQL 查询';
    if (type === 'condition') return '条件判断';
    if (type === 'end') return '结束';
    return String(type);
  }

  async function handleMediaVariableChange(field: RuntimeVariableField, options: { fileList: UploadFileInfo[] }) {
    const uploadFile = options.fileList[0]?.file as File | undefined;
    if (!uploadFile) {
      runtimeVariableValues[field.key] = null;
      return;
    }
    if (uploadFile.size > maxMediaVariableBytes(field)) {
      message.warning(`${field.label} 文件过大，请选择 ${formatBytes(maxMediaVariableBytes(field))} 以内的文件`);
      runtimeVariableValues[field.key] = null;
      return;
    }
    try {
      const text = await readTextPreviewIfSupported(uploadFile);
      const baseValue: RuntimeMediaVariableValue = {
        type: field.type as RuntimeMediaVariableValue['type'],
        name: uploadFile.name,
        mime_type: uploadFile.type || fallbackMimeType(field),
        size: uploadFile.size,
        ...(text ? { text } : {}),
      };
      try {
        const uploaded = await uploadManagedFile({
          file: uploadFile,
          visibility: 'tenant',
          metadata: {
            source: 'ai_application_runtime',
            variable_key: field.key,
            variable_type: field.type,
          },
        });
        const item = uploaded.item;
        runtimeVariableValues[field.key] = {
          ...baseValue,
          file_ref: `file_${item.id}`,
          file_id: item.id,
          sha256: item.sha256,
          preview_url: `/files/${item.id}/preview`,
          storage_status: 'stored',
          redacted: true,
        };
      } catch (uploadError) {
        runtimeVariableValues[field.key] = {
          ...baseValue,
          file_ref: null,
          storage_status: 'unavailable',
          redacted: true,
          reason: 'file_upload_unavailable',
        };
        message.warning('文件上传能力不可用，本次运行日志仅记录文件名和脱敏标记');
      }
    } catch (error) {
      runtimeVariableValues[field.key] = null;
      message.error(error instanceof Error ? error.message : String(error));
    }
  }

  async function runDraftStream(payload: { variables: Record<string, unknown>; response_format?: Record<string, unknown> }, signal?: AbortSignal) {
    const response = isCapability.value
      ? await fetchAiCapabilityStream(form.app_key, payload, signal)
      : await fetchAiApplicationDraftStream(form.app_key, payload, signal);
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }
    if (!response.body) {
      throw new Error('当前浏览器不支持流式响应');
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let content = '';
    let reasoning = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';
      for (const event of events) {
        const parsed = parseStreamEvent(event);
        if (!parsed.data || parsed.data === '[DONE]') continue;
        if (parsed.type === 'error') {
          const errorPayload = parseStreamPayload(parsed.data);
          throw new Error(extractRuntimeErrorMessage(errorPayload) || parsed.data || 'AI 应用运行失败');
        }
        const payloadData = parseStreamPayload(parsed.data);
        if (parsed.type === 'meta') {
          runResult.value = {
            ...(runResult.value || { answer: '', usage: {} }),
            trace_id: payloadData.trace_id || '',
          };
          continue;
        }
        if (parsed.type === 'trace') {
          runResult.value = {
            ...(runResult.value || { answer: content, trace_id: payloadData.trace_id || '', usage: {} }),
            trace_id: payloadData.trace_id || runResult.value?.trace_id || '',
            trace: payloadData.trace,
          };
          continue;
        }
        const delta = payloadData?.choices?.[0]?.delta || {};
        const reasoningDelta = delta.reasoning_content || delta.reasoning || delta.think || delta.thinking || '';
        const contentDelta = delta.content || '';
        if (reasoningDelta) {
          reasoning += reasoningDelta;
          streamThinkText.value = reasoning;
        }
        if (contentDelta) {
          content += contentDelta;
          const parsedContent = splitThinkContent(content);
          streamThinkText.value = reasoning || parsedContent.think;
          runResult.value = {
            ...(runResult.value || { trace_id: '', usage: {} }),
            answer: content,
          };
        }
      }
    }
  }

  function parseStreamPayload(data: string) {
    try {
      return JSON.parse(data);
    } catch {
      return { message: data };
    }
  }

  function parseStreamEvent(event: string) {
    const type =
      event
        .split('\n')
        .find((line) => line.startsWith('event: '))
        ?.slice(7)
        .trim() || 'message';
    const data =
      event
        .split('\n')
        .find((line) => line.startsWith('data: '))
        ?.slice(6)
        .trim() || '';
    return { type, data };
  }

  function isAbortError(error: unknown) {
    return error instanceof DOMException && error.name === 'AbortError';
  }

  function splitThinkContent(content: string) {
    const match = content.match(/<think\b[^>]*>([\s\S]*?)(?:<\/think>|$)/i);
    if (!match) {
      return { think: '', answer: content.trim() };
    }
    const answer = content.replace(match[0], '').trim();
    return {
      think: match[1].trim(),
      answer,
    };
  }

  function runOutputFormatPayload() {
    if (selectedOutputFormat.value !== 'json') return {};
    return {
      response_format: { type: 'json_object' },
    };
  }

  function normalizeOutputFormat(value: unknown): OutputFormat {
    return value === 'html' || value === 'json' ? value : 'markdown';
  }

  function renderAnswer(value: string, format: OutputFormat): RenderedOutput {
    if (format === 'html') {
      const rawContent = normalizeHtmlOutput(value);
      return {
        kind: 'html',
        content: allowHtmlScripts.value ? rawContent : staticHtmlOutput(rawContent),
        rawContent,
      };
    }
    if (format === 'json') {
      return { kind: 'json', content: normalizeJsonOutput(value) };
    }
    return { kind: 'markdown', content: renderMarkdown(value) };
  }

  function normalizeHtmlOutput(value: string) {
    const content = extractFencedBlock(value, ['html']) || extractHtmlDocument(value) || value.trim();
    if (!content) return '';
    if (/<!doctype\s+html|<html[\s>]/i.test(content)) {
      return content;
    }
    return `<!doctype html><html><head><meta charset="UTF-8"><base target="_blank"></head><body>${content}</body></html>`;
  }

  function staticHtmlOutput(value: string) {
    if (!value) return '';
    return value
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/\s+on[a-z]+\s*=\s*"[^"]*"/gi, '')
      .replace(/\s+on[a-z]+\s*=\s*'[^']*'/gi, '')
      .replace(/\s+on[a-z]+\s*=\s*[^\s>]+/gi, '')
      .replace(/\s+(src|href)\s*=\s*(['"])(?!https?:|data:|mailto:|tel:|#|\/\/)(.*?)\2/gi, ' $1="#"');
  }

  function normalizeJsonOutput(value: string) {
    const content = extractFencedBlock(value, ['json']) || extractJsonCandidate(value) || value.trim();
    if (!content) return '';
    try {
      return JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      return content;
    }
  }

  function extractFencedBlock(value: string, languages: string[]) {
    const pattern = /```([a-zA-Z0-9_-]*)\s*\n([\s\S]*?)```/g;
    let fallback = '';
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(value))) {
      const lang = match[1].toLowerCase();
      const body = match[2].trim();
      if (!fallback) fallback = body;
      if (languages.includes(lang)) return body;
    }
    return fallback;
  }

  function extractHtmlDocument(value: string) {
    const documentMatch = value.match(/(?:<!doctype\s+html[^>]*>\s*)?<html[\s\S]*<\/html>/i);
    if (documentMatch) return documentMatch[0].trim();
    const bodyMatch = value.match(/<body[\s\S]*<\/body>/i);
    if (bodyMatch) return bodyMatch[0].trim();
    const tagMatch = value.match(/<([a-z][a-z0-9-]*)(?:\s[^>]*)?>[\s\S]*<\/\1>/i);
    return tagMatch ? tagMatch[0].trim() : '';
  }

  function extractJsonCandidate(value: string) {
    const trimmed = value.trim();
    if (!trimmed) return '';
    const start = findFirstJsonBoundary(trimmed);
    if (start < 0) return '';
    const end = findLastJsonBoundary(trimmed);
    return end > start ? trimmed.slice(start, end + 1) : '';
  }

  function findFirstJsonBoundary(value: string) {
    const objectIndex = value.indexOf('{');
    const arrayIndex = value.indexOf('[');
    if (objectIndex < 0) return arrayIndex;
    if (arrayIndex < 0) return objectIndex;
    return Math.min(objectIndex, arrayIndex);
  }

  function findLastJsonBoundary(value: string) {
    return Math.max(value.lastIndexOf('}'), value.lastIndexOf(']'));
  }

  function buildPayload() {
    const workflow = isWorkflowMode.value ? workflowDefinitionPayload() : undefined;
    return {
      ...form,
      model_preferences: buildModelPreferences(),
      variables_schema: buildVariablesSchemaFromTemplateFromKeys(parsedVariablesSchema.value, savedInputVariableKeys.value),
      output_schema: parseJsonObject(outputSchemaText.value),
      trace_policy: { enabled: true },
      runtime_config: {
        ...(activeApp.value?.runtime_config || {}),
        icon: form.icon,
        system_prompt_source: systemPromptSource.value,
        system_prompt_asset_key: systemPromptSource.value === 'asset' ? selectedSystemPromptAssetKey.value : '',
        output_format: selectedOutputFormat.value,
        ...(workflow ? { workflow } : {}),
      },
    };
  }

  function buildCapabilityPayload() {
    const workflow = isWorkflowMode.value ? workflowDefinitionPayload() : undefined;
    const systemPromptAssetEnabled = canUsePromptAsset.value && systemPromptSource.value === 'asset';
    const runtimeConfig = {
      ...(activeCapability.value?.runtime_config || {}),
      icon: form.icon,
      system_prompt_source: systemPromptAssetEnabled ? 'asset' : 'inline',
      system_prompt_asset_key: systemPromptAssetEnabled ? selectedSystemPromptAssetKey.value : '',
      output_format: selectedOutputFormat.value,
      ...(workflow ? { workflow } : {}),
    };
    return {
      capability_key: form.app_key,
      name: form.name,
      description: form.description,
      scope: editingPlatformCapability.value ? 'platform' : 'tenant',
      binding_type: isWorkflowMode.value ? 'workflow_runtime' : 'prompt_runtime',
      binding_key: form.app_key,
      call_method: activeCapability.value?.call_method || 'aiService.execute',
      system_prompt: form.system_prompt,
      developer_prompt: form.developer_prompt,
      user_prompt_template: form.user_prompt_template,
      input_schema: buildVariablesSchemaFromTemplateFromKeys(parsedVariablesSchema.value, savedInputVariableKeys.value),
      output_schema: parseJsonObject(outputSchemaText.value),
      model_preferences: buildModelPreferences(),
      runtime_config: runtimeConfig,
      enabled: activeCapability.value?.enabled ?? true,
    };
  }

  function buildModelPreferences() {
    const modelKey = selectedModelKey.value.trim();
    return {
      [isPlatformCapabilityRoute.value ? 'route_key' : 'model']: modelKey,
      temperature: 0.2,
    };
  }

  function saveCapabilityPayload() {
    const payload = buildCapabilityPayload();
    return editingPlatformCapability.value
      ? updatePlatformAiCapability(form.app_key, payload)
      : updateAiCapability(form.app_key, payload);
  }

  function generatePromptHint() {
    message.info('后续会接入提示词生成能力');
  }

  async function copyText(value: string, label = '内容') {
    const text = String(value || '');
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      message.success(`${label}已复制`);
    } catch {
      message.error('复制失败，请手动复制');
    }
  }

  function revokeHtmlPreviewObjectUrl() {
    if (!htmlPreviewObjectUrl) return;
    URL.revokeObjectURL(htmlPreviewObjectUrl);
    htmlPreviewObjectUrl = '';
  }

  function openCurrentHtmlPreviewInNewTab() {
    const html = htmlPreviewSrcdoc.value;
    if (!html) {
      message.warning('暂无可预览的 HTML 内容');
      return;
    }
    revokeHtmlPreviewObjectUrl();
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    htmlPreviewObjectUrl = URL.createObjectURL(blob);
    const opened = window.open(htmlPreviewObjectUrl, '_blank', 'noopener,noreferrer');
    if (!opened) {
      message.warning('浏览器阻止了新标签页，请允许弹出窗口后重试');
    }
  }

  function togglePreviewFocusMode() {
    previewFocusMode.value = !previewFocusMode.value;
  }

  function toggleRuntimeVariablesCollapsed() {
    runtimeVariablesCollapsed.value = !runtimeVariablesCollapsed.value;
  }

  function togglePreviewWidth() {
    if (previewFocusMode.value) return;
    if (previewResizeDragged.value) {
      previewResizeDragged.value = false;
      return;
    }
    previewWidthPercent.value = previewWidthPercent.value > 52 ? 42 : 62;
  }

  function startPreviewResize(event: PointerEvent) {
    if (previewFocusMode.value) return;
    const target = event.currentTarget as HTMLElement;
    const container = workbenchRef.value;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const startX = event.clientX;
    previewResizeDragged.value = false;
    target.setPointerCapture?.(event.pointerId);

    const resize = (moveEvent: PointerEvent) => {
      const delta = Math.abs(moveEvent.clientX - startX);
      if (delta > 3) previewResizeDragged.value = true;
      const width = rect.right - moveEvent.clientX;
      const percent = (width / rect.width) * 100;
      previewWidthPercent.value = clampNumber(percent, 34, 68);
    };
    const stop = () => {
      target.releasePointerCapture?.(event.pointerId);
      window.removeEventListener('pointermove', resize);
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
    };
    window.addEventListener('pointermove', resize);
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
  }

  function clampNumber(value: number, min: number, max: number) {
    return Math.min(max, Math.max(min, value));
  }

  function asSchemaRecord(value: unknown): SchemaRecord | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as SchemaRecord) : null;
  }

  function extractTemplateVariableKeys(template: string): string[] {
    const keys = new Set<string>();
    for (const match of template.matchAll(TEMPLATE_VARIABLE_PATTERN)) {
      keys.add(match[1]);
    }
    return [...keys];
  }

  function collectSchemaEntries(schema?: SchemaRecord): {
    entries: Map<string, unknown>;
    requiredKeys: Set<string>;
  } {
    const entries = new Map<string, unknown>();
    const requiredKeys = new Set<string>();
    if (!schema) return { entries, requiredKeys };

    const required = Array.isArray(schema.required) ? schema.required : [];
    required.forEach((key) => {
      if (typeof key === 'string') requiredKeys.add(key);
    });

    const properties = asSchemaRecord(schema.properties);
    if (properties) {
      Object.entries(properties).forEach(([key, value]) => entries.set(key, value));
      return { entries, requiredKeys };
    }

    const variables = Array.isArray(schema.variables) ? schema.variables : [];
    variables.forEach((item) => {
      if (typeof item === 'string') {
        entries.set(item, {});
      } else {
        const record = asSchemaRecord(item);
        const key = record && typeof record.key === 'string' ? record.key : record && typeof record.name === 'string' ? record.name : '';
        if (key) entries.set(key, record);
      }
    });

    Object.entries(schema).forEach(([key, value]) => {
      if (!RESERVED_SCHEMA_KEYS.has(key) && !entries.has(key)) {
        entries.set(key, value);
      }
    });
    return { entries, requiredKeys };
  }

  function buildRuntimeVariableFields(schema: SchemaRecord | null, keys: string[]): RuntimeVariableField[] {
    const tokenKeys = new Set(keys);
    const { entries, requiredKeys } = collectSchemaEntries(schema || undefined);
    const activeKeys = [...new Set(keys)];

    return activeKeys.map((key) => {
      const startVariable = isWorkflowMode.value ? workflowStartVariableMap.value.get(key) : undefined;
      const raw = entries.get(key);
      const node = asSchemaRecord(raw);
      const rawLabel = typeof raw === 'string' ? raw : undefined;
      const label = String(startVariable?.label || node?.label || node?.title || node?.name || rawLabel || key);
      const description = String(startVariable?.description || node?.description || node?.help || '');
      const typeValue = String(startVariable?.type || node?.type || '').toLowerCase();
      const options = buildVariableOptions(node);
      const fieldType = variableTypeOverrides[key] || resolveRuntimeVariableType(typeValue);
      const optional = variableOptionalOverrides[key] ?? (startVariable ? !startVariable.required : node?.required === false);

      return {
        key,
        label: variableLabelOverrides[key] || label,
        description,
        type: fieldType,
        required: !optional && (tokenKeys.has(key) || requiredKeys.has(key) || node?.required === true || startVariable?.required === true),
        placeholder: String(node?.placeholder || node?.example || `请输入${variableLabelOverrides[key] || label}`),
        options,
      };
    });
  }

  function buildVariablesSchemaFromTemplate(schema: SchemaRecord | null, template: string): Record<string, unknown> {
    return buildVariablesSchemaFromTemplateFromKeys(schema, extractTemplateVariableKeys(template || ''));
  }

  function buildVariablesSchemaFromTemplateFromKeys(schema: SchemaRecord | null, keys: string[]): Record<string, unknown> {
    if (!keys.length) return {};
    const existingProperties = asSchemaRecord(schema?.properties);
    const requiredKeys = keys.filter((key) => {
      const startVariable = isWorkflowMode.value ? workflowStartVariableMap.value.get(key) : undefined;
      return variableOptionalOverrides[key] !== true && startVariable?.required !== false;
    });
    const properties = keys.reduce<Record<string, unknown>>((result, key) => {
      const startVariable = isWorkflowMode.value ? workflowStartVariableMap.value.get(key) : undefined;
      const existing = asSchemaRecord(existingProperties?.[key]) || {};
      const label = (variableLabelOverrides[key] || startVariable?.label || String(existing.label || existing.title || '')).trim();
      const description = (startVariable?.description || String(existing.description || '')).trim();
      result[key] = {
        ...existing,
        type: schemaTypeFromRuntimeType(variableTypeOverrides[key] || startVariable?.type || resolveRuntimeVariableType(String(existing.type || ''))),
        ...(label ? { label } : {}),
        ...(description ? { description } : {}),
        ...(variableOptionalOverrides[key] === true ? { required: false } : {}),
      };
      return result;
    }, {});
    return {
      type: 'object',
      required: requiredKeys,
      properties,
    };
  }

  function schemaTypeFromRuntimeType(type: RuntimeVariableType) {
    if (type === 'text') return 'string';
    return type;
  }

  function buildModelConfigOptions(modelRows: Recordable[], policyRows: Recordable[]) {
    const options: SelectOption[] = [];
    const seen = new Set<string>();
    const push = (value: string, label: string) => {
      if (!value || seen.has(value)) return;
      seen.add(value);
      options.push({ value, label });
    };
    policyRows
      .filter((item) => item.enabled !== false)
      .forEach((item) => {
        const routeKey = String(item.route_key || '').trim();
        push(routeKey, `路由：${item.display_name || routeKey} (${routeKey})`);
      });
    modelRows
      .filter((item) => item.enabled !== false)
      .forEach((item) => {
        const modelKey = String(item.model_key || '').trim();
        push(modelKey, `模型：${item.display_name || item.model_name || modelKey} (${modelKey})`);
      });
    return options;
  }

  function updateVariableType(key: string, type: RuntimeVariableType) {
    variableTypeOverrides[key] = type;
    refreshVariablesSchemaText();
    const currentValue = runtimeVariableValues[key];
    if (type === 'boolean') {
      runtimeVariableValues[key] = typeof currentValue === 'boolean' ? currentValue : false;
    } else if (type === 'number') {
      runtimeVariableValues[key] = typeof currentValue === 'number' ? currentValue : null;
    } else if (['image', 'audio', 'video', 'file'].includes(type)) {
      runtimeVariableValues[key] = isRuntimeMediaVariableValue(currentValue) && currentValue.type === type ? currentValue : null;
    } else if (isRuntimeMediaVariableValue(currentValue) || typeof currentValue === 'boolean' || typeof currentValue === 'number') {
      runtimeVariableValues[key] = null;
    }
  }

  function updateVariableLabel(key: string, value: string | null) {
    variableLabelOverrides[key] = String(value || '').trim();
    refreshVariablesSchemaText();
  }

  function updateVariableOptional(key: string, optional: boolean) {
    variableOptionalOverrides[key] = optional;
    refreshVariablesSchemaText();
  }

  function refreshVariablesSchemaText() {
    variablesSchemaText.value = stringifyJson(buildVariablesSchemaFromTemplateFromKeys(parsedVariablesSchema.value || {}, savedInputVariableKeys.value));
  }

  function syncVariablesSchemaFromTemplate() {
    syncRuntimeVariableValues();
    refreshVariablesSchemaText();
  }

  function resolveRuntimeVariableType(typeValue: string): RuntimeVariableType {
    if (typeValue === 'boolean') return 'boolean';
    if (typeValue === 'number' || typeValue === 'integer') return 'number';
    if (['image', 'file', 'audio', 'video'].includes(typeValue)) return typeValue as RuntimeVariableType;
    return 'text';
  }

  function buildVariableOptions(node: SchemaRecord | null): SelectOption[] | undefined {
    const enumValues = Array.isArray(node?.enum) ? node?.enum : Array.isArray(node?.options) ? node?.options : [];
    const options = enumValues
      .map((item) => {
        const record = asSchemaRecord(item);
        if (record) {
          const value = record.value;
          if (typeof value !== 'string' && typeof value !== 'number') return null;
          return { label: String(record.label || value), value };
        }
        if (typeof item !== 'string' && typeof item !== 'number') return null;
        return { label: String(item), value: item };
      })
      .filter(Boolean) as SelectOption[];
    return options.length ? options : undefined;
  }

  function syncRuntimeVariableValues() {
    const activeKeys = new Set(runtimeVariableFields.value.map((field) => field.key));
    Object.keys(runtimeVariableValues).forEach((key) => {
      if (!activeKeys.has(key)) delete runtimeVariableValues[key];
    });
    Object.keys(variableTypeOverrides).forEach((key) => {
      if (!activeKeys.has(key)) delete variableTypeOverrides[key];
    });
    Object.keys(variableLabelOverrides).forEach((key) => {
      if (!activeKeys.has(key)) delete variableLabelOverrides[key];
    });
    Object.keys(variableOptionalOverrides).forEach((key) => {
      if (!activeKeys.has(key)) delete variableOptionalOverrides[key];
    });
    runtimeVariableFields.value.forEach((field) => {
      if (!variableTypeOverrides[field.key]) {
        variableTypeOverrides[field.key] = field.type;
      }
      if (typeof variableLabelOverrides[field.key] === 'undefined') {
        variableLabelOverrides[field.key] = field.label === field.key ? '' : field.label;
      }
      const startVariable = isWorkflowMode.value ? workflowStartVariableMap.value.get(field.key) : undefined;
      if (startVariable) {
        variableTypeOverrides[field.key] = startVariable.type;
        variableLabelOverrides[field.key] = startVariable.label === field.key ? '' : startVariable.label;
        variableOptionalOverrides[field.key] = !startVariable.required;
      } else if (typeof variableOptionalOverrides[field.key] === 'undefined') {
        variableOptionalOverrides[field.key] = !field.required;
      }
      if (typeof runtimeVariableValues[field.key] === 'undefined') {
        runtimeVariableValues[field.key] = field.type === 'boolean' ? false : null;
      }
    });
  }

  function buildRuntimeVariables() {
    const variables: Record<string, unknown> = {};
    const fields = isWorkflowMode.value ? workflowInputVariableFields.value : runtimeVariableFields.value;
    fields.forEach((field) => {
      const value = runtimeVariableValues[field.key];
      if (value === null || typeof value === 'undefined' || value === '') return;
      assignVariableValue(variables, field.key, value);
    });
    return variables;
  }

  function sampleRuntimeVariables() {
    const variables: Record<string, unknown> = {};
    runtimeVariableFields.value.forEach((field) => {
      const value = field.type === 'number' ? 123 : field.type === 'boolean' ? true : isMediaVariableField(field) ? `<${field.type}>` : field.label;
      assignVariableValue(variables, field.key, value);
    });
    return variables;
  }

  function assignVariableValue(target: Record<string, unknown>, key: string, value: unknown) {
    const parts = key.split('.').filter(Boolean);
    let current = target;
    parts.forEach((part, index) => {
      if (index === parts.length - 1) {
        current[part] = value;
        return;
      }
      const next = asSchemaRecord(current[part]) || {};
      current[part] = next;
      current = next;
    });
  }

  function findUnfilledRequiredVariables(fields: RuntimeVariableField[] = runtimeVariableFields.value) {
    return fields
      .filter((field) => field.required)
      .filter((field) => {
        const value = runtimeVariableValues[field.key];
        return value === null || typeof value === 'undefined' || (typeof value === 'string' && !value.trim());
      })
      .map((field) => field.label);
  }

  function isMediaVariableField(field: RuntimeVariableField) {
    return ['image', 'file', 'audio', 'video'].includes(field.type);
  }

  function mediaVariableValue(key: string) {
    const value = runtimeVariableValues[key];
    return isRuntimeMediaVariableValue(value) ? value : null;
  }

  function isRuntimeMediaVariableValue(value: unknown): value is RuntimeMediaVariableValue {
    return !!value && typeof value === 'object' && ['image', 'file', 'audio', 'video'].includes(String((value as any).type || ''));
  }

  function mediaVariableAccept(field: RuntimeVariableField) {
    if (field.type === 'image') return 'image/*';
    if (field.type === 'audio') return 'audio/*';
    if (field.type === 'video') return 'video/*';
    return '';
  }

  function mediaVariableUploadTitle(field: RuntimeVariableField) {
    const labels: Record<string, string> = {
      image: '上传图片',
      audio: '上传音频',
      video: '上传视频',
      file: '上传文件',
    };
    return labels[field.type] || '上传文件';
  }

  function mediaVariableUploadHint(field: RuntimeVariableField) {
    if (field.type === 'image') return '支持图片理解模型分析图片内容';
    if (field.type === 'audio') return '支持音频理解模型分析或转写音频';
    if (field.type === 'video') return '支持视频理解模型分析视频内容';
    return '文本类文件会作为内容传入，其他文件会作为附件传入';
  }

  function maxMediaVariableBytes(field: RuntimeVariableField) {
    if (field.type === 'image') return 8 * 1024 * 1024;
    if (field.type === 'audio') return 20 * 1024 * 1024;
    if (field.type === 'video') return 32 * 1024 * 1024;
    return 10 * 1024 * 1024;
  }

  function startRunStopwatch() {
    stopRunStopwatch();
    runningElapsedMs.value = 0;
    lastRunElapsedMs.value = 0;
    const startedAt = Date.now();
    runStopwatchTimer = window.setInterval(() => {
      runningElapsedMs.value = Date.now() - startedAt;
    }, 100);
  }

  function finishRunStopwatch() {
    lastRunElapsedMs.value = runningElapsedMs.value;
    stopRunStopwatch();
  }

  function stopRunStopwatch() {
    if (runStopwatchTimer === null) return;
    window.clearInterval(runStopwatchTimer);
    runStopwatchTimer = null;
  }

  function fallbackMimeType(field: RuntimeVariableField) {
    if (field.type === 'image') return 'image/png';
    if (field.type === 'audio') return 'audio/mpeg';
    if (field.type === 'video') return 'video/mp4';
    return 'application/octet-stream';
  }

  function readTextPreviewIfSupported(file: File) {
    const textLike =
      file.type.startsWith('text/') || /\.(txt|md|json|csv|xml|yaml|yml|log)$/i.test(file.name || '');
    if (!textLike || file.size > 512 * 1024) return Promise.resolve('');
    return new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || '').slice(0, 20000));
      reader.onerror = () => resolve('');
      reader.readAsText(file);
    });
  }

  function formatBytes(value: number) {
    if (!value) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
    return `${(value / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`;
  }

  function formatElapsedSeconds(elapsedMs: unknown) {
    const seconds = Number(elapsedMs || 0) / 1000;
    if (!Number.isFinite(seconds) || seconds <= 0) return '0.00';
    return seconds < 10 ? seconds.toFixed(2) : seconds.toFixed(1);
  }

  function formatDateTime(value: unknown) {
    const text = String(value || '').trim();
    if (!text) return '-';
    const date = new Date(text.includes('T') ? text : text.replace(' ', 'T'));
    if (Number.isNaN(date.getTime())) return text;
    const pad = (item: number) => String(item).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  }

  function formatStopwatchSeconds(elapsedMs: unknown) {
    const seconds = Number(elapsedMs || 0) / 1000;
    if (!Number.isFinite(seconds) || seconds <= 0) return '0.0';
    return seconds < 10 ? seconds.toFixed(1) : seconds.toFixed(0);
  }

  function runModeLabel(value: string) {
    if (value === 'studio_draft') return '调试运行';
    if (value === 'application_api') return 'API 调用';
    if (value === 'ai_capability') return '内部能力调用';
    return value || '未知来源';
  }

  function tokenUsageText(usage: Record<string, unknown>) {
    const total = usage?.total_tokens ?? usage?.total ?? '';
    const prompt = usage?.prompt_tokens ?? '';
    const completion = usage?.completion_tokens ?? '';
    if (total || prompt || completion) {
      return `total ${total || '-'} / prompt ${prompt || '-'} / completion ${completion || '-'}`;
    }
    return '-';
  }

  function renderMarkdown(value: string) {
    return markdownRenderer.render(value || '');
  }

  function parseJsonObject(value: string): Record<string, unknown> {
    try {
      const payload = JSON.parse(value || '{}');
      return payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {};
    } catch {
      message.error('JSON 格式不正确');
      throw new Error('Invalid JSON');
    }
  }

  function parseJsonObjectSilently(value: string): Record<string, unknown> | null {
    try {
      const payload = JSON.parse(value || '{}');
      return payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : null;
    } catch {
      return null;
    }
  }

  function parseJsonArraySilently(value: string): unknown[] | null {
    try {
      const payload = JSON.parse(value || '[]');
      return Array.isArray(payload) ? payload : null;
    } catch {
      return null;
    }
  }

  function stringifyJson(value: unknown) {
    return JSON.stringify(value || {}, null, 2);
  }

  watch(selectedSystemPromptAssetKey, (key) => {
    if (key) void loadPublishedPromptDetail(key);
  });

  onMounted(reload);
</script>

<style lang="less" scoped>
  .studio-workbench {
    display: grid;
    grid-template-columns: minmax(360px, 1fr) 10px minmax(420px, var(--studio-preview-width, 42%));
    gap: 10px;
    align-items: start;
    min-width: 0;
  }

  .studio-workbench.is-preview-focus {
    grid-template-columns: minmax(0, 1fr);
  }

  .studio-workbench.is-preview-focus .studio-builder,
  .studio-workbench.is-preview-focus .studio-resizer {
    display: none;
  }

  .studio-workbench.is-preview-focus .studio-preview {
    position: static;
  }

  .studio-workbench.is-preview-focus .chat-preview__bubble {
    max-height: min(760px, calc(100vh - 320px));
  }

  .studio-workbench.is-preview-focus .html-answer-frame {
    min-height: 620px;
  }

  .platform-preview-modal {
    max-width: calc(100vw - 32px);

    &__footer {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }
  }

  .studio-workspace-nav {
    display: flex;
    gap: 4px;
    align-items: center;
    min-width: 0;
    margin-bottom: 12px;
    padding: 4px;
    overflow-x: auto;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 74%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: var(--app-card-radius);
  }

  .studio-workspace-nav__item {
    display: grid;
    gap: 1px;
    min-width: 92px;
    padding: 7px 12px;
    color: var(--app-text-color-2);
    text-align: left;
    white-space: nowrap;
    cursor: pointer;
    background: transparent;
    border: 0;
    border-radius: 7px;
  }

  .studio-workspace-nav__item span {
    font-size: 13px;
    font-weight: 650;
    line-height: 1.35;
  }

  .studio-workspace-nav__item small {
    color: var(--app-text-color-3);
    font-size: 11px;
    line-height: 1.35;
  }

  .studio-workspace-nav__item:hover,
  .studio-workspace-nav__item.is-active {
    color: var(--app-primary-color);
    background: var(--app-surface-bg);
    box-shadow: 0 1px 3px color-mix(in srgb, #000 8%, transparent);
  }

  .studio-workspace-panel {
    min-width: 0;
    padding: 16px;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: var(--app-card-radius);
  }

  .workflow-fullscreen {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    min-width: 0;
    height: calc(100vh - 250px);
    min-height: 620px;
  }

  .workflow-canvas-shell {
    min-width: 0;
    min-height: 0;
  }

  .workflow-canvas-shell {
    --workflow-panel-gap: 14px;
    --workflow-run-panel-width: 440px;
    position: relative;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: var(--app-card-radius);
  }

  .workflow-canvas-toolbar {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
    min-width: 0;
    padding: 10px 12px;
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
  }

  .workflow-canvas-toolbar div {
    display: grid;
    gap: 1px;
    min-width: 0;
  }

  .workflow-canvas-toolbar span {
    color: var(--app-text-color-1);
    font-size: 14px;
    font-weight: 650;
    line-height: 1.35;
  }

  .workflow-canvas-toolbar small {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.35;
  }

  .workflow-canvas-panel {
    position: relative;
    min-height: 0;
    padding: 0;
    overflow: hidden;
    background:
      radial-gradient(circle, color-mix(in srgb, var(--app-border-color, #d9e1ec) 46%, transparent) 1px, transparent 1px) 0 0 / 18px 18px,
      var(--app-surface-bg);
  }

  .workflow-canvas {
    width: 100%;
    height: 100%;
  }

  .workflow-canvas-menu {
    position: absolute;
    z-index: 25;
    display: grid;
    gap: 4px;
    width: 220px;
    padding: 8px;
    color: var(--app-text-color-1);
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 86%, transparent);
    border-radius: 8px;
    box-shadow: 0 18px 42px color-mix(in srgb, #0f172a 18%, transparent);
  }

  .workflow-canvas-menu__title {
    padding: 6px 8px 7px;
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.2;
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 64%, transparent);
  }

  .workflow-canvas-menu button {
    display: grid;
    gap: 3px;
    width: 100%;
    padding: 9px 10px;
    color: var(--app-text-color-2);
    text-align: left;
    cursor: pointer;
    background: transparent;
    border: 0;
    border-radius: 6px;
  }

  .workflow-canvas-menu button:hover,
  .workflow-canvas-menu button:focus-visible {
    color: var(--app-primary-color);
    background: color-mix(in srgb, var(--app-primary-color) 9%, transparent);
    outline: none;
  }

  .workflow-canvas-menu button strong {
    font-size: 14px;
    line-height: 1.3;
  }

  .workflow-canvas-menu button span {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.35;
  }

  :deep(.vue-flow__node) {
    color: var(--app-text-color-1);
    background: transparent;
    border: 0;
    box-shadow: none;
  }

  :deep(.vue-flow__node.selected) {
    box-shadow: none;
  }

  .workflow-node-card {
    position: relative;
    display: grid;
    gap: 10px;
    width: 245px;
    min-height: 120px;
    padding: 14px;
    color: var(--app-text-color-1);
    background: color-mix(in srgb, var(--app-surface-bg) 94%, var(--app-primary-soft-bg, #eef4ff));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 86%, transparent);
    border-radius: 14px;
    box-shadow: 0 14px 30px color-mix(in srgb, #0f172a 10%, transparent);
  }

  .workflow-node-card.is-selected {
    border-color: var(--app-primary-color);
    box-shadow:
      0 0 0 2px color-mix(in srgb, var(--app-primary-color) 18%, transparent),
      0 18px 36px color-mix(in srgb, var(--app-primary-color) 16%, transparent);
  }

  .workflow-node-card.is-executed {
    border-color: color-mix(in srgb, var(--app-success-color, #18a058) 72%, var(--app-border-color, #d9e1ec));
    box-shadow:
      0 0 0 2px color-mix(in srgb, var(--app-success-color, #18a058) 14%, transparent),
      0 18px 36px color-mix(in srgb, var(--app-success-color, #18a058) 12%, transparent);
  }

  .workflow-node-card.is-failed {
    border-color: var(--app-error-color, #d03050);
    box-shadow:
      0 0 0 2px color-mix(in srgb, var(--app-error-color, #d03050) 16%, transparent),
      0 18px 36px color-mix(in srgb, var(--app-error-color, #d03050) 12%, transparent);
  }

  .workflow-node-card--condition {
    width: 286px;
  }

  .workflow-node-card__head {
    display: flex;
    gap: 10px;
    align-items: center;
    min-width: 0;
  }

  .workflow-node-card__head strong {
    min-width: 0;
    overflow: hidden;
    font-size: 15px;
    font-weight: 750;
    line-height: 1.3;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .workflow-node-card__icon {
    display: grid;
    flex: 0 0 auto;
    width: 34px;
    height: 34px;
    place-items: center;
    color: #fff;
    font-size: 12px;
    font-weight: 800;
    background: color-mix(in srgb, var(--app-primary-color) 82%, #10b981);
    border-radius: 10px;
  }

  .workflow-node-card__meta,
  .workflow-node-branch {
    min-width: 0;
    padding: 7px 10px;
    overflow: hidden;
    color: var(--app-text-color-2);
    font-size: 12px;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 78%, var(--app-surface-bg));
    border-radius: 8px;
  }

  .workflow-node-branch {
    display: grid;
    gap: 2px;
    padding: 8px 10px;
    white-space: normal;
  }

  .workflow-node-branch strong {
    font-size: 12px;
    line-height: 1.2;
  }

  .workflow-node-branch span {
    display: -webkit-box;
    overflow: hidden;
    color: var(--app-text-color-3);
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .workflow-node-card p {
    display: -webkit-box;
    margin: 0;
    overflow: hidden;
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 500;
    line-height: 1.45;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
  }

  .workflow-node-card--sql .workflow-node-card__sql-preview {
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
    font-size: 11.5px;
    font-weight: 500;
    line-height: 1.45;
    word-break: break-word;
  }

  .workflow-node-card--sql .workflow-node-card__meta {
    padding: 0;
    background: transparent;
    border: 0;
  }

  .workflow-node-card__actions {
    position: absolute;
    top: -38px;
    right: 4px;
    z-index: 5;
    display: flex;
    gap: 2px;
    align-items: center;
    padding: 4px;
    pointer-events: auto;
    opacity: 0;
    background: color-mix(in srgb, var(--app-surface-bg) 92%, transparent);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 12px;
    box-shadow: 0 10px 24px color-mix(in srgb, #0f172a 14%, transparent);
    transition: opacity 0.15s ease, transform 0.15s ease;
    transform: translateY(4px);
  }

  .workflow-node-card:hover .workflow-node-card__actions,
  .workflow-node-card.is-selected .workflow-node-card__actions {
    opacity: 1;
    transform: translateY(0);
  }

  .workflow-node-card__actions button,
  .workflow-node-menu button {
    color: var(--app-text-color-2);
    cursor: pointer;
    background: transparent;
    border: 0;
  }

  .workflow-node-card__actions button {
    display: grid;
    width: 28px;
    height: 26px;
    place-items: center;
    font-size: 13px;
    border-radius: 8px;
  }

  .workflow-node-card__actions button:hover,
  .workflow-node-card__actions button:focus-visible {
    color: var(--app-primary-color);
    background: var(--app-primary-soft-bg, #eef4ff);
    outline: none;
  }

  .workflow-node-menu {
    position: absolute;
    top: 4px;
    right: 10px;
    z-index: 20;
    display: grid;
    min-width: 172px;
    padding: 7px;
    background: color-mix(in srgb, var(--app-surface-bg) 94%, transparent);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 78%, transparent);
    border-radius: 12px;
    box-shadow: 0 20px 46px color-mix(in srgb, #0f172a 22%, transparent);
    backdrop-filter: blur(10px);
  }

  .workflow-node-menu button {
    width: 100%;
    padding: 9px 10px;
    font-size: 13px;
    line-height: 1.25;
    text-align: left;
    border-radius: 8px;
  }

  .workflow-node-menu button:hover,
  .workflow-node-menu button:focus-visible {
    color: var(--app-text-color-1);
    background: var(--app-surface-muted-bg, #f5f7fb);
    outline: none;
  }

  .workflow-node-menu button.is-danger {
    color: var(--app-error-color, #d03050);
  }

  .workflow-node-menu button:disabled {
    color: var(--app-text-color-4, #c0c4cc);
    cursor: not-allowed;
  }

  :deep(.workflow-node-card .vue-flow__handle) {
    width: 10px;
    height: 10px;
    background: var(--app-primary-color);
    border: 2px solid var(--app-surface-bg);
    box-shadow: 0 2px 8px color-mix(in srgb, var(--app-primary-color) 28%, transparent);
  }

  :deep(.workflow-node-card__branch-handle--true) {
    top: 42%;
  }

  :deep(.workflow-node-card__branch-handle--false) {
    top: 62%;
  }

  :deep(.vue-flow__controls) {
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 8px;
    box-shadow: 0 8px 18px color-mix(in srgb, #0f172a 10%, transparent);
  }

  :deep(.vue-flow__edge-path) {
    stroke: color-mix(in srgb, var(--app-primary-color) 72%, #64748b);
    stroke-width: 2;
  }

  :deep(.vue-flow__edge.selected .vue-flow__edge-path) {
    stroke: var(--app-primary-color);
    stroke-width: 3;
  }

  :deep(.vue-flow__edge.is-workflow-executed-edge .vue-flow__edge-path) {
    stroke: var(--app-success-color, #18a058);
    stroke-width: 3;
    filter: drop-shadow(0 0 5px color-mix(in srgb, var(--app-success-color, #18a058) 32%, transparent));
  }

  .workflow-run-panel {
    position: absolute;
    top: 60px;
    right: var(--workflow-panel-gap);
    z-index: 9;
    display: grid;
    align-content: start;
    gap: 12px;
    width: min(var(--workflow-run-panel-width), calc(100% - var(--workflow-panel-gap) * 2));
    max-height: calc(100% - 76px);
    padding: 14px;
    overflow: auto;
    background: color-mix(in srgb, var(--app-surface-bg) 96%, transparent);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: var(--app-card-radius);
    box-shadow: 0 24px 60px color-mix(in srgb, #0f172a 22%, transparent);
    backdrop-filter: blur(12px);
  }

  .workflow-run-panel__head {
    position: sticky;
    top: -14px;
    z-index: 2;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
    padding-bottom: 12px;
    background: color-mix(in srgb, var(--app-surface-bg) 96%, transparent);
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 62%, transparent);
    backdrop-filter: blur(12px);
  }

  .workflow-run-panel__head h3 {
    margin: 0;
    color: var(--app-text-color-1);
    font-size: 17px;
    font-weight: 750;
    line-height: 1.35;
  }

  .workflow-run-panel__head span {
    display: block;
    margin-top: 3px;
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.45;
  }

  .workflow-run-panel__actions {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .workflow-run-panel__actions .workflow-run-panel__close {
    flex: 0 0 auto;
    width: 28px;
    height: 28px;
    color: var(--app-text-color-3);
    font-size: 19px;
    line-height: 1;
    cursor: pointer;
    background: transparent;
    border: 0;
    border-radius: 6px;
  }

  .workflow-run-panel__actions .workflow-run-panel__close:hover,
  .workflow-run-panel__actions .workflow-run-panel__close:focus-visible {
    color: var(--app-text-color-1);
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 82%, var(--app-surface-bg));
    outline: none;
  }

  .workflow-run-panel__section,
  .workflow-run-panel__answer {
    display: grid;
    gap: 10px;
    min-width: 0;
    padding: 12px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 44%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 68%, transparent);
    border-radius: 8px;
  }

  .workflow-run-panel__section--logs {
    background: color-mix(in srgb, var(--app-success-color, #18a058) 7%, var(--app-surface-bg));
    border-color: color-mix(in srgb, var(--app-success-color, #18a058) 22%, var(--app-border-color, #d9e1ec));
  }

  .workflow-run-panel__section-head {
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
    min-width: 0;
  }

  .workflow-run-panel__section-head strong,
  .workflow-run-panel__answer strong {
    color: var(--app-text-color-1);
    font-size: 14px;
    font-weight: 700;
    line-height: 1.35;
  }

  .workflow-run-panel__section-head span {
    color: var(--app-text-color-3);
    font-size: 12px;
    white-space: nowrap;
  }

  .workflow-run-inputs {
    display: grid;
    gap: 10px;
  }

  .workflow-run-input {
    display: grid;
    gap: 6px;
    min-width: 0;
  }

  .workflow-run-input label {
    display: flex;
    gap: 4px;
    align-items: center;
    min-width: 0;
    color: var(--app-text-color-2);
    font-size: 12px;
    font-weight: 650;
    line-height: 1.35;
  }

  .workflow-run-input label span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .workflow-run-input label em {
    color: var(--app-error-color, #d03050);
    font-style: normal;
  }

  .workflow-run-input small {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.45;
  }

  .workflow-trace-list {
    display: grid;
    gap: 8px;
  }

  .workflow-trace-item {
    min-width: 0;
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .workflow-trace-item.is-success {
    border-color: color-mix(in srgb, var(--app-success-color, #18a058) 28%, var(--app-border-color, #d9e1ec));
  }

  .workflow-trace-item.is-failed {
    border-color: color-mix(in srgb, var(--app-error-color, #d03050) 52%, var(--app-border-color, #d9e1ec));
  }

  .workflow-trace-item.is-running {
    border-color: color-mix(in srgb, var(--app-primary-color) 34%, var(--app-border-color, #d9e1ec));
  }

  .workflow-trace-item summary {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr) auto auto 10px;
    gap: 8px;
    align-items: center;
    padding: 9px 10px;
    cursor: pointer;
    list-style: none;
  }

  .workflow-trace-item summary::-webkit-details-marker {
    display: none;
  }

  .workflow-trace-item__icon {
    display: grid;
    width: 28px;
    height: 28px;
    place-items: center;
    color: #fff;
    font-size: 10px;
    font-weight: 800;
    background: color-mix(in srgb, var(--app-primary-color) 82%, #10b981);
    border-radius: 8px;
  }

  .workflow-trace-item__title {
    min-width: 0;
    overflow: hidden;
    color: var(--app-text-color-1);
    font-size: 13px;
    font-weight: 700;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .workflow-trace-item__branch,
  .workflow-trace-item__elapsed {
    color: var(--app-text-color-3);
    font-size: 12px;
    white-space: nowrap;
  }

  .workflow-trace-item__status {
    width: 9px;
    height: 9px;
    background: var(--app-success-color, #18a058);
    border-radius: 999px;
  }

  .workflow-trace-item.is-failed .workflow-trace-item__status {
    background: var(--app-error-color, #d03050);
  }

  .workflow-trace-item.is-running .workflow-trace-item__status {
    background: var(--app-primary-color);
  }

  .workflow-trace-item__body {
    display: grid;
    gap: 8px;
    padding: 0 10px 10px 48px;
  }

  .workflow-trace-item__body strong {
    display: block;
    margin-bottom: 4px;
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  .workflow-trace-item__body pre {
    max-height: 180px;
    margin: 0;
    padding: 9px;
    overflow: auto;
    color: var(--app-text-color-1);
    font-size: 12px;
    line-height: 1.55;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 76%, var(--app-surface-bg));
    border-radius: 7px;
  }

  .workflow-trace-item__error {
    padding: 8px 9px;
    color: var(--app-error-color, #d03050);
    font-size: 12px;
    line-height: 1.45;
    background: color-mix(in srgb, var(--app-error-color, #d03050) 8%, var(--app-surface-bg));
    border-radius: 7px;
  }

  .workflow-trace-error {
    padding: 10px 12px;
    color: var(--app-error-color, #d03050);
    font-size: 12px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
    background: color-mix(in srgb, var(--app-error-color, #d03050) 8%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-error-color, #d03050) 22%, transparent);
    border-radius: 8px;
  }

  .workflow-trace-placeholder {
    display: flex;
    gap: 8px;
    align-items: center;
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .workflow-run-panel__answer {
    background: var(--app-surface-bg);
  }

  .workflow-run-panel__answer :deep(.markdown-answer),
  .workflow-run-panel__answer div,
  .workflow-run-panel__answer pre {
    min-width: 0;
    max-height: 240px;
    margin: 0;
    overflow: auto;
    overflow-wrap: anywhere;
    color: var(--app-text-color-1);
    font-size: 13px;
    line-height: 1.65;
  }

  .workflow-floating-panel {
    position: absolute;
    top: 60px;
    right: var(--workflow-panel-gap);
    z-index: 8;
    display: grid;
    align-content: start;
    gap: 12px;
    width: min(520px, calc(100% - 28px));
    max-height: calc(100% - 76px);
    padding: 14px;
    overflow: auto;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: var(--app-card-radius);
    box-shadow: 0 18px 42px color-mix(in srgb, #0f172a 18%, transparent);
  }

  .workflow-floating-panel.is-run-panel-open {
    right: calc(var(--workflow-run-panel-width) + var(--workflow-panel-gap) * 2);
    width: min(520px, calc(100% - var(--workflow-run-panel-width) - var(--workflow-panel-gap) * 3));
  }

  .workflow-floating-panel header {
    position: sticky;
    top: -14px;
    z-index: 1;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
    padding: 0 0 10px;
    background: var(--app-surface-bg);
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 60%, transparent);
  }

  .workflow-floating-panel header div {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .workflow-floating-panel header button {
    flex: 0 0 auto;
    width: 28px;
    height: 28px;
    color: var(--app-text-color-3);
    font-size: 20px;
    line-height: 1;
    cursor: pointer;
    background: transparent;
    border: 0;
    border-radius: 6px;
  }

  .workflow-floating-panel header button:hover,
  .workflow-floating-panel header button:focus-visible {
    color: var(--app-text-color-1);
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 82%, var(--app-surface-bg));
    outline: none;
  }

  .workflow-floating-panel h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 650;
    line-height: 1.35;
  }

  .workflow-floating-panel header span {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.45;
  }

  .workflow-sql-editor {
    overflow: hidden;
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: 8px;
  }

  .workflow-start-variables {
    display: grid;
    gap: 10px;
  }

  .workflow-start-variables__head {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    justify-content: space-between;
  }

  .workflow-start-variables__head div {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .workflow-start-variables__head h4 {
    margin: 0;
    color: var(--app-text-color-1);
    font-size: 14px;
    font-weight: 650;
    line-height: 1.4;
  }

  .workflow-start-variables__head span,
  .workflow-start-variables__empty {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.55;
  }

  .workflow-start-variable-list {
    display: grid;
    gap: 8px;
  }

  .workflow-start-variable-row {
    display: grid;
    grid-template-columns: minmax(92px, 1fr) minmax(92px, 1fr) minmax(88px, 0.8fr) 44px;
    gap: 8px;
    align-items: center;
    padding: 10px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 54%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 64%, transparent);
    border-radius: 7px;
  }

  .workflow-start-variable-row__description {
    grid-column: 1 / 4;
  }

  .workflow-prompt-asset-control {
    display: grid;
    gap: 10px;
    width: 100%;
    min-width: 0;
  }

  .workflow-prompt-asset-control :deep(.n-radio-group),
  .workflow-prompt-asset-control :deep(.n-base-selection),
  .workflow-prompt-asset-control :deep(.n-input) {
    min-width: 0;
  }

  .workspace-panel__head {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  .workspace-panel__head h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 650;
    line-height: 1.35;
  }

  .workspace-panel__head span {
    color: var(--app-text-color-3);
    font-size: 13px;
    line-height: 1.5;
  }

  .api-doc-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
    gap: 18px;
    align-items: start;
    min-width: 0;
  }

  .api-doc-main,
  .api-doc-aside {
    display: grid;
    gap: 14px;
    min-width: 0;
  }

  .api-doc-hero,
  .api-doc-section,
  .api-info-panel {
    min-width: 0;
    padding: 14px;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .api-doc-hero {
    display: grid;
    gap: 10px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 52%, var(--app-surface-bg));
  }

  .api-doc-hero p {
    margin: 0;
    color: var(--app-text-color-3);
    font-size: 13px;
    line-height: 1.6;
  }

  .api-endpoint-line {
    display: flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
  }

  .api-endpoint-line code {
    flex: 1;
    min-width: 0;
    padding: 8px 10px;
    overflow: hidden;
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 6px;
  }

  .api-method {
    padding: 5px 9px;
    color: var(--app-success-color, #18a058);
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
    background: color-mix(in srgb, var(--app-success-color, #18a058) 10%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-success-color, #18a058) 28%, transparent);
    border-radius: 5px;
  }

  .api-doc-section h4,
  .api-info-panel h4 {
    margin: 0 0 10px;
    color: var(--app-text-color-1);
    font-size: 14px;
    font-weight: 650;
    line-height: 1.4;
  }

  .api-doc-section__head {
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .api-doc-section__head h4 {
    margin: 0;
  }

  .api-field-table {
    display: grid;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 7px;
  }

  .api-field-row {
    display: grid;
    grid-template-columns: minmax(128px, 0.9fr) minmax(92px, 0.55fr) minmax(62px, 0.36fr) minmax(220px, 1.6fr);
    gap: 12px;
    align-items: center;
    min-width: 0;
    padding: 10px 12px;
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 62%, transparent);
  }

  .api-field-table--compact .api-field-row {
    grid-template-columns: 72px minmax(150px, 0.8fr) minmax(260px, 1.3fr);
  }

  .api-field-row:first-child {
    border-top: 0;
  }

  .api-field-row--head {
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 650;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 72%, var(--app-surface-bg));
  }

  .api-field-row span,
  .api-field-row code {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: 13px;
    line-height: 1.45;
  }

  .api-field-row code {
    color: var(--app-text-color-1);
    font-weight: 650;
  }

  .api-code-block {
    max-height: 360px;
    margin: 0;
    padding: 12px;
    overflow: auto;
    color: var(--app-text-color-1);
    font-size: 13px;
    line-height: 1.65;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 64%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 64%, transparent);
    border-radius: 7px;
  }

  .api-code-block--curl {
    max-height: 260px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .api-info-panel dl {
    display: grid;
    grid-template-columns: 86px minmax(0, 1fr);
    gap: 8px 10px;
    margin: 0;
    font-size: 13px;
    line-height: 1.5;
  }

  .api-info-panel dt {
    color: var(--app-text-color-3);
  }

  .api-info-panel dd {
    min-width: 0;
    margin: 0;
    overflow-wrap: anywhere;
  }

  .api-note-list {
    display: grid;
    gap: 8px;
    margin: 0;
    padding-left: 18px;
    color: var(--app-text-color-2);
    font-size: 13px;
    line-height: 1.6;
  }

  .app-settings-layout {
    display: grid;
    grid-template-columns: minmax(0, 640px) minmax(260px, 360px);
    gap: 18px;
    align-items: start;
    min-width: 0;
  }

  .app-settings-card,
  .app-settings-preview {
    min-width: 0;
    padding: 16px;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .app-settings-card__head {
    margin-bottom: 14px;
  }

  .app-settings-card__head h4,
  .app-settings-preview h4 {
    margin: 0;
    color: var(--app-text-color-1);
    font-size: 15px;
    font-weight: 650;
    line-height: 1.4;
  }

  .app-settings-card__head span {
    display: block;
    margin-top: 4px;
    color: var(--app-text-color-3);
    font-size: 13px;
    line-height: 1.5;
  }

  .app-settings-form {
    max-width: 560px;
  }

  .app-settings-preview {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 48%, var(--app-surface-bg));
  }

  .app-settings-preview__icon {
    display: grid;
    flex: 0 0 auto;
    place-items: center;
    width: 42px;
    height: 42px;
    color: var(--app-primary-color);
    font-size: 16px;
    font-weight: 700;
    background: color-mix(in srgb, var(--app-primary-color) 10%, var(--app-surface-bg));
    border-radius: 8px;
  }

  .app-settings-preview p {
    margin: 8px 0;
    color: var(--app-text-color-2);
    font-size: 13px;
    line-height: 1.6;
  }

  .app-settings-preview small {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }

  .run-log-layout {
    display: grid;
    grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
    gap: 14px;
    align-items: start;
    min-width: 0;
  }

  .run-log-list {
    display: grid;
    align-content: start;
    gap: 8px;
    min-width: 0;
  }

  .run-log-item {
    display: grid;
    gap: 6px;
    width: 100%;
    padding: 10px 12px;
    color: var(--app-text-color-2);
    text-align: left;
    cursor: pointer;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 46%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .run-log-item:hover,
  .run-log-item.is-active {
    background: var(--app-surface-bg);
    border-color: color-mix(in srgb, var(--app-primary-color) 54%, var(--app-border-color, #d9e1ec));
  }

  .run-log-item__top,
  .run-log-item__meta {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
    min-width: 0;
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .run-log-item strong {
    overflow: hidden;
    color: var(--app-text-color-1);
    font-size: 14px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .run-log-detail {
    display: grid;
    gap: 14px;
    align-self: start;
    align-content: start;
    min-width: 0;
    padding: 14px;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .run-log-detail__summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    align-items: start;
  }

  .run-log-detail__summary > div {
    display: grid;
    align-content: start;
    gap: 3px;
    min-width: 0;
    min-height: 72px;
    padding: 10px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 64%, var(--app-surface-bg));
    border-radius: 7px;
  }

  .run-log-detail__summary span,
  .run-log-detail h4 {
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .run-log-detail__summary strong {
    overflow: hidden;
    color: var(--app-text-color-1);
    font-size: 14px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .run-log-detail h4 {
    margin: 0 0 8px;
    font-weight: 650;
  }

  .run-log-json-viewer {
    max-height: 220px;
    margin: 0;
    padding: 10px 12px;
    overflow: auto;
    color: var(--app-text-color-2);
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 62%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 62%, transparent);
    border-radius: 7px;
  }

  .run-log-error {
    padding: 9px 10px;
    color: var(--app-error-color, #d03050);
    background: color-mix(in srgb, var(--app-error-color, #d03050) 8%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-error-color, #d03050) 22%, transparent);
    border-radius: 7px;
  }

  .run-log-answer {
    max-height: 360px;
    padding: 10px 12px;
    overflow: auto;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 60%, transparent);
    border-radius: 7px;
  }

  .studio-resizer {
    position: sticky;
    top: 12px;
    display: grid;
    place-items: center;
    width: 10px;
    min-height: 72px;
    padding: 0;
    color: var(--app-text-color-3);
    cursor: col-resize;
    background: transparent;
    border: 0;
    border-radius: 999px;
  }

  .studio-resizer::before {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 4px;
    width: 2px;
    content: '';
    background: color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 999px;
  }

  .studio-resizer span {
    z-index: 1;
    width: 6px;
    height: 28px;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 80%, transparent);
    border-radius: 999px;
    box-shadow: 0 1px 4px color-mix(in srgb, #000 10%, transparent);
  }

  .studio-resizer:hover::before,
  .studio-resizer:focus-visible::before {
    background: color-mix(in srgb, var(--app-primary-color) 55%, var(--app-border-color, #d9e1ec));
  }

  .studio-builder {
    display: grid;
    gap: 12px;
    min-width: 0;
  }

  .studio-section,
  .preview-panel {
    min-width: 0;
    padding: 14px;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: var(--app-card-radius);
  }

  .studio-section--prompt {
    border-color: color-mix(in srgb, var(--app-primary-color) 70%, var(--app-border-color, #d9e1ec));
    box-shadow: 0 0 0 2px var(--app-primary-soft-bg);
  }

  .studio-section__head,
  .preview-panel__head,
  .runtime-variables__header {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .studio-section__head h3,
  .preview-panel__head h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 650;
    line-height: 1.35;
  }

  .studio-section__head span,
  .preview-panel__head span,
  .studio-form {
    min-width: 0;
  }

  .preview-panel__head {
    align-items: center;
  }

  .preview-panel__actions {
    display: inline-flex;
    flex: 0 0 auto;
    gap: 10px;
    align-items: center;
    margin-left: auto;
  }

  .preview-output-format {
    width: 118px;
  }

  .preview-run-status {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    max-width: 180px;
    padding: 4px 9px;
    overflow: hidden;
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.5;
    white-space: nowrap;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 72%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 64%, transparent);
    border-radius: 999px;
  }

  .preview-run-status span:last-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .preview-run-status__dot {
    flex: 0 0 auto;
    width: 6px;
    height: 6px;
    background: var(--app-success-color, #18a058);
    border-radius: 999px;
  }

  .preview-run-status.is-running .preview-run-status__dot {
    background: var(--app-primary-color);
    animation: preview-run-pulse 1s ease-in-out infinite;
  }

  @keyframes preview-run-pulse {
    0%,
    100% {
      opacity: 0.45;
    }

    50% {
      opacity: 1;
    }
  }

  .system-prompt-source {
    display: grid;
    width: 100%;
    gap: 10px;
    min-width: 0;
  }

  .prompt-asset-preview {
    min-width: 0;
    padding: 10px 12px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 76%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 8px;
  }

  .prompt-asset-preview__meta {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  .prompt-asset-preview pre {
    max-height: min(360px, calc(100vh - 360px));
    margin: 0;
    padding-right: 8px;
    overflow: auto;
    color: var(--app-text-color-1);
    font-size: 13px;
    line-height: 1.75;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
    scrollbar-gutter: stable;
  }

  .workflow-system-prompt-preview pre {
    max-height: 120px;
    font-size: 12px;
    line-height: 1.55;
  }

  .variable-schema {
    display: grid;
    gap: 10px;
    min-width: 0;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
  }

  .variable-schema__header {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    justify-content: space-between;
  }

  .variable-schema__header h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 650;
    line-height: 1.35;
  }

  .variable-schema__header span {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.5;
  }

  .variable-schema__table {
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
    border-radius: 8px;
  }

  .variable-schema__row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(160px, 0.8fr) 112px 58px;
    gap: 12px;
    align-items: center;
    min-height: 44px;
    padding: 8px 10px;
    background: var(--app-surface-bg);
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 55%, transparent);
  }

  .variable-schema__row:first-child {
    border-top: 0;
  }

  .variable-schema__row--head {
    min-height: 34px;
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 600;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 82%, var(--app-surface-bg));
  }

  .variable-schema__key {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .variable-schema__key span,
  .variable-schema__key small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .variable-schema__key span {
    color: var(--app-text-color-1);
    font-weight: 600;
  }

  .variable-schema__key small {
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .variable-schema__type {
    width: 112px;
  }

  .variable-schema__row :deep(.n-switch) {
    justify-self: start;
  }

  .studio-preview {
    position: sticky;
    top: 12px;
    min-width: 0;
  }

  .preview-panel {
    display: grid;
    gap: 12px;
  }

  .runtime-variables {
    min-width: 0;
    padding: 14px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 78%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: var(--app-card-radius);
  }

  .runtime-variables.is-collapsed {
    padding: 0;
    background: var(--app-surface-bg);
  }

  .runtime-variables__header {
    width: 100%;
    padding: 0;
    align-items: center;
    margin-bottom: 12px;
    text-align: left;
    background: transparent;
    border: 0;
    color: var(--app-text-color-1);
    cursor: pointer;
    font-size: 14px;
    font-weight: 650;
  }

  .runtime-variables.is-collapsed .runtime-variables__header {
    min-height: 42px;
    padding: 0 14px;
    margin-bottom: 0;
  }

  .runtime-variables__meta {
    margin-left: auto;
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 400;
  }

  .runtime-variables__chevron {
    display: inline-flex;
    width: 18px;
    height: 18px;
    align-items: center;
    justify-content: center;
    color: var(--app-text-color-3);
    font-size: 20px;
    font-weight: 400;
    line-height: 1;
    transform: rotate(90deg);
    transition: transform 0.16s ease;
  }

  .runtime-variables.is-collapsed .runtime-variables__chevron {
    transform: rotate(0deg);
  }

  .runtime-variable-list {
    display: grid;
    gap: 12px;
  }

  .runtime-variable-item {
    display: grid;
    gap: 6px;
  }

  .runtime-variable-label {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
    max-width: 100%;
  }

  .runtime-variable-label-row {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    max-width: 100%;
    min-width: 0;
  }

  .runtime-variable-name {
    max-width: 260px;
    overflow: hidden;
    color: var(--app-text-color-1);
    font-size: 13px;
    font-weight: 520;
    line-height: 1.5;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .runtime-variable-optional,
  .runtime-variable-description {
    color: var(--app-text-color-3);
    font-size: 12px;
    font-weight: 400;
  }

  .runtime-variable-optional {
    padding: 0 6px;
    color: var(--app-text-color-3);
    line-height: 18px;
    background: color-mix(in srgb, var(--app-surface-bg) 70%, transparent);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 65%, transparent);
    border-radius: 999px;
  }

  .runtime-variable-required {
    color: var(--app-error-color, #d03050);
    font-weight: 650;
    line-height: 1;
  }

  .runtime-variable-description {
    margin-top: 6px;
    line-height: 1.5;
  }

  .runtime-variable-number {
    width: 100%;
  }

  .runtime-media-upload__title {
    color: var(--app-text-color-1);
    font-size: 13px;
    font-weight: 600;
    line-height: 1.5;
  }

  .runtime-media-upload__hint,
  .runtime-media-file {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.5;
  }

  .runtime-media-file {
    display: flex;
    gap: 8px;
    justify-content: space-between;
    margin-top: 6px;
    min-width: 0;
  }

  .runtime-media-file span:first-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chat-preview {
    display: grid;
    gap: 8px;
    min-height: 150px;
    background: transparent;
  }

  .chat-preview__bubble {
    min-width: 0;
    max-height: min(560px, calc(100vh - 340px));
    padding: 10px 12px;
    overflow: auto;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 60%, transparent);
    border-radius: var(--app-card-radius);
  }

  .chat-preview__empty {
    color: var(--app-text-color-3);
    line-height: 1.7;
  }

  .think-collapse {
    margin: 0 0 12px;
    color: var(--app-text-color-3);
    font-size: 13px;
  }

  .think-collapse__title {
    color: var(--app-text-color-3);
    font-size: 13px;
    font-weight: 500;
  }

  .think-box {
    max-height: 160px;
    margin: 4px 0 2px;
    padding: 2px 0 2px 12px;
    overflow: auto;
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.7;
    background: transparent;
    border-left: 2px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 80%, transparent);
  }

  :deep(.think-collapse .n-collapse-item) {
    margin: 0;
  }

  :deep(.think-collapse .n-collapse-item__header) {
    min-height: 24px;
    padding: 0;
  }

  :deep(.think-collapse .n-collapse-item__header-main) {
    gap: 4px;
  }

  :deep(.think-collapse .n-collapse-item__content-inner) {
    padding: 0;
  }

  .markdown-answer {
    min-width: 0;
    color: var(--app-text-color-1);
    font-size: 14px;
    line-height: 1.75;
    overflow-wrap: anywhere;
  }

  .answer-renderer {
    position: relative;
    min-width: 0;
  }

  .html-preview-toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
    min-height: 34px;
    padding: 6px 10px;
    margin-bottom: 8px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 76%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 8px;
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.5;
  }

  .html-preview-toolbar > span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .html-preview-toolbar__actions {
    display: inline-flex;
    flex: 0 0 auto;
    gap: 8px;
    align-items: center;
  }

  .html-preview-toolbar__actions :deep(.n-switch) {
    flex: 0 0 auto;
  }

  .html-answer-frame {
    width: 100%;
    min-height: 420px;
    overflow: hidden;
    background: #fff;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 8px;
  }

  .rendering-state {
    display: flex;
    gap: 10px;
    align-items: center;
    color: var(--app-text-color-2);
  }

  .rendering-state {
    min-height: 180px;
    justify-content: center;
    padding: 20px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 72%, var(--app-surface-bg));
    border: 1px dashed color-mix(in srgb, var(--app-border-color, #d9e1ec) 76%, transparent);
    border-radius: 8px;
  }

  .rendering-state strong,
  .rendering-state span {
    display: block;
  }

  .rendering-state strong {
    margin-bottom: 2px;
    color: var(--app-text-color-1);
    font-weight: 650;
  }

  .rendering-spinner {
    width: 16px;
    height: 16px;
    flex: 0 0 auto;
    border: 2px solid color-mix(in srgb, var(--app-primary-color) 18%, var(--app-border-color, #d9e1ec));
    border-top-color: var(--app-primary-color);
    border-radius: 999px;
    animation: ai-output-spin 0.8s linear infinite;
  }

  .html-source-fallback {
    margin-top: 10px;
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .html-source-fallback summary {
    cursor: pointer;
    user-select: none;
  }

  .html-source-fallback pre {
    max-height: 260px;
    margin-top: 8px;
    padding: 10px 12px;
    overflow: auto;
    color: var(--app-text-color-2);
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 86%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 58%, transparent);
    border-radius: 8px;
  }

  @keyframes ai-output-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .json-answer {
    max-height: 520px;
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 58%, transparent);
    border-radius: 8px;
  }

  .json-answer :deep(.monaco-editor),
  .json-answer :deep(.monaco-editor-background),
  .json-answer :deep(.monaco-editor .margin) {
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 70%, var(--app-surface-bg));
  }

  :deep(.markdown-answer h1),
  :deep(.markdown-answer h2),
  :deep(.markdown-answer h3),
  :deep(.markdown-answer h4) {
    margin: 18px 0 8px;
    font-weight: 650;
    line-height: 1.35;
  }

  :deep(.markdown-answer h1:first-child),
  :deep(.markdown-answer h2:first-child),
  :deep(.markdown-answer h3:first-child),
  :deep(.markdown-answer h4:first-child),
  :deep(.markdown-answer p:first-child) {
    margin-top: 0;
  }

  :deep(.markdown-answer h1) {
    font-size: 20px;
  }

  :deep(.markdown-answer h2) {
    font-size: 18px;
  }

  :deep(.markdown-answer h3) {
    font-size: 16px;
  }

  :deep(.markdown-answer p),
  :deep(.markdown-answer ul),
  :deep(.markdown-answer ol),
  :deep(.markdown-answer blockquote),
  :deep(.markdown-answer pre) {
    margin: 0 0 10px;
  }

  :deep(.markdown-answer ul),
  :deep(.markdown-answer ol) {
    padding-left: 22px;
  }

  :deep(.markdown-answer li + li) {
    margin-top: 4px;
  }

  :deep(.markdown-answer code) {
    padding: 2px 5px;
    font-size: 12px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 86%, var(--app-surface-bg));
    border-radius: 4px;
  }

  :deep(.markdown-answer pre) {
    padding: 10px 12px;
    overflow: auto;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 86%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 58%, transparent);
    border-radius: 8px;
  }

  :deep(.markdown-answer pre code) {
    padding: 0;
    background: transparent;
  }

  :deep(.markdown-answer blockquote) {
    padding: 8px 12px;
    color: var(--app-text-color-2);
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 72%, var(--app-surface-bg));
    border-left: 3px solid var(--app-primary-color);
    border-radius: 6px;
  }

  :deep(.markdown-answer table) {
    width: 100%;
    margin-bottom: 10px;
    border-collapse: collapse;
  }

  :deep(.markdown-answer th),
  :deep(.markdown-answer td) {
    padding: 8px;
    border: 1px solid var(--app-border-color, #d9e1ec);
  }

  .preview-collapse {
    min-width: 0;
  }

  .trace-list {
    margin: 0;
  }

  .trace-list dt {
    margin-top: 8px;
    font-weight: 600;
  }

  .trace-list dd {
    margin: 4px 0 0;
  }

  pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }

  code {
    display: block;
    padding: 10px;
    overflow: auto;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 80%, var(--app-surface-bg));
    border-radius: 6px;
  }

  @media (max-width: 1180px) {
    .studio-workbench {
      grid-template-columns: 1fr;
    }

    .run-log-layout {
      grid-template-columns: 1fr;
    }

    .workflow-fullscreen {
      grid-template-columns: 1fr;
      height: auto;
      min-height: 0;
    }

    .workflow-canvas-panel {
      height: 520px;
    }

    .workflow-floating-panel {
      top: 58px;
      right: 10px;
      width: min(390px, calc(100% - 20px));
    }

    .workflow-floating-panel.is-run-panel-open {
      right: 10px;
      width: min(390px, calc(100% - 20px));
    }

    .studio-resizer {
      display: none;
    }

    .studio-preview {
      position: static;
    }
  }
</style>
