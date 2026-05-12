<template>
  <div class="file-object-page">
    <ListPageRuntime :schema="filePage" :rows="rows" :loading="loading" @refresh="reload">
      <template #filters>
        <n-input v-model:value="query.keyword" clearable placeholder="搜索文件名" class="file-object-page__keyword" @keyup.enter="reload" />
        <n-select
          v-model:value="query.library_id"
          clearable
          placeholder="文件库"
          :options="libraryOptions"
          class="file-object-page__library"
        />
        <n-input v-model:value="query.mime_type" clearable placeholder="MIME 类型" class="file-object-page__mime" @keyup.enter="reload" />
        <n-button @click="reload">查询</n-button>
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="uploadVisible" width="520">
      <n-drawer-content title="上传文件">
        <n-form label-placement="top">
          <n-form-item label="归属文件库">
            <n-select v-model:value="uploadForm.library_id" clearable placeholder="不选择则归入默认文件空间" :options="libraryOptions" />
          </n-form-item>
          <n-form-item label="文件">
            <n-upload :default-upload="false" :max="1" @change="handleUploadChange">
              <n-upload-dragger>
                <div class="file-object-page__upload-text">点击或拖入文件</div>
              </n-upload-dragger>
            </n-upload>
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="uploadVisible = false">取消</n-button>
            <n-button type="primary" :loading="uploading" :disabled="!uploadForm.file" @click="submitUpload">上传</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, SelectOption, UploadFileInfo } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deleteManagedFile,
    downloadManagedFile,
    getFileLibraries,
    getFiles,
    reindexManagedFile,
    uploadManagedFile,
    type FileLibrary,
    type ManagedFile,
  } from '@/api/fileManagement';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const uploading = ref(false);
  const uploadVisible = ref(false);
  const rows = ref<ManagedFile[]>([]);
  const libraries = ref<FileLibrary[]>([]);
  const libraryOptions = ref<SelectOption[]>([]);
  const query = reactive<{ keyword: string; library_id: number | null; mime_type: string }>({
    keyword: '',
    library_id: null,
    mime_type: '',
  });
  const uploadForm = reactive<{ library_id: number | null; file: File | null }>({
    library_id: null,
    file: null,
  });

  const columns: DataTableColumns<ManagedFile> = [
    { title: '文件名', key: 'original_name', minWidth: 220, ellipsis: { tooltip: true } },
    { title: '文件库', key: 'library_id', width: 160, render: (row) => libraryName(row.library_id) },
    { title: '类型', key: 'mime_type', minWidth: 180 },
    { title: '大小', key: 'size_bytes', width: 110, render: (row) => formatBytes(row.size_bytes) },
    {
      title: '索引',
      key: 'indexed_at',
      width: 150,
      render(row) {
        return row.indexed_at
          ? h(AppStatusTag, { tone: 'success', label: '已索引' })
          : h(AppStatusTag, { tone: 'info', label: '待索引' });
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
            { label: '下载', show: hasPermission(['file:object:read']), onClick: () => download(row) },
            { label: '重建索引', show: hasPermission(['file:object:upload']), onClick: () => reindex(row) },
            { label: '删除', tone: 'danger', show: hasPermission(['file:object:delete']), onClick: () => remove(row) },
          ],
        });
      },
    },
  ];

  const filePage = defineListPage<ManagedFile>({
    id: 'files.objects',
    title: '文件',
    description: '上传、检索、下载和删除当前租户文件，检索接口已预留 Elasticsearch 接入边界。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1260,
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: hasPermission(['file:object:upload'])
        ? { key: 'upload', label: '上传文件', type: 'primary', onClick: () => openUpload() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function openUpload() {
    uploadForm.library_id = null;
    uploadForm.file = null;
    uploadVisible.value = true;
  }

  function handleUploadChange(options: { fileList: UploadFileInfo[] }) {
    uploadForm.file = (options.fileList[0]?.file as File | undefined) || null;
  }

  async function submitUpload() {
    if (!uploadForm.file) return;
    uploading.value = true;
    try {
      await uploadManagedFile({ file: uploadForm.file, library_id: uploadForm.library_id });
      message.success('文件已上传');
      uploadVisible.value = false;
      await reload();
    } finally {
      uploading.value = false;
    }
  }

  async function download(row: ManagedFile) {
    await downloadManagedFile(row);
  }

  async function reindex(row: ManagedFile) {
    await reindexManagedFile(row.id);
    message.success('索引任务已提交');
    await reload();
  }

  async function remove(row: ManagedFile) {
    await deleteManagedFile(row.id);
    message.success('文件已删除');
    await reload();
  }

  async function reloadLibraries() {
    const payload = await getFileLibraries({ page: 1, page_size: 100 });
    libraries.value = payload.items || [];
    libraryOptions.value = libraries.value.map((item) => ({ label: item.name, value: item.id }));
  }

  async function reload() {
    loading.value = true;
    try {
      await reloadLibraries();
      const payload = await getFiles({
        page: 1,
        page_size: 100,
        keyword: query.keyword.trim() || undefined,
        library_id: query.library_id || undefined,
        mime_type: query.mime_type.trim() || undefined,
      });
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  function libraryName(libraryId?: number | null) {
    if (!libraryId) return '-';
    return libraries.value.find((item) => item.id === libraryId)?.name || `#${libraryId}`;
  }

  function formatBytes(value: number) {
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
    return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
  }

  reload();
</script>

<style lang="less" scoped>
  .file-object-page {
    min-width: 0;
  }

  .file-object-page__keyword {
    width: min(300px, 100%);
  }

  .file-object-page__library,
  .file-object-page__mime {
    width: 200px;
  }

  .file-object-page__upload-text {
    padding: 24px 0;
    color: var(--app-text-color-2);
    text-align: center;
  }
</style>
