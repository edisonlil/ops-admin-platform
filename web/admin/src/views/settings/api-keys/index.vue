<template>
  <div>
    <n-card :bordered="false" size="small" class="proCard">
      <template #header>API 密钥</template>
      <template #header-extra>
        <n-button type="primary" @click="showCreate = true">新建密钥</n-button>
      </template>

      <n-data-table
        size="small"
        :columns="columns"
        :data="rows"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
      />
    </n-card>

    <n-modal v-model:show="showCreate" preset="dialog" title="新建 API 密钥" positive-text="创建" @positive-click="create">
      <n-input v-model:value="newKeyName" placeholder="密钥名称" />
    </n-modal>

    <n-modal v-model:show="createdVisible" preset="card" title="密钥已创建" style="width: 620px">
      <n-alert type="warning" class="mb-3">密钥只会显示一次，请妥善保存。</n-alert>
      <n-input :value="createdKey" readonly type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, ref } from 'vue';
  import { useRoute } from 'vue-router';
  import { NButton, NTag, useMessage } from 'naive-ui';
  import type { DataTableColumns } from 'naive-ui';
  import {
    createApiKey,
    createCurrentTenantApiKey,
    getApiKeys,
    getCurrentTenantApiKeys,
    revokeApiKey,
    revokeCurrentTenantApiKey,
  } from '@/api/business';
  import { useUserStore } from '@/store/modules/user';
  import { formatToDateTime } from '@/utils/dateUtil';

  const message = useMessage();
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

  const columns: DataTableColumns<Recordable> = [
    { title: 'ID', key: 'id', width: 80 },
    { title: '名称', key: 'name', minWidth: 180 },
    { title: '前缀', key: 'prefix', width: 140 },
    {
      title: '状态',
      key: 'is_active',
      width: 100,
      render(row) {
        return h(NTag, { size: 'small', type: row.is_active ? 'success' : 'default' }, () =>
          row.is_active ? '有效' : '已撤销'
        );
      },
    },
    { title: '创建人', key: 'created_by', width: 120 },
    { title: '创建时间', key: 'created_at', width: 220, render: (row) => formatToDateTime(row.created_at) },
    {
      title: '操作',
      key: 'actions',
      width: 110,
      fixed: 'right',
      render(row) {
        return h(
          NButton,
          {
            size: 'small',
            type: 'error',
            secondary: true,
            disabled: !row.is_active,
            onClick: () => revoke(row),
          },
          () => '撤销'
        );
      },
    },
  ];

  async function reload() {
    loading.value = true;
    try {
      const payload = usePlatformApiKeys.value ? await getApiKeys() : await getCurrentTenantApiKeys();
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  async function create() {
    if (!newKeyName.value.trim()) {
      message.warning('请输入密钥名称');
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
    message.success('密钥已撤销');
    await reload();
  }

  reload();
</script>
