<template>
  <AppPage :density="schema.density" :variant="schema.variant">
    <AppPageHeader :title="schema.title" :description="schema.description">
      <template v-if="$slots.actions || schema.actions?.length" #actions>
        <slot name="actions"></slot>
        <n-button
          v-for="action in schema.actions || []"
          :key="action.key"
          :type="action.type || 'default'"
          :disabled="action.disabled"
          :loading="action.loading"
          @click="handleAction(action)"
        >
          {{ action.label }}
        </n-button>
      </template>
    </AppPageHeader>

    <section class="app-detail-runtime" :class="`app-detail-runtime--${schema.kind}`">
      <slot></slot>
    </section>
  </AppPage>
</template>

<script lang="ts" setup generic="T extends Record<string, unknown>">
  import { computed } from 'vue';
  import AppPage from '../components/AppPage.vue';
  import AppPageHeader from '../components/AppPageHeader.vue';
  import type { DetailPageSchema, PageAction, PageRuntimeContext } from '../types';

  const props = defineProps<{
    schema: DetailPageSchema<T>;
  }>();

  const context = computed<PageRuntimeContext>(() => ({
    pageId: props.schema.id,
    density: props.schema.density || 'comfortable',
    variant: props.schema.variant || 'enterprise',
  }));

  function handleAction(action: PageAction) {
    return action.onClick?.(context.value);
  }
</script>

<style lang="less" scoped>
  .app-detail-runtime {
    display: grid;
    gap: var(--app-page-detail-section-gap);
    min-width: 0;
  }
</style>
