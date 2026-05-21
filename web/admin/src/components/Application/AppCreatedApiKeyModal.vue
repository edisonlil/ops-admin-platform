<template>
  <n-modal
    :show="show"
    preset="card"
    class="app-created-api-key-modal"
    :style="{ width: '620px', maxWidth: 'calc(100vw - 32px)' }"
    :bordered="false"
    @update:show="updateShow"
  >
    <template #header>
      <span class="app-created-api-key-modal__title">创建新的 API Key</span>
    </template>

    <div class="app-created-api-key-modal__body">
      <p class="app-created-api-key-modal__description">请复制并妥善保存此 API Key，请勿泄露给他人。</p>

      <div class="app-created-api-key-modal__key-row" :title="apiKey">
        <n-input :value="apiKey" readonly class="app-created-api-key-modal__input">
          <template #suffix>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button text type="primary" :aria-label="copyLabel" @click="copyApiKey">
                  <template #icon>
                    <n-icon><CopyOutlined /></n-icon>
                  </template>
                </n-button>
              </template>
              {{ copyLabel }}
            </n-tooltip>
          </template>
        </n-input>
      </div>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button type="primary" @click="close">确定</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useMessage } from 'naive-ui';
  import { CopyOutlined } from '@vicons/antd';

  const props = defineProps<{
    show: boolean;
    apiKey: string;
  }>();

  const emit = defineEmits<{
    (event: 'update:show', value: boolean): void;
  }>();

  const message = useMessage();
  const copyLabel = computed(() => (props.apiKey ? '复制 API Key' : '暂无可复制的 API Key'));

  function updateShow(value: boolean) {
    emit('update:show', value);
  }

  function close() {
    emit('update:show', false);
  }

  async function copyApiKey() {
    if (!props.apiKey) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(props.apiKey);
      } else {
        fallbackCopy(props.apiKey);
      }
      message.success('API Key 已复制');
    } catch {
      message.error('复制失败，请手动复制');
    }
  }

  function fallbackCopy(value: string) {
    const input = document.createElement('textarea');
    input.value = value;
    input.setAttribute('readonly', 'readonly');
    input.style.position = 'fixed';
    input.style.opacity = '0';
    input.style.pointerEvents = 'none';
    document.body.appendChild(input);
    input.select();
    document.execCommand('copy');
    document.body.removeChild(input);
  }
</script>

<style lang="less" scoped>
  .app-created-api-key-modal__title {
    color: var(--app-text-color, #1f2937);
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0;
    line-height: 1.4;
  }

  .app-created-api-key-modal__body {
    display: grid;
    gap: 16px;
  }

  .app-created-api-key-modal__description {
    margin: 0;
    color: var(--app-text-color, #1f2937);
    font-size: 14px;
    line-height: 1.6;
  }

  .app-created-api-key-modal__key-row {
    min-width: 0;
  }

  .app-created-api-key-modal__input {
    :deep(.n-input__input-el) {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
    }
  }

  @media (max-width: 640px) {
    .app-created-api-key-modal__body {
      gap: 14px;
    }
  }
</style>
