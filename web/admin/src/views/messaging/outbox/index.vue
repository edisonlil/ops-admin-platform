<template>
  <ListPageRuntime :schema="outboxPage" :rows="rows" :loading="loading" @refresh="reload" />
</template>

<script lang="ts" setup>
  import { h, ref } from 'vue';
  import type { DataTableColumns } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { getMessagingMessages, type MessageIntent } from '@/api/messaging';

  const loading = ref(false);
  const rows = ref<MessageIntent[]>([]);

  const columns: DataTableColumns<MessageIntent> = [
    { title: 'ID', key: 'id', width: 80 },
    { title: '标题', key: 'title', minWidth: 260 },
    { title: '类型', key: 'message_type', width: 120 },
    { title: '优先级', key: 'priority', width: 110 },
    {
      title: '状态',
      key: 'status',
      width: 120,
      render(row) {
        return h(AppStatusTag, {
          tone: row.status === 'dispatched' ? 'success' : row.status === 'failed' ? 'error' : 'info',
          label: row.status,
        });
      },
    },
    { title: '发送人', key: 'sender_name', width: 140 },
    { title: '创建时间', key: 'create_time', width: 190, render: (row) => formatToDateTime(row.create_time) },
  ];

  const outboxPage = defineListPage<MessageIntent>({
    id: 'messaging.outbox',
    title: '发送记录',
    description: '查看租户消息发送记录和投递状态，保留可追溯的消息台账。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => Number(row.id),
      scrollX: 1020,
      tableProps: { size: 'small' },
    },
    toolbar: {
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  async function reload() {
    loading.value = true;
    try {
      const payload = await getMessagingMessages({ page: 1, page_size: 50 });
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>
