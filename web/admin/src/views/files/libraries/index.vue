<template>
  <div class="file-library-page">
    <ListPageRuntime :schema="libraryPage" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload">
      <template #filters>
        <n-input v-model:value="keyword" clearable placeholder="搜索文件库名称" class="file-library-page__filter" @keyup.enter="reload" />
        <n-select v-model:value="statusFilter" clearable placeholder="状态" :options="statusOptions" class="file-library-page__status" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="560">
      <n-drawer-content :title="form.id ? '编辑文件库' : '新建文件库'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-form-item label="名称" path="name">
            <n-input v-model:value="form.name" placeholder="例如：合同归档" />
          </n-form-item>
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="类型" path="library_type">
              <n-input v-model:value="form.library_type" placeholder="general" />
            </n-form-item-gi>
            <n-form-item-gi label="状态" path="status">
              <n-select v-model:value="form.status" :options="statusOptions" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="说明">
            <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存文件库</n-button>
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
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deleteFileLibrary,
    getFileLibraries,
    saveFileLibrary,
    type FileLibrary,
  } from '@/api/fileManagement';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<FileLibrary[]>([]);
  const paginationTotal = ref(0);
  const keyword = ref('');
  const statusFilter = ref<string | null>(null);

  const form = reactive<Partial<FileLibrary>>({
    name: '',
    description: '',
    library_type: 'general',
    visibility: 'tenant',
    status: 'active',
  });

  const statusOptions: SelectOption[] = [
    { label: '启用', value: 'active' },
    { label: '停用', value: 'disabled' },
  ];

  const rules: FormRules = {
    name: [{ required: true, message: '请输入文件库名称', trigger: ['blur', 'input'] }],
  };

  const columns: DataTableColumns<FileLibrary> = [
    { title: '文件库', key: 'name', minWidth: 180 },
    { title: '类型', key: 'library_type', width: 140 },
    {
      title: '状态',
      key: 'status',
      width: 110,
      render(row) {
        return h(AppStatusTag, {
          tone: row.status === 'active' ? 'success' : 'neutral',
          label: row.status === 'active' ? '启用' : '停用',
        });
      },
    },
    { title: '说明', key: 'description', minWidth: 260, ellipsis: { tooltip: true } },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['file:library:manage']), onClick: () => openEdit(row) },
            { label: '删除', tone: 'danger', show: hasPermission(['file:library:manage']), onClick: () => remove(row) },
          ],
        });
      },
    },
  ];

  const libraryPage = defineListPage<FileLibrary>({
    id: 'files.libraries',
    title: '文件库',
    description: '按租户维护业务文件分组，文件库会作为文件树的根节点。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1040,
      sort: { remote: true },
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: hasPermission(['file:library:manage'])
        ? { key: 'create', label: '新建文件库', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function resetForm() {
    Object.assign(form, {
      id: undefined,
      name: '',
      description: '',
      library_type: 'general',
      visibility: 'tenant',
      status: 'active',
    });
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: FileLibrary) {
    Object.assign(form, row);
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
      await saveFileLibrary(form);
      message.success('文件库已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function remove(row: FileLibrary) {
    await deleteFileLibrary(row.id);
    message.success('文件库已删除');
    await reload();
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const payload = await getFileLibraries(runtimeListParams(state));
      rows.value = payload.items || [];
      paginationTotal.value = payload.pagination?.total || rows.value.length;
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>

<style lang="less" scoped>
  .file-library-page {
    min-width: 0;
  }

  .file-library-page__filter {
    width: min(320px, 100%);
  }

  .file-library-page__status {
    width: 160px;
  }
</style>
