<template>
  <div class="preview-profile-page">
    <ListPageRuntime :schema="profilePage" :rows="rows" :loading="loading" @refresh="reload" />

    <n-drawer v-model:show="drawerVisible" width="720">
      <n-drawer-content :title="form.id ? '编辑预览配置' : '新增预览配置'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="预览服务" path="provider">
              <n-select v-model:value="form.provider" :options="providerOptions" @update:value="applyProviderDefaults" />
            </n-form-item-gi>
            <n-form-item-gi label="名称" path="name">
              <n-input v-model:value="form.name" placeholder="例如：默认 kkFileView" />
            </n-form-item-gi>
            <n-form-item-gi label="服务地址" path="base_url" :span="2">
              <n-input v-model:value="form.base_url" placeholder="http://localhost:8012" />
            </n-form-item-gi>
            <n-form-item-gi label="支持扩展名" :span="2">
              <n-input
                v-model:value="extensionsText"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 4 }"
                placeholder="doc, docx, xls, xlsx, ppt, pptx"
              />
            </n-form-item-gi>
            <n-form-item-gi label="源文件有效期（秒）">
              <n-input-number v-model:value="sourceUrlTtlSeconds" :min="60" :max="3600" :step="60" />
            </n-form-item-gi>
            <n-form-item-gi label="URL 参数名">
              <n-input v-model:value="urlParamName" placeholder="url" />
            </n-form-item-gi>
            <n-form-item-gi v-if="form.provider === 'custom'" label="预览路径" :span="2">
              <n-input v-model:value="previewPath" placeholder="/onlinePreview" />
            </n-form-item-gi>
          </n-grid>
          <n-space class="preview-profile-page__toggles">
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
    getPreviewProfiles,
    getPreviewProviderOptions,
    savePreviewProfile,
    setDefaultPreviewProfile,
    type PreviewProfile,
    type PreviewProfilePayload,
  } from '@/api/fileManagement';

  const defaultOfficeExtensions = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'];

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<PreviewProfile[]>([]);
  const providerOptions = ref<SelectOption[]>([{ label: 'kkFileView', value: 'kkfileview' }]);
  const extensionsText = ref(defaultOfficeExtensions.join(', '));
  const sourceUrlTtlSeconds = ref(300);
  const urlParamName = ref('url');
  const previewPath = ref('/onlinePreview');

  const form = reactive<PreviewProfilePayload>({
    provider: 'kkfileview',
    name: '',
    base_url: '',
    enabled: true,
    is_default: true,
    supported_extensions: defaultOfficeExtensions,
    config: {
      source_url_ttl_seconds: 300,
      url_param_name: 'url',
    },
  });

  const rules: FormRules = {
    provider: [{ required: true, message: '请选择预览服务', trigger: ['change'] }],
    name: [{ required: true, message: '请输入配置名称', trigger: ['blur', 'input'] }],
    base_url: [{ required: true, message: '请输入服务地址', trigger: ['blur', 'input'] }],
  };

  const columns: DataTableColumns<PreviewProfile> = [
    { title: '名称', key: 'name', minWidth: 180 },
    { title: '服务', key: 'provider', width: 130 },
    { title: '服务地址', key: 'base_url', minWidth: 240, ellipsis: { tooltip: true } },
    {
      title: '支持扩展名',
      key: 'supported_extensions',
      minWidth: 220,
      ellipsis: { tooltip: true },
      render: (row) => row.supported_extensions.join(', '),
    },
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
      width: 210,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['file:preview_profiles:manage']), onClick: () => openEdit(row) },
            {
              label: '设为默认',
              show: hasPermission(['file:preview_profiles:manage']) && row.enabled && !row.is_default,
              onClick: () => makeDefault(row),
            },
          ],
        });
      },
    },
  ];

  const profilePage = defineListPage<PreviewProfile>({
    id: 'files.preview-profiles',
    title: '文件预览配置',
    description: '平台管理员配置 Office 等非原生文件的外部预览服务。原生预览仍优先处理图片、PDF、文本、Markdown、音视频。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1280,
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: hasPermission(['file:preview_profiles:manage'])
        ? { key: 'create', label: '新增预览配置', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function resetForm() {
    Object.assign(form, {
      id: undefined,
      provider: 'kkfileview',
      name: '',
      base_url: '',
      enabled: true,
      is_default: !rows.value.length,
      supported_extensions: [...defaultOfficeExtensions],
      config: {
        source_url_ttl_seconds: 300,
        url_param_name: 'url',
      },
    });
    extensionsText.value = defaultOfficeExtensions.join(', ');
    sourceUrlTtlSeconds.value = 300;
    urlParamName.value = 'url';
    previewPath.value = '/onlinePreview';
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: PreviewProfile) {
    Object.assign(form, {
      ...row,
      config: row.config || {},
    });
    extensionsText.value = row.supported_extensions.join(', ');
    sourceUrlTtlSeconds.value = Number(row.config?.source_url_ttl_seconds || 300);
    urlParamName.value = String(row.config?.url_param_name || 'url');
    previewPath.value = String(row.config?.preview_path || '/onlinePreview');
    drawerVisible.value = true;
  }

  function applyProviderDefaults() {
    if (form.provider === 'kkfileview') {
      previewPath.value = '/onlinePreview';
    }
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      await savePreviewProfile(buildPayload());
      message.success('预览配置已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  function buildPayload(): PreviewProfilePayload {
    const config: Record<string, unknown> = {
      source_url_ttl_seconds: sourceUrlTtlSeconds.value || 300,
      url_param_name: urlParamName.value || 'url',
    };
    if (form.provider === 'custom') {
      config.preview_path = previewPath.value || '/onlinePreview';
    }
    return {
      ...form,
      base_url: String(form.base_url || '').trim().replace(/\/+$/, ''),
      supported_extensions: parseExtensions(extensionsText.value),
      config,
    };
  }

  function parseExtensions(value: string) {
    const items = value
      .split(/[\s,;，；]+/)
      .map((item) => item.trim().toLowerCase().replace(/^\./, ''))
      .filter(Boolean);
    return Array.from(new Set(items));
  }

  async function makeDefault(row: PreviewProfile) {
    await setDefaultPreviewProfile(row.id);
    message.success('默认预览配置已更新');
    await reload();
  }

  async function reload() {
    loading.value = true;
    try {
      const [profilePayload, providerPayload] = await Promise.all([getPreviewProfiles(), getPreviewProviderOptions()]);
      rows.value = profilePayload.items || [];
      providerOptions.value = (providerPayload.items || [])
        .filter((item) => item.provider !== 'native')
        .map((item) => ({
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
  .preview-profile-page {
    min-width: 0;
  }

  .preview-profile-page__toggles {
    padding-top: 4px;
  }
</style>
