<template>
  <div>
    <ListPageRuntime :schema="apiKeyListPage" :rows="rows" :loading="loading" @refresh="reload" />

    <n-modal v-model:show="showCreate" preset="dialog" title="新增 API Key" positive-text="创建" @positive-click="create">
      <n-input v-model:value="newKeyName" placeholder="API Key 名称" />
    </n-modal>

    <n-modal v-model:show="createdVisible" preset="card" title="API Key 已创建" style="width: 620px">
      <n-alert type="warning" class="mb-3">请立即保存密钥明文，关闭后将无法再次查看。</n-alert>
      <n-input :value="createdKey" readonly type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, ref } from 'vue';
  import { useRoute } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns } from 'naive-ui';
  import {
    createApiKey,
    createCurrentTenantApiKey,
    getApiKeys,
    getCurrentTenantApiKeys,
    revokeApiKey,
    revokeCurrentTenantApiKey,
  } from '@/api/business';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { usePermission } from '@/hooks/web/usePermission';
  import { useUserStore } from '@/store/modules/user';
  import { defineListPage, ListPageRuntime, runtimeSortParams, type ListRuntimeState } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const userStore = useUserStore();
  const route = useRoute();
  const loading = ref(false);
  const rows = ref<Recordable[]>([]);
  const showCreate = ref(false);
  const createdVisible = ref(false);
  const createdKey = ref('');
  const newKeyName = ref('');
  const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);
  const usePlatformApiKeys = computed(() => isPlatformAdmin.value && String(route.name || '') !== 'tenant-api-keys');
  const canCreate = computed(() => hasPermission([usePlatformApiKeys.value ? 'api_keys:create' : 'tenant:api_keys:create']));
  const canRevoke = computed(() => hasPermission([usePlatformApiKeys.value ? 'api_keys:revoke' : 'tenant:api_keys:revoke']));

  const columns: DataTableColumns<Recordable> = [
    { title: 'ID', key: 'id', width: 80 },
    { title: '名称', key: 'name', minWidth: 180 },
    { title: '前缀', key: 'prefix', width: 140 },
    {
      title: '状态',
      key: 'is_active',
      width: 100,
      render(row) {
        return h(AppStatusTag, { statusKey: row.is_active ? 'valid' : 'revoked' });
      },
    },
    { title: '创建人', key: 'created_by', width: 120 },
    { title: '创建时间', key: 'create_time', width: 220, render: (row) => formatToDateTime(row.create_time) },
    {
      title: '操作',
      key: 'actions',
      width: 110,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            {
              label: '吊销',
              tone: 'danger',
              show: canRevoke.value,
              disabled: !row.is_active,
              confirm: true,
              confirmTitle: '吊销 API Key',
              confirmContent: `确认吊销 API Key「${row.name || row.prefix}」？`,
              onConfirm: () => revoke(row),
            },
          ],
        });
      },
    },
  ];

  const apiKeyListPage = defineListPage<Recordable>({
    id: 'settings.api-keys',
    title: 'API Key',
    description: '管理用于外部集成和自动化访问的 API Key。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => Number(row.id),
      scrollX: 1000,
      selectionColumn: {
        fixed: 'left',
      },
      columnRuntime: {
        minWidth: 80,
      },
      sort: { remote: true },
      tableLayout: {
        headerHeight: 44,
        minRowHeight: 48,
        rowHeight: 48,
      },
      tableProps: {
        size: 'small',
      },
    },
    toolbar: {
      primaryAction: canCreate.value
        ? {
            key: 'create',
            label: '新增 API Key',
            type: 'primary',
            onClick: () => {
              showCreate.value = true;
            },
          }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const params = runtimeSortParams(state);
      const payload = usePlatformApiKeys.value ? await getApiKeys(params) : await getCurrentTenantApiKeys(params);
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  async function create() {
    if (!newKeyName.value.trim()) {
      message.warning('请输入 API Key 名称');
      return false;
    }
    const payload = usePlatformApiKeys.value
      ? await createApiKey({ name: newKeyName.value.trim() })
      : await createCurrentTenantApiKey({ name: newKeyName.value.trim() });
    createdKey.value = payload.key;
    createdVisible.value = true;
    newKeyName.value = '';
    await reload();
    return true;
  }

  async function revoke(row: Recordable) {
    if (usePlatformApiKeys.value) await revokeApiKey(Number(row.id));
    else await revokeCurrentTenantApiKey(Number(row.id));
    message.success('API Key 已吊销');
    await reload();
  }

  reload();
</script>
