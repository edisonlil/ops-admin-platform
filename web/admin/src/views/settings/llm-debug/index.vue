<template>
  <div class="llm-debug">
    <n-card :bordered="false" size="small" class="proCard debug-header">
      <div class="debug-header__main">
        <div>
          <div class="eyebrow">LLM Runtime</div>
          <h2>模型调试</h2>
          <p>使用 OpenAI 兼容协议调用已配置的模型或路由策略，验证供应商、模型、fallback 和响应格式。</p>
        </div>
        <n-space align="center">
          <n-button secondary :loading="loadingModels" @click="loadModels">刷新模型</n-button>
          <n-button v-if="canSendDebug" type="primary" :loading="submitting" @click="submitDebug">发送</n-button>
        </n-space>
      </div>
    </n-card>

    <div class="debug-grid">
      <n-card :bordered="false" size="small" class="proCard debug-panel">
        <template #header>请求</template>
        <n-form label-placement="top" :model="form">
          <n-form-item label="模型 / 路由">
            <n-select
              v-model:value="form.model"
              :options="modelOptions"
              filterable
              tag
              placeholder="选择模型 key 或路由 key"
            />
          </n-form-item>
          <n-grid :cols="2" :x-gap="12">
            <n-form-item-gi label="温度">
              <n-slider v-model:value="form.temperature" :min="0" :max="2" :step="0.1" />
            </n-form-item-gi>
            <n-form-item-gi label="响应格式">
              <n-select v-model:value="form.responseFormat" :options="responseFormatOptions" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="输出模式">
            <n-space align="center">
              <n-switch v-model:value="form.enableThinkOutput">
                <template #checked>Think 开</template>
                <template #unchecked>Think 关</template>
              </n-switch>
              <n-switch v-model:value="form.stream">
                <template #checked>流式</template>
                <template #unchecked>非流式</template>
              </n-switch>
            </n-space>
          </n-form-item>
          <n-form-item label="System">
            <n-input v-model:value="form.systemPrompt" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
          </n-form-item>
          <n-form-item label="User">
            <n-input v-model:value="form.userPrompt" type="textarea" :autosize="{ minRows: 8, maxRows: 14 }" />
          </n-form-item>
        </n-form>
      </n-card>

      <n-card :bordered="false" size="small" class="proCard debug-panel">
        <template #header>响应</template>
        <template #header-extra>
          <n-space align="center" size="small">
            <n-tag v-if="resultStatus" size="small" :type="resultStatus === 'success' ? 'success' : 'error'">
              {{ resultStatus === 'success' ? '成功' : '失败' }}
            </n-tag>
            <n-tag v-if="elapsedLabel" size="small">{{ elapsedLabel }}</n-tag>
          </n-space>
        </template>

        <n-alert v-if="submitting && form.stream" type="info" :bordered="false" class="stream-alert">
          正在接收流式响应
        </n-alert>
        <n-collapse v-if="thinkText" class="think-collapse" default-expanded-names="think">
          <n-collapse-item title="Think" name="think">
            <pre class="think-box">{{ thinkText }}</pre>
          </n-collapse-item>
        </n-collapse>
        <div class="answer-box" :class="{ 'answer-box--streaming': submitting && form.stream }">
          <pre>{{ answerText || (submitting ? '等待首个 token...' : '暂无响应') }}</pre>
        </div>
        <n-collapse v-if="rawResponse" class="raw-collapse">
          <n-collapse-item title="原始响应" name="raw">
            <pre class="raw-json">{{ rawResponse }}</pre>
          </n-collapse-item>
        </n-collapse>
      </n-card>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import {
    createLlmOpenAIChatCompletion,
    getLlmOpenAIModels,
    type OpenAIChatMessagePayload,
    type OpenAIChatCompletionPayload,
  } from '@/api/business';
  import { useGlobSetting } from '@/hooks/setting';
  import { usePermission } from '@/hooks/web/usePermission';
  import { useUser } from '@/store/modules/user';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const userStore = useUser();
  const { apiUrl, urlPrefix } = useGlobSetting();
  const loadingModels = ref(false);
  const submitting = ref(false);
  const canSendDebug = computed(() => hasPermission(['llm_debug:send']));
  const modelRows = ref<Recordable[]>([]);
  const answerText = ref('');
  const thinkText = ref('');
  const rawResponse = ref('');
  const resultStatus = ref('');
  const elapsedMs = ref(0);

  const form = reactive({
    model: '',
    temperature: 0.1,
    responseFormat: 'text',
    enableThinkOutput: false,
    stream: true,
    systemPrompt: '你是一个严谨的后台模型调试助手，请直接回答问题。',
    userPrompt: '用一句话说明当前模型配置是否可用。',
  });

  const responseFormatOptions = [
    { label: 'text', value: 'text' },
    { label: 'json_object', value: 'json_object' },
  ];

  const modelOptions = computed(() =>
    modelRows.value.map((item) => ({
      value: String(item.id || ''),
      label: `${item.display_name || item.id} · ${item.kind || 'model'} · ${item.id}`,
    }))
  );

  const elapsedLabel = computed(() => (elapsedMs.value ? `${(elapsedMs.value / 1000).toFixed(2)}s` : ''));

  async function loadModels() {
    loadingModels.value = true;
    try {
      const payload = await getLlmOpenAIModels();
      modelRows.value = Array.isArray(payload?.data) ? payload.data : [];
      if (!form.model && modelRows.value.length) {
        form.model = String(modelRows.value[0].id || '');
      }
    } finally {
      loadingModels.value = false;
    }
  }

  function buildMessages() {
    const messages: OpenAIChatMessagePayload[] = [];
    if (form.systemPrompt.trim()) {
      messages.push({ role: 'system', content: form.systemPrompt.trim() });
    }
    messages.push({ role: 'user', content: form.userPrompt.trim() });
    return messages;
  }

  async function submitDebug() {
    if (!form.model.trim()) {
      message.warning('请选择模型或路由');
      return;
    }
    if (!form.userPrompt.trim()) {
      message.warning('请输入 User 内容');
      return;
    }
    submitting.value = true;
    answerText.value = '';
    thinkText.value = '';
    rawResponse.value = '';
    resultStatus.value = '';
    const startedAt = performance.now();
    try {
      const requestPayload: OpenAIChatCompletionPayload = {
        model: form.model.trim(),
        messages: buildMessages(),
        temperature: form.temperature,
        enable_think_output: form.enableThinkOutput,
        stream: form.stream,
        ...(form.responseFormat === 'json_object' ? { response_format: { type: 'json_object' } } : {}),
      };
      if (form.stream) {
        await submitStreamingDebug(requestPayload);
        elapsedMs.value = performance.now() - startedAt;
        return;
      }
      const payload = await createLlmOpenAIChatCompletion(requestPayload);
      elapsedMs.value = performance.now() - startedAt;
      resultStatus.value = 'success';
      const content = payload?.choices?.[0]?.message?.content || '';
      const parsed = splitThinkContent(content);
      thinkText.value = parsed.think;
      answerText.value = parsed.answer;
      rawResponse.value = JSON.stringify(payload, null, 2);
    } catch (error) {
      elapsedMs.value = performance.now() - startedAt;
      resultStatus.value = 'failed';
      answerText.value = error instanceof Error ? error.message : String(error);
    } finally {
      submitting.value = false;
    }
  }

  onMounted(loadModels);

  async function submitStreamingDebug(payload: OpenAIChatCompletionPayload) {
    const response = await fetch(openAIChatCompletionsUrl(), {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(userStore.getToken ? { Authorization: `Bearer ${userStore.getToken}`, token: userStore.getToken } : {}),
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }
    if (!response.body) {
      throw new Error('当前浏览器不支持流式响应');
    }
    resultStatus.value = 'success';
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
        const line = event.split('\n').find((item) => item.startsWith('data: '));
        if (!line) continue;
        const data = line.slice(6).trim();
        if (!data || data === '[DONE]') continue;
        const chunk = JSON.parse(data);
        const delta = chunk?.choices?.[0]?.delta || {};
        const reasoningDelta =
          delta.reasoning_content || delta.reasoning || delta.think || delta.thinking || '';
        const contentDelta = delta.content || '';
        if (reasoningDelta) {
          reasoning += reasoningDelta;
          thinkText.value = reasoning;
        }
        if (contentDelta) {
          content += contentDelta;
          const parsed = splitThinkContent(content);
          thinkText.value = reasoning || parsed.think;
          answerText.value = parsed.answer;
        }
      }
    }
    rawResponse.value = JSON.stringify({ stream: true, content, reasoning }, null, 2);
  }

  function openAIChatCompletionsUrl() {
    return `${apiUrl || ''}${urlPrefix || ''}/llm/openai/v1/chat/completions`;
  }

  function splitThinkContent(content: string) {
    const match = content.match(/<think\b[^>]*>([\s\S]*?)<\/think>/i);
    if (!match) {
      return { think: '', answer: content };
    }
    return {
      think: match[1].trim(),
      answer: content.replace(match[0], '').trim(),
    };
  }
</script>

<style lang="less" scoped>
  .llm-debug {
    padding: 16px;
  }

  .debug-header {
    margin-bottom: 12px;
  }

  .debug-header__main {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;

    h2 {
      margin: 2px 0 6px;
      font-size: 24px;
      font-weight: 700;
    }

    p {
      margin: 0;
      color: #5d6472;
    }
  }

  .eyebrow {
    font-size: 12px;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0;
    text-transform: uppercase;
  }

  .debug-grid {
    display: grid;
    grid-template-columns: minmax(360px, 0.92fr) minmax(420px, 1.08fr);
    gap: 12px;
  }

  .debug-panel {
    min-height: 560px;
  }

  .answer-box {
    min-height: 420px;
    padding: 14px;
    overflow: auto;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;

    pre {
      margin: 0;
      color: #e5edf7;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
    }
  }

  .answer-box--streaming {
    border-color: #2b7fff;
    box-shadow: inset 0 0 0 1px rgba(43, 127, 255, 0.35);
  }

  .stream-alert {
    margin-bottom: 12px;
  }

  .think-collapse {
    margin-bottom: 12px;
  }

  .think-box {
    max-height: 220px;
    padding: 12px;
    overflow: auto;
    color: #475569;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .raw-collapse {
    margin-top: 12px;
  }

  .raw-json {
    max-height: 260px;
    padding: 12px;
    overflow: auto;
    background: #f8fafc;
    border-radius: 6px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  @media (max-width: 1100px) {
    .debug-grid {
      grid-template-columns: 1fr;
    }

    .debug-header__main {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
