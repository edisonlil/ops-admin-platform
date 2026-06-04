<template>
  <section
    ref="agentRuntimeRef"
    class="agent-runtime"
    :class="{ 'is-trace-hidden': !traceVisible }"
    :style="agentRuntimeStyle"
  >
    <aside class="agent-runtime__config">
      <header>
        <div>
          <h3>Agent 调试工作台</h3>
          <span>配置本次调试运行</span>
        </div>
      </header>

      <div class="agent-config-body">
        <section class="agent-config-section">
          <h4>模型与路由</h4>
          <n-select
            :value="modelValue"
            :options="modelOptions"
            :loading="modelLoading"
            filterable
            clearable
            placeholder="选择 Agent 运行模型或路由"
            @update:value="handleModelUpdate"
          />
          <n-alert v-if="!modelValue" type="warning" :bordered="false">请选择模型后再发送消息</n-alert>
        </section>

        <section class="agent-config-section">
          <h4>能力编排</h4>
          <div class="agent-config-row">
            <div>
              <strong>可用工具</strong>
              <span>待接入</span>
            </div>
            <n-button size="small" secondary disabled>配置</n-button>
          </div>
          <div class="agent-config-row">
            <div>
              <strong>可用 Skill</strong>
              <span>{{ skillBindings.length ? `${skillBindings.length} 个已绑定` : '未绑定' }}</span>
            </div>
            <n-switch :value="skillPlanningEnabled" size="small" @update:value="handleSkillPlanningUpdate" />
          </div>
          <div class="agent-config-row">
            <div>
              <strong>调用预算</strong>
              <span>自动规划最多调用次数</span>
            </div>
            <n-input-number
              class="agent-skill-budget"
              size="small"
              :value="skillCallBudget"
              :min="0"
              :max="10"
              @update:value="handleSkillBudgetUpdate"
            />
          </div>
          <div v-if="skillBindings.length" class="agent-skill-list">
            <span v-for="item in skillBindings" :key="skillBindingKey(item)">
              {{ skillBindingLabel(item) }}
            </span>
          </div>
          <div class="agent-config-row">
            <div>
              <strong>会话记忆</strong>
              <span>待接入</span>
            </div>
            <n-switch disabled />
          </div>
        </section>
      </div>

      <footer class="agent-config-actions">
        <n-button secondary :loading="loadingConversations" @click="handleResetConversation">重置会话</n-button>
        <n-button type="primary" :loading="saving" @click="emit('saveConfig')">保存配置</n-button>
      </footer>
    </aside>

    <button
      class="agent-resizer"
      type="button"
      aria-label="拖动调整 Agent 编排面板宽度"
      title="拖动调整 Agent 编排面板宽度"
      @pointerdown="startConfigResize"
      @dblclick="resetConfigWidth"
    >
      <span></span>
    </button>

    <main class="agent-runtime__main" :class="{ 'has-trace-toggle': !traceVisible }">
      <div v-if="!traceVisible" class="agent-trace-toggle-bar">
        <n-button size="small" secondary @click="traceVisible = true">显示 Trace</n-button>
      </div>
      <section ref="messagePaneRef" class="agent-message-list">
        <n-spin :show="loadingMessages">
          <div v-if="messages.length" class="agent-message-stack">
            <article
              v-for="item in messages"
              :key="item.message_key"
              class="agent-message"
              :class="[`is-${item.role}`, `is-${item.status}`]"
            >
              <div class="agent-message__role">{{ roleLabel(item.role) }}</div>
              <div class="agent-message__bubble">
                <div v-if="item.content" class="agent-message__content" v-html="renderMarkdown(item.content)"></div>
                <div v-else class="agent-message__empty">{{ item.status === 'streaming' ? '正在生成...' : '暂无内容' }}</div>
                <small v-if="item.status === 'failed'">{{ item.error_message || '生成失败' }}</small>
              </div>
            </article>
          </div>
          <n-empty v-else size="small" description="输入任务开始调试 Agent" />
        </n-spin>
      </section>

      <footer class="agent-composer">
        <n-alert v-if="errorText" type="error" :bordered="false">{{ errorText }}</n-alert>
        <n-input
          v-model:value="draft"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          placeholder="输入要交给 Agent 的任务或问题"
          @keydown.enter.exact.prevent="handleSend"
        />
        <div class="agent-composer__actions">
          <span>{{ activeConversation?.title || 'Agent 调试会话' }}</span>
          <n-button v-if="sending" type="warning" @click="stop">停止生成</n-button>
          <n-button v-else type="primary" :disabled="!canSend" @click="handleSend">发送</n-button>
        </div>
      </footer>
    </main>

    <aside v-if="traceVisible" class="agent-runtime__trace">
      <header>
        <h3>运行 Trace</h3>
        <div class="agent-trace-head__actions">
          <span>{{ traceState?.trace_id || '等待运行' }}</span>
          <n-button size="tiny" tertiary @click="traceVisible = false">隐藏</n-button>
        </div>
      </header>
      <dl v-if="traceState?.trace" class="agent-trace-list">
        <dt>状态</dt>
        <dd>{{ traceState.trace.status || '-' }}</dd>
        <dt>模型</dt>
        <dd>{{ traceState.trace.model_key || traceState.trace.route_key || '-' }}</dd>
        <dt>耗时</dt>
        <dd>{{ traceState.trace.elapsed_ms || 0 }} ms</dd>
        <dt v-if="traceState.trace.error_message">错误</dt>
        <dd v-if="traceState.trace.error_message">{{ traceState.trace.error_message }}</dd>
      </dl>
      <div v-if="traceState?.skill_plan || traceState?.skill_results?.length" class="agent-skill-trace">
        <section v-if="traceState.skill_plan">
          <strong>Skill 计划</strong>
          <span>{{ traceState.skill_plan.skills.length }} 个可用，{{ traceState.skill_plan.planned_calls.length }} 个自动调用</span>
        </section>
        <details v-for="item in traceState.skill_results || []" :key="skillTraceItemKey(item)" open>
          <summary>
            <span>{{ skillTraceTitle(item) }}</span>
            <small>{{ skillTraceStatus(item) }}</small>
          </summary>
          <p v-if="skillTraceSummary(item)">{{ skillTraceSummary(item) }}</p>
        </details>
      </div>
      <n-empty v-else-if="!traceState?.trace" size="small" description="发送消息后展示本次运行信息" />
    </aside>
  </section>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import type { SelectOption } from 'naive-ui';
  import MarkdownIt from 'markdown-it';
  import { useAgentChat } from './useAgentChat';

  const props = withDefaults(
    defineProps<{
      appKey: string;
      modelValue?: string;
      skillPlanningEnabled?: boolean;
      skillCallBudget?: number;
      skillBindings?: Array<Record<string, unknown>>;
      modelOptions?: SelectOption[];
      modelLoading?: boolean;
      saving?: boolean;
    }>(),
    {
      modelValue: '',
      skillPlanningEnabled: false,
      skillCallBudget: 3,
      skillBindings: () => [],
      modelOptions: () => [],
      modelLoading: false,
      saving: false,
    }
  );

  const emit = defineEmits<{
    (event: 'update:modelValue', value: string): void;
    (event: 'update:skillPlanningEnabled', value: boolean): void;
    (event: 'update:skillCallBudget', value: number): void;
    (event: 'saveConfig'): void;
  }>();

  const markdownRenderer = new MarkdownIt({ html: false, linkify: true, breaks: true });
  const draft = ref('');
  const traceVisible = ref(true);
  const agentRuntimeRef = ref<HTMLElement | null>(null);
  const messagePaneRef = ref<HTMLElement | null>(null);
  const configWidth = ref(300);
  const configResizeDragged = ref(false);
  const {
    messages,
    activeConversation,
    loadingConversations,
    loadingMessages,
    sending,
    errorText,
    traceState,
    loadConversations,
    resetConversation,
    send,
    stop,
  } = useAgentChat(() => props.appKey);

  const canSend = computed(() => Boolean(draft.value.trim() && !sending.value && props.modelValue));
  const agentRuntimeStyle = computed(() => ({
    '--agent-config-width': `${configWidth.value}px`,
  }));

  function renderMarkdown(value: string) {
    return markdownRenderer.render(value || '');
  }

  function roleLabel(role: string) {
    if (role === 'user') return '用户';
    if (role === 'assistant') return 'Agent';
    if (role === 'tool') return '工具';
    return '系统';
  }

  function handleModelUpdate(value: string | number | null) {
    emit('update:modelValue', value == null ? '' : String(value));
  }

  function handleSkillPlanningUpdate(value: boolean) {
    emit('update:skillPlanningEnabled', value);
  }

  function handleSkillBudgetUpdate(value: number | null) {
    emit('update:skillCallBudget', clampNumber(Number(value || 0), 0, 10));
  }

  function skillBindingKey(item: Record<string, unknown>) {
    return String(item.skill_key || item.alias || JSON.stringify(item));
  }

  function skillBindingLabel(item: Record<string, unknown>) {
    const key = String(item.alias || item.skill_key || 'Skill');
    const mode = String(item.mode || 'auto');
    return `${key} · ${skillModeLabel(mode)}`;
  }

  function skillModeLabel(mode: string) {
    if (mode === 'required') return '必选';
    if (mode === 'manual') return '手动';
    if (mode === 'disabled') return '停用';
    return '自动';
  }

  function skillTraceItemKey(item: Record<string, unknown>) {
    const skill = skillTracePayload(item);
    return String(skill.run_id || `${skill.skill_key || skill.alias || 'skill'}-${skill.elapsed_ms || 0}`);
  }

  function skillTracePayload(item: Record<string, unknown>) {
    const skill = item.skill;
    return skill && typeof skill === 'object' && !Array.isArray(skill) ? (skill as Record<string, unknown>) : item;
  }

  function skillTraceTitle(item: Record<string, unknown>) {
    const skill = skillTracePayload(item);
    return String(skill.alias || skill.skill_key || 'Skill');
  }

  function skillTraceStatus(item: Record<string, unknown>) {
    const skill = skillTracePayload(item);
    return String(skill.status || '-');
  }

  function skillTraceSummary(item: Record<string, unknown>) {
    const skill = skillTracePayload(item);
    return String(skill.summary || skill.error_message || '');
  }

  function clampNumber(value: number, min: number, max: number) {
    return Math.min(Math.max(value, min), max);
  }

  function resetConfigWidth() {
    configWidth.value = 300;
  }

  function startConfigResize(event: PointerEvent) {
    const target = event.currentTarget as HTMLElement;
    const container = agentRuntimeRef.value;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const startX = event.clientX;
    configResizeDragged.value = false;
    target.setPointerCapture?.(event.pointerId);

    const resize = (moveEvent: PointerEvent) => {
      const delta = Math.abs(moveEvent.clientX - startX);
      if (delta > 3) configResizeDragged.value = true;
      const nextWidth = moveEvent.clientX - rect.left;
      const maxWidth = Math.max(320, Math.min(520, rect.width * 0.42));
      configWidth.value = clampNumber(nextWidth, 240, maxWidth);
    };
    const stopResize = () => {
      target.releasePointerCapture?.(event.pointerId);
      window.removeEventListener('pointermove', resize);
      window.removeEventListener('pointerup', stopResize);
      window.removeEventListener('pointercancel', stopResize);
    };
    window.addEventListener('pointermove', resize);
    window.addEventListener('pointerup', stopResize, { once: true });
    window.addEventListener('pointercancel', stopResize, { once: true });
  }

  async function handleResetConversation() {
    await resetConversation();
  }

  async function handleSend() {
    const value = draft.value.trim();
    if (!value || sending.value || !props.modelValue) return;
    draft.value = '';
    await send(value, {
      model: props.modelValue,
      skill_planning: props.skillPlanningEnabled,
      skill_call_budget: clampNumber(Number(props.skillCallBudget || 0), 0, 10),
    });
  }

  function scrollToBottom() {
    void nextTick(() => {
      const el = messagePaneRef.value;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }

  watch(messages, scrollToBottom, { deep: true });
  watch(
    () => props.appKey,
    () => {
      void loadConversations();
    }
  );

  onMounted(() => {
    void loadConversations();
  });
</script>

<style scoped>
  .agent-runtime {
    display: grid;
    grid-template-columns: minmax(240px, var(--agent-config-width, 300px)) 10px minmax(0, 1fr) minmax(220px, 280px);
    gap: 8px;
    height: min(720px, calc(100vh - 220px));
    min-height: 520px;
    max-height: 720px;
    min-width: 0;
    overflow: hidden;
  }

  .agent-runtime.is-trace-hidden {
    grid-template-columns: minmax(240px, var(--agent-config-width, 300px)) 10px minmax(0, 1fr);
  }

  .agent-runtime__config,
  .agent-runtime__main,
  .agent-runtime__trace {
    min-width: 0;
    min-height: 0;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color, #d9e1ec);
    border-radius: var(--app-card-radius, 8px);
  }

  .agent-runtime__config,
  .agent-runtime__trace {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto;
    overflow: hidden;
  }

  .agent-runtime__trace {
    grid-template-rows: auto minmax(0, 1fr);
  }

  .agent-runtime header {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    justify-content: space-between;
    padding: 12px;
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
  }

  .agent-runtime h3,
  .agent-config-section h4 {
    margin: 0;
    font-size: 15px;
    font-weight: 650;
  }

  .agent-config-section h4 {
    font-size: 14px;
  }

  .agent-runtime header span,
  .agent-config-row span,
  .agent-composer__actions span,
  .agent-message__role,
  .agent-trace-list dt,
  .agent-message__empty {
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .agent-config-body {
    display: grid;
    align-content: start;
    gap: 14px;
    padding: 12px;
    overflow: auto;
  }

  .agent-config-section {
    display: grid;
    gap: 10px;
  }

  .agent-config-row {
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
    padding: 10px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 78%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 7px;
  }

  .agent-config-row > div {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .agent-config-row strong {
    font-size: 13px;
    font-weight: 600;
  }

  .agent-skill-budget {
    width: 92px;
  }

  .agent-skill-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    min-width: 0;
  }

  .agent-skill-list span {
    max-width: 100%;
    padding: 3px 7px;
    overflow: hidden;
    color: var(--app-text-color-2);
    text-overflow: ellipsis;
    white-space: nowrap;
    background: color-mix(in srgb, var(--app-primary-color) 8%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-primary-color) 18%, var(--app-border-color, #d9e1ec));
    border-radius: 999px;
  }

  .agent-config-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    padding: 12px;
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
  }

  .agent-resizer {
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
    touch-action: none;
  }

  .agent-resizer::before {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 4px;
    width: 2px;
    content: '';
    background: color-mix(in srgb, var(--app-border-color, #d9e1ec) 78%, transparent);
    border-radius: 999px;
  }

  .agent-resizer span {
    z-index: 1;
    width: 6px;
    height: 28px;
    background: var(--app-surface-bg);
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 80%, transparent);
    border-radius: 999px;
    box-shadow: 0 1px 2px color-mix(in srgb, #000 8%, transparent);
  }

  .agent-resizer:hover::before,
  .agent-resizer:focus-visible::before {
    background: color-mix(in srgb, var(--app-primary-color) 55%, var(--app-border-color, #d9e1ec));
  }

  .agent-runtime__main {
    display: grid;
    grid-template-rows: minmax(0, 1fr) auto;
    overflow: hidden;
  }

  .agent-runtime__main.has-trace-toggle {
    grid-template-rows: auto minmax(0, 1fr) auto;
  }

  .agent-trace-toggle-bar {
    display: flex;
    justify-content: flex-end;
    min-height: 42px;
    padding: 8px 12px;
    border-bottom: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
  }

  .agent-message-list {
    min-height: 0;
    padding: 14px;
    overflow: auto;
  }

  .agent-message-list :deep(.n-spin-container),
  .agent-message-list :deep(.n-spin-content) {
    min-height: 100%;
  }

  .agent-message-stack {
    display: grid;
    gap: 12px;
  }

  .agent-message {
    display: grid;
    gap: 5px;
    max-width: min(760px, 92%);
  }

  .agent-message.is-user {
    justify-self: end;
  }

  .agent-message.is-assistant,
  .agent-message.is-tool,
  .agent-message.is-system {
    justify-self: start;
  }

  .agent-message__role {
    padding: 0 3px;
  }

  .agent-message.is-user .agent-message__role {
    text-align: right;
  }

  .agent-message__bubble {
    min-width: 0;
    padding: 0;
    background: transparent;
    border: 0;
    border-radius: 0;
  }

  .agent-message.is-user .agent-message__bubble {
    padding: 10px 12px;
    color: var(--app-primary-text-color, #fff);
    background: var(--app-primary-color);
    border-color: var(--app-primary-color);
    border-radius: 8px;
  }

  .agent-message.is-failed .agent-message__bubble {
    color: var(--app-error-color, #d03050);
  }

  .agent-message__content {
    min-width: 0;
    line-height: 1.7;
    overflow-wrap: anywhere;
  }

  .agent-message__content :deep(p:first-child) {
    margin-top: 0;
  }

  .agent-message__content :deep(p:last-child) {
    margin-bottom: 0;
  }

  .agent-composer {
    display: grid;
    gap: 10px;
    padding: 12px;
    border-top: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 72%, transparent);
  }

  .agent-composer__actions {
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
  }

  .agent-trace-list {
    display: grid;
    grid-template-columns: 64px minmax(0, 1fr);
    gap: 8px 10px;
    align-content: start;
    padding: 12px;
    overflow: auto;
  }

  .agent-trace-head__actions {
    display: grid;
    gap: 6px;
    justify-items: end;
    min-width: 0;
  }

  .agent-trace-head__actions span {
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .agent-trace-list dd {
    min-width: 0;
    margin: 0;
    overflow-wrap: anywhere;
  }

  .agent-skill-trace {
    display: grid;
    gap: 8px;
    padding: 0 12px 12px;
    overflow: auto;
  }

  .agent-skill-trace section,
  .agent-skill-trace details {
    min-width: 0;
    padding: 8px;
    background: color-mix(in srgb, var(--app-surface-muted-bg, #f5f7fb) 72%, var(--app-surface-bg));
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 68%, transparent);
    border-radius: 7px;
  }

  .agent-skill-trace strong,
  .agent-skill-trace span,
  .agent-skill-trace small,
  .agent-skill-trace p {
    overflow-wrap: anywhere;
  }

  .agent-skill-trace strong {
    display: block;
    margin-bottom: 2px;
    font-size: 13px;
  }

  .agent-skill-trace summary {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
  }

  .agent-skill-trace p {
    margin: 8px 0 0;
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  @media (max-width: 1180px) {
    .agent-runtime {
      grid-template-columns: 1fr;
      height: auto;
      max-height: none;
      overflow: visible;
    }

    .agent-resizer {
      display: none;
    }

    .agent-runtime__main {
      min-height: 560px;
    }
  }
</style>
