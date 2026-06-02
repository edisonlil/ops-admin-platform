<template>
  <div>
    <ListPageRuntime
      :schema="apiKeyListPage"
      :rows="rows"
      :loading="loading"
      :pagination-total="paginationTotal"
      @refresh="reload"
      @filter-reset="resetFilters"
    >
      <template #filters="{ submit }">
        <n-input v-model:value="filters.keyword" clearable placeholder="密钥名称 / 前缀 / 创建人" @keyup.enter="submit" />
        <n-select
          v-if="capabilities?.can_filter_owner"
          v-model:value="filters.owner_user_id"
          clearable
          filterable
          remote
          placeholder="所属人员"
          :options="ownerOptions"
          :loading="ownerOptionsLoading"
          @search="loadOwnerOptions"
          @focus="loadOwnerOptions()"
          @update:value="submit"
        />
        <n-select v-model:value="filters.is_active" clearable placeholder="状态" :options="activeOptions" @update:value="submit" />
      </template>
    </ListPageRuntime>

    <n-modal v-model:show="showCreate" preset="dialog" title="新增 API Key" positive-text="创建" @positive-click="create">
      <n-input v-model:value="newKeyName" placeholder="API Key 名称" />
    </n-modal>

    <n-modal v-model:show="editVisible" preset="dialog" title="编辑 API Key" positive-text="保存" @positive-click="saveEdit">
      <n-input v-model:value="editName" placeholder="API Key 名称" />
    </n-modal>

    <AppCreatedApiKeyModal v-model:show="createdVisible" :api-key="createdKey" />
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns } from 'naive-ui';
  import {
    createApiKey,
    createCurrentTenantApiKey,
    getApiKeyFilterCapabilities,
    getApiKeys,
    getCurrentTenantApiKeyFilterCapabilities,
    getCurrentTenantApiKeys,
    revokeApiKey,
    revokeCurrentTenantApiKey,
    updateApiKey,
    updateCurrentTenantApiKey,
  } from '@/api/business';
  import AppCreatedApiKeyModal from '@/components/Application/AppCreatedApiKeyModal.vue';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { usePermission } from '@/hooks/web/usePermission';
  import { useUserStore } from '@/store/modules/user';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const userStore = useUserStore();
  const route = useRoute();
  const loading = ref(false);
  const rows = ref<Recordable[]>([]);
  const paginationTotal = ref(0);
  const showCreate = ref(false);
  const editVisible = ref(false);
  const editName = ref('');
  const editingRow = ref<Recordable | null>(null);
  const createdVisible = ref(false);
  const createdKey = ref('');
  const newKeyName = ref('');
  const runtimeState = ref<ListRuntimeState>();
  const capabilities = ref<Recordable | null>(null);
  const ownerOptionsLoading = ref(false);
  const ownerOptions = ref<{ label: string; value: number }[]>([]);
  const filters = reactive({
    keyword: '',
    owner_user_id: null as number | null,
    is_active: null as boolean | null,
  });
  const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);
  const usePlatformApiKeys = computed(() => isPlatformAdmin.value && String(route.name || '') !== 'tenant-api-keys');
  const canCreate = computed(() => hasPermission([usePlatformApiKeys.value ? 'api_keys:create' : 'tenant:api_keys:create']));
  const canRevoke = computed(() => hasPermission([usePlatformApiKeys.value ? 'api_keys:revoke' : 'tenant:api_keys:revoke']));
  const activeOptions = [
    { label: '有效', value: true },
    { label: '已吊销', value: false },
  ];

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
    { title: '创建人', key: 'creator', width: 120 },
    { title: '创建时间', key: 'create_time', width: 220, render: (row) => formatToDateTime(row.create_time) },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: canCreate.value, disabled: !row.is_active, onClick: () => openEdit(row) },
            { label: '复制', onClick: () => copyApiKey(row) },
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
      scrollX: 1100,
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
    filterBar: {
      showSubmit: true,
      showReset: true,
    },
    pagination: { pageSize: 20 },
  });

  async function reload(state?: ListRuntimeState) {
    runtimeState.value = state || runtimeState.value;
    loading.value = true;
    try {
      await ensureCapabilities();
      const params = {
        ...runtimeListParams(runtimeState.value),
        ...filterParams(),
      };
      const payload = usePlatformApiKeys.value ? await getApiKeys(params) : await getCurrentTenantApiKeys(params);
      rows.value = payload.items || [];
      paginationTotal.value = payload.pagination?.total || rows.value.length;
    } finally {
      loading.value = false;
    }
  }

  async function ensureCapabilities() {
    if (capabilities.value) return;
    const payload = usePlatformApiKeys.value ? await getApiKeyFilterCapabilities({ page: 1, page_size: 100 }) : await getCurrentTenantApiKeyFilterCapabilities({ page: 1, page_size: 100 });
    capabilities.value = payload;
    ownerOptions.value = (payload.owner_options || []).map((item: Recordable) => ({ label: String(item.label || item.username || item.id), value: Number(item.value || item.id) }));
  }

  async function loadOwnerOptions(query = '') {
    if (!capabilities.value?.can_filter_owner) return;
    ownerOptionsLoading.value = true;
    try {
      const payload = usePlatformApiKeys.value
        ? await getApiKeyFilterCapabilities({ q: query || undefined, page: 1, page_size: 100 })
        : await getCurrentTenantApiKeyFilterCapabilities({ q: query || undefined, page: 1, page_size: 100 });
      ownerOptions.value = (payload.owner_options || []).map((item: Recordable) => ({ label: String(item.label || item.username || item.id), value: Number(item.value || item.id) }));
      capabilities.value = payload;
      if (!payload.can_filter_owner) filters.owner_user_id = null;
    } finally {
      ownerOptionsLoading.value = false;
    }
  }

  function filterParams() {
    const params: Record<string, string | number | boolean> = {};
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim();
    if (capabilities.value?.can_filter_owner && filters.owner_user_id) params.owner_user_id = filters.owner_user_id;
    if (filters.is_active !== null) params.is_active = filters.is_active;
    return params;
  }

  function resetFilters() {
    Object.assign(filters, { keyword: '', owner_user_id: null, is_active: null });
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

  function openEdit(row: Recordable) {
    editingRow.value = row;
    editName.value = String(row.name || '');
    editVisible.value = true;
  }

  async function saveEdit() {
    const name = editName.value.trim();
    if (!editingRow.value || !name) {
      message.warning('请输入 API Key 名称');
      return false;
    }
    const keyId = Number(editingRow.value.id);
    if (usePlatformApiKeys.value) await updateApiKey(keyId, { name });
    else await updateCurrentTenantApiKey(keyId, { name });
    editVisible.value = false;
    editingRow.value = null;
    editName.value = '';
    message.success('API Key 已保存');
    await reload();
    return true;
  }

  async function copyApiKey(row: Recordable) {
    const fullKey = String(row.key || '');
    if (fullKey) {
      await copyText(fullKey);
      message.success('API Key 已复制');
      return;
    }
    const prefix = String(row.prefix || '');
    if (!prefix) {
      message.warning('暂无可复制的 API Key');
      return;
    }
    await copyText(prefix);
    message.warning('仅复制了历史 Key 前缀，完整 Key 需重新创建后复制');
  }

  async function revoke(row: Recordable) {
    if (usePlatformApiKeys.value) await revokeApiKey(Number(row.id));
    else await revokeCurrentTenantApiKey(Number(row.id));
    message.success('API Key 已吊销');
    await reload();
  }

  async function copyText(value: string) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return;
    }
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

  watch(
    () => route.name,
    () => {
      capabilities.value = null;
      ownerOptions.value = [];
      Object.assign(filters, { keyword: '', owner_user_id: null, is_active: null });
      runtimeState.value = undefined;
      reload();
    }
  );

  reload();
</script>
