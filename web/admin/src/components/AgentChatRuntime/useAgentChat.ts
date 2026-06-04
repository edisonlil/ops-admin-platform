import { computed, nextTick, reactive, ref, watch } from 'vue';
import {
  createAiApplicationAgentConversation,
  fetchAiApplicationAgentMessageStream,
  getAiApplicationAgentConversations,
  getAiApplicationAgentMessages,
  type AiAgentMessage,
  type AiAgentMessagePayload,
} from '@/api/aiStudio';
import type { AgentConversation, AgentStreamMeta, AgentTraceState } from './types';

function parseSseBlock(block: string) {
  let event = 'message';
  const data: string[] = [];
  block.split(/\r?\n/).forEach((line) => {
    if (line.startsWith('event:')) event = line.slice(6).trim() || 'message';
    if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  });
  return { event, data: data.join('\n') };
}

function streamDeltaContent(payload: Record<string, any>) {
  const choices = Array.isArray(payload.choices) ? payload.choices : [];
  const first = choices[0];
  const delta = first?.delta || {};
  return String(delta.content || delta.reasoning_content || '');
}

export function useAgentChat(appKey: () => string) {
  const conversations = ref<AgentConversation[]>([]);
  const messages = ref<AiAgentMessage[]>([]);
  const activeConversationKey = ref('');
  const loadingConversations = ref(false);
  const loadingMessages = ref(false);
  const sending = ref(false);
  const errorText = ref('');
  const streamMeta = reactive<AgentStreamMeta>({});
  const traceState = ref<AgentTraceState | null>(null);
  let abortController: AbortController | null = null;

  const activeConversation = computed(
    () => conversations.value.find((item) => item.conversation_key === activeConversationKey.value) || null
  );

  async function loadConversations() {
    const key = appKey();
    if (!key) return;
    loadingConversations.value = true;
    errorText.value = '';
    try {
      const payload = await getAiApplicationAgentConversations(key, { page: 1, page_size: 50 });
      conversations.value = payload.items || [];
      const currentStillExists = conversations.value.some((item) => item.conversation_key === activeConversationKey.value);
      const nextConversationKey = currentStillExists ? activeConversationKey.value : conversations.value[0]?.conversation_key || '';
      if (activeConversationKey.value !== nextConversationKey) {
        activeConversationKey.value = nextConversationKey;
      } else if (nextConversationKey) {
        await loadMessages(nextConversationKey);
      } else {
        messages.value = [];
      }
    } catch (error) {
      errorText.value = error instanceof Error ? error.message : String(error);
    } finally {
      loadingConversations.value = false;
    }
  }

  async function createConversation(title = '') {
    const key = appKey();
    if (!key) return null;
    loadingConversations.value = true;
    try {
      const conversation = await createAiApplicationAgentConversation(key, { title });
      conversations.value = [conversation, ...conversations.value.filter((item) => item.conversation_key !== conversation.conversation_key)];
      activeConversationKey.value = conversation.conversation_key;
      messages.value = [];
      traceState.value = null;
      errorText.value = '';
      return conversation;
    } finally {
      loadingConversations.value = false;
    }
  }

  async function loadMessages(conversationKey = activeConversationKey.value) {
    const key = appKey();
    if (!key || !conversationKey) {
      messages.value = [];
      return;
    }
    loadingMessages.value = true;
    errorText.value = '';
    try {
      const payload = await getAiApplicationAgentMessages(key, conversationKey, { page: 1, page_size: 80 });
      messages.value = payload.items || [];
    } catch (error) {
      errorText.value = error instanceof Error ? error.message : String(error);
    } finally {
      loadingMessages.value = false;
    }
  }

  async function selectConversation(conversationKey: string) {
    if (activeConversationKey.value === conversationKey) return;
    activeConversationKey.value = conversationKey;
    await loadMessages(conversationKey);
  }

  async function resetConversation() {
    stop();
    return createConversation('Agent 调试会话');
  }

  async function send(
    content: string,
    options: Pick<AiAgentMessagePayload, 'model' | 'variables' | 'temperature' | 'skill_planning' | 'skill_call_budget'> = {}
  ) {
    const key = appKey();
    const text = content.trim();
    if (!key || !text) return;
    let conversationKey = activeConversationKey.value;
    if (!conversationKey) {
      const created = await createConversation('Agent 调试会话');
      conversationKey = created?.conversation_key || '';
    }
    if (!conversationKey) return;

    abortController?.abort();
    abortController = new AbortController();
    sending.value = true;
    errorText.value = '';
    traceState.value = null;
    for (const keyName of Object.keys(streamMeta) as Array<keyof typeof streamMeta>) {
      delete streamMeta[keyName];
    }

    const localUserKey = `local_user_${Date.now()}`;
    const localAssistantKey = `local_assistant_${Date.now()}`;
    messages.value = [
      ...messages.value,
      {
        id: 0,
        tenant_id: 0,
        conversation_key: conversationKey,
        message_key: localUserKey,
        app_key: key,
        role: 'user',
        content: text,
        content_json: {},
        status: 'completed',
        trace_id: '',
        error_code: '',
        error_message: '',
        metadata: {},
      },
      {
        id: 0,
        tenant_id: 0,
        conversation_key: conversationKey,
        message_key: localAssistantKey,
        app_key: key,
        role: 'assistant',
        content: '',
        content_json: {},
        status: 'streaming',
        trace_id: '',
        error_code: '',
        error_message: '',
        metadata: {},
      },
    ];

    try {
      const requestPayload: AiAgentMessagePayload = { content: text, variables: options.variables || {} };
      if (options.model) requestPayload.model = options.model;
      if (typeof options.temperature === 'number') requestPayload.temperature = options.temperature;
      if (typeof options.skill_planning === 'boolean') requestPayload.skill_planning = options.skill_planning;
      if (typeof options.skill_call_budget === 'number') requestPayload.skill_call_budget = options.skill_call_budget;
      const response = await fetchAiApplicationAgentMessageStream(key, conversationKey, requestPayload, abortController.signal);
      if (!response.ok || !response.body) throw new Error(`Agent stream failed: ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split(/\n\n/);
        buffer = chunks.pop() || '';
        for (const chunk of chunks) {
          const { event, data } = parseSseBlock(chunk);
          if (!data || data === '[DONE]') continue;
          let payload: Record<string, any> = {};
          try {
            payload = JSON.parse(data);
          } catch {
            continue;
          }
          if (event === 'meta') {
            Object.assign(streamMeta, payload);
            replaceLocalMessageKey(localUserKey, String(payload.user_message_key || localUserKey));
            replaceLocalMessageKey(localAssistantKey, String(payload.assistant_message_key || localAssistantKey));
          } else if (event === 'trace') {
            traceState.value = { ...(traceState.value || { trace_id: String(payload.trace_id || '') }), trace_id: String(payload.trace_id || ''), trace: payload.trace };
          } else if (event === 'skill_plan') {
            traceState.value = {
              ...(traceState.value || { trace_id: String(payload.trace_id || '') }),
              trace_id: String(payload.trace_id || traceState.value?.trace_id || ''),
              skill_plan: {
                trace_id: payload.trace_id,
                skills: Array.isArray(payload.skills) ? payload.skills : [],
                planned_calls: Array.isArray(payload.planned_calls) ? payload.planned_calls : [],
              },
            };
          } else if (event === 'skill_result') {
            const current = traceState.value || { trace_id: String(payload.trace_id || '') };
            traceState.value = {
              ...current,
              trace_id: String(payload.trace_id || current.trace_id || ''),
              skill_results: [
                ...(current.skill_results || []),
                { trace_id: payload.trace_id, skill: isRecord(payload.skill) ? payload.skill : {} },
              ],
            };
          } else if (event === 'final' && payload.assistant_message) {
            upsertMessage(payload.assistant_message as AiAgentMessage);
          } else if (event === 'error') {
            errorText.value = String(payload.message || 'Agent 执行失败');
            markAssistantFailed(localAssistantKey, errorText.value);
          } else {
            appendAssistantContent(localAssistantKey, streamDeltaContent(payload));
          }
        }
      }
      markAssistantCompleted(localAssistantKey);
      await loadConversations();
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        markAssistantFailed(localAssistantKey, '已停止生成');
      } else {
        errorText.value = error instanceof Error ? error.message : String(error);
        markAssistantFailed(localAssistantKey, errorText.value);
      }
    } finally {
      sending.value = false;
      abortController = null;
      await nextTick();
    }
  }

  function stop() {
    abortController?.abort();
  }

  function isRecord(value: unknown): value is Record<string, unknown> {
    return !!value && typeof value === 'object' && !Array.isArray(value);
  }

  function replaceLocalMessageKey(oldKey: string, newKey: string) {
    messages.value = messages.value.map((item) => (item.message_key === oldKey ? { ...item, message_key: newKey } : item));
  }

  function appendAssistantContent(messageKey: string, delta: string) {
    if (!delta) return;
    const key = streamMeta.assistant_message_key || messageKey;
    messages.value = messages.value.map((item) =>
      item.message_key === key || item.message_key === messageKey
        ? { ...item, message_key: key, content: `${item.content || ''}${delta}`, status: 'streaming' }
        : item
    );
  }

  function markAssistantCompleted(messageKey: string) {
    const key = streamMeta.assistant_message_key || messageKey;
    messages.value = messages.value.map((item) =>
      item.message_key === key || item.message_key === messageKey ? { ...item, message_key: key, status: 'completed' } : item
    );
  }

  function markAssistantFailed(messageKey: string, reason: string) {
    const key = streamMeta.assistant_message_key || messageKey;
    messages.value = messages.value.map((item) =>
      item.message_key === key || item.message_key === messageKey
        ? { ...item, message_key: key, status: 'failed', error_message: reason }
        : item
    );
  }

  function upsertMessage(message: AiAgentMessage) {
    const index = messages.value.findIndex((item) => item.message_key === message.message_key);
    if (index >= 0) {
      messages.value.splice(index, 1, message);
    } else {
      messages.value.push(message);
    }
  }

  watch(activeConversationKey, (value) => {
    if (value) void loadMessages(value);
  });

  return {
    conversations,
    messages,
    activeConversationKey,
    activeConversation,
    loadingConversations,
    loadingMessages,
    sending,
    errorText,
    traceState,
    loadConversations,
    createConversation,
    resetConversation,
    selectConversation,
    loadMessages,
    send,
    stop,
  };
}
