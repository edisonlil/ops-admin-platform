<template>
  <div class="storage-profile-page">
    <ListPageRuntime :schema="profilePage" :rows="rows" :loading="loading" @refresh="reload" />

    <n-drawer v-model:show="drawerVisible" width="680">
      <n-drawer-content :title="form.id ? '编辑对象存储' : '新增对象存储'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="存储类型" path="provider">
              <n-select v-model:value="form.provider" :options="providerOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="名称" path="name">
              <n-input v-model:value="form.name" placeholder="如：默认 MinIO" />
            </n-form-item-gi>
            <n-form-item-gi label="Endpoint" path="endpoint">
              <n-input v-model:value="form.endpoint" placeholder="http://localhost:9000" />
            </n-form-item-gi>
            <n-form-item-gi label="Bucket" path="bucket">
              <n-input v-model:value="form.bucket" placeholder="ops-files" />
            </n-form-item-gi>
            <n-form-item-gi label="Region">
              <n-input v-model:value="form.region" placeholder="可选" />
            </n-form-item-gi>
            <n-form-item-gi label="Access Key">
              <n-input v-model:value="form.access_key_id" />
            </n-form-item-gi>
            <n-form-item-gi label="Secret Key">
              <n-input v-model:value="form.secret_access_key" type="password" show-password-on="click" placeholder="编辑时留空表示不变" />
            </n-form-item-gi>
          </n-grid>
          <n-space class="storage-profile-page__toggles">
            <n-checkbox v-model:checked="form.path_style_enabled">Path style</n-checkbox>
            <n-checkbox v-model:checked="form.tls_enabled">启用 TLS</n-checkbox>
            <n-checkbox v-model:checked="form.enabled">启用配置</n-checkbox>
            <n-checkbox v-model:checked="form.is_default">设为默认</n-checkbox>
          </n-space>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存配置</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    getStorageProfiles,
    getStorageProviderOptions,
    saveStorageProfile,
    setDefaultStorageProfile,
    testStorageProfile,
    type StorageProfile,
    type StorageProfilePayload,
  } from '@/api/fileManagement';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<StorageProfile[]>([]);
  const providerOptions = ref<SelectOption[]>([{ label: 'MinIO', value: 'minio' }]);

  const form = reactive<StorageProfilePayload>({
    provider: 'minio',
    name: '',
    endpoint: '',
    region: '',
    bucket: '',
    access_key_id: '',
    secret_access_key: '',
    path_style_enabled: true,
    tls_enabled: true,
    is_default: true,
    enabled: true,
    extra_config: {},
  });

  const rules: FormRules = {
    provider: [{ required: true, message: '请选择存储类型', trigger: ['change'] }],
    name: [{ required: true, message: '请输入配置名称', trigger: ['blur', 'input'] }],
    endpoint: [{ required: true, message: '请输入 Endpoint', trigger: ['blur', 'input'] }],
    bucket: [{ required: true, message: '请输入 Bucket', trigger: ['blur', 'input'] }],
  };

  const columns: DataTableColumns<StorageProfile> = [
    { title: '名称', key: 'name', minWidth: 180 },
    { title: '类型', key: 'provider', width: 120 },
    { title: 'Endpoint', key: 'endpoint', minWidth: 220, ellipsis: { tooltip: true } },
    { title: 'Bucket', key: 'bucket', minWidth: 160 },
    {
      title: '默认',
      key: 'is_default',
      width: 100,
      render(row) {
        return h(AppStatusTag, { tone: row.is_default ? 'success' : 'neutral', label: row.is_default ? '默认' : '备用' });
      },
    },
    {
      title: '状态',
      key: 'enabled',
      width: 100,
      render(row) {
        return h(AppStatusTag, { tone: row.enabled ? 'success' : 'neutral', label: row.enabled ? '启用' : '停用' });
      },
    },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['file:storage_profiles:manage']), onClick: () => openEdit(row) },
            { label: '测试', show: hasPermission(['file:storage_profiles:manage']), onClick: () => testProfile(row) },
            { label: '设为默认', show: hasPermission(['file:storage_profiles:manage']) && !row.is_default, onClick: () => makeDefault(row) },
          ],
        });
      },
    },
  ];

  const profilePage = defineListPage<StorageProfile>({
    id: 'files.storage-profiles',
    title: '文件存储配置',
    description: '平台管理员配置租户文件使用的对象存储。第一版启用 MinIO，腾讯云 COS 和阿里云 OSS 作为扩展预留。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1240,
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: hasPermission(['file:storage_profiles:manage'])
        ? { key: 'create', label: '新增存储', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function resetForm() {
    Object.assign(form, {
      id: undefined,
      provider: 'minio',
      name: '',
      endpoint: '',
      region: '',
      bucket: '',
      access_key_id: '',
      secret_access_key: '',
      path_style_enabled: true,
      tls_enabled: true,
      is_default: !rows.value.length,
      enabled: true,
      extra_config: {},
    });
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: StorageProfile) {
    Object.assign(form, {
      ...row,
      secret_access_key: '',
      extra_config: row.extra_config || {},
    });
    drawerVisible.value = true;
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      await saveStorageProfile(form);
      message.success('存储配置已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function testProfile(row: StorageProfile) {
    const result = await testStorageProfile(row.id);
    if (result.ok) {
      message.success('连接测试通过');
    } else {
      message.warning(result.message || '连接测试未通过');
    }
  }

  async function makeDefault(row: StorageProfile) {
    await setDefaultStorageProfile(row.id);
    message.success('默认存储已更新');
    await reload();
  }

  async function reload() {
    loading.value = true;
    try {
      const [profilePayload, providerPayload] = await Promise.all([getStorageProfiles(), getStorageProviderOptions()]);
      rows.value = profilePayload.items || [];
      providerOptions.value = (providerPayload.items || []).map((item) => ({
        label: item.supported ? item.label : `${item.label}（预留）`,
        value: item.provider,
        disabled: !item.supported,
      }));
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>

<style lang="less" scoped>
  .storage-profile-page {
    min-width: 0;
  }

  .storage-profile-page__toggles {
    padding-top: 4px;
  }
</style>
