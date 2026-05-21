<template>
  <div>
    <ListPageRuntime :schema="inboxPage" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload" />

    <n-drawer v-model:show="detailVisible" :width="720" placement="right">
      <n-drawer-content :title="activeMessage?.title || '消息详情'">
        <div v-if="activeMessage" class="message-detail">
          <div class="message-detail__meta">
            <AppStatusTag :tone="activeMessage.read_status === 'unread' ? 'warning' : 'success'" :label="activeMessage.read_status" />
            <AppStatusTag tone="info" :label="activeMessage.message_type" />
            <AppStatusTag tone="neutral" :label="activeMessage.priority" />
          </div>
          <n-divider />
          <div class="message-detail__content">{{ activeMessage.content }}</div>
          <n-divider />
          <n-descriptions :column="1" size="small" bordered>
            <n-descriptions-item label="消息 ID">{{ activeMessage.message_id }}</n-descriptions-item>
            <n-descriptions-item label="发送时间">{{ formatToDateTime(activeMessage.create_time) }}</n-descriptions-item>
            <n-descriptions-item label="阅读时间">{{ activeMessage.read_time ? formatToDateTime(activeMessage.read_time) : '-' }}</n-descriptions-item>
          </n-descriptions>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { h, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { usePermission } from '@/hooks/web/usePermission';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    getMessagingInbox,
    markAllMessagingRead,
    markMessagingRead,
    type MessageRecipient,
  } from '@/api/messaging';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const rows = ref<MessageRecipient[]>([]);
  const paginationTotal = ref(0);
  const detailVisible = ref(false);
  const activeMessage = ref<MessageRecipient | null>(null);

  const columns: DataTableColumns<MessageRecipient> = [
    {
      title: '状态',
      key: 'read_status',
      width: 96,
      render(row) {
        return h(AppStatusTag, {
          tone: row.read_status === 'unread' ? 'warning' : 'success',
          label: row.read_status === 'unread' ? '未读' : '已读',
        });
      },
    },
    { title: '标题', key: 'title', minWidth: 240 },
    { title: '类型', key: 'message_type', width: 120 },
    { title: '优先级', key: 'priority', width: 110 },
    { title: '接收时间', key: 'create_time', width: 190, render: (row) => formatToDateTime(row.create_time) },
    {
      title: '操作',
      key: 'actions',
      width: 170,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '查看', onClick: () => openMessage(row) },
            {
              label: '标为已读',
              show: hasPermission(['messaging:inbox:manage_self']),
              disabled: row.read_status !== 'unread',
              onClick: () => markRead(row),
            },
          ],
        });
      },
    },
  ];

  const inboxPage = defineListPage<MessageRecipient>({
    id: 'messaging.inbox',
    title: '站内信',
    description: '查看平台消息、处理未读通知，并保留关键运营消息上下文。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => Number(row.id),
      scrollX: 960,
      sort: { remote: true },
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: hasPermission(['messaging:inbox:manage_self'])
        ? { key: 'read-all', label: '全部已读', type: 'default', onClick: markAllRead }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const payload = await getMessagingInbox(runtimeListParams(state));
      rows.value = payload.items || [];
      paginationTotal.value = payload.pagination?.total || rows.value.length;
    } finally {
      loading.value = false;
    }
  }

  async function openMessage(row: MessageRecipient) {
    activeMessage.value = row;
    detailVisible.value = true;
    if (row.read_status === 'unread' && hasPermission(['messaging:inbox:manage_self'])) {
      await markRead(row, false);
    }
  }

  async function markRead(row: MessageRecipient, showToast = true) {
    const payload = await markMessagingRead(row.id);
    const index = rows.value.findIndex((item) => item.id === row.id);
    if (index >= 0) rows.value[index] = payload.item;
    if (activeMessage.value?.id === row.id) activeMessage.value = payload.item;
    if (showToast) message.success('已标记为已读');
  }

  async function markAllRead() {
    const payload = await markAllMessagingRead();
    message.success(`已标记 ${payload.updated} 条消息`);
    await reload();
  }

  reload();
</script>

<style lang="less" scoped>
  .message-detail {
    display: grid;
    gap: 12px;
  }

  .message-detail__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .message-detail__content {
    white-space: pre-wrap;
    line-height: 1.7;
    color: var(--app-text-color);
  }
</style>
