<template>
  <div class="file-object-page">
    <ListPageRuntime :schema="filePage" :rows="workspaceRows" :loading="loading" @refresh="reload">
      <template #filters>
        <n-select
          v-model:value="selectedLibraryId"
          clearable
          placeholder="选择文件库"
          :options="libraryOptions"
          class="file-object-page__library"
          @update:value="handleLibraryChange"
        />
        <n-input
          v-model:value="keyword"
          clearable
          placeholder="搜索当前租户文件"
          class="file-object-page__keyword"
          @keyup.enter="reload"
          @clear="reload"
        />
        <n-button @click="reload">查询</n-button>
      </template>

      <template #toolbar-left>
        <n-button
          v-if="hasPermission(['file:library:manage'])"
          :disabled="!currentLibrary"
          @click="openFolderDrawer"
        >
          <template #icon>
            <n-icon><FolderAddOutlined /></n-icon>
          </template>
          新建目录
        </n-button>
        <n-button
          v-if="hasPermission(['file:object:upload'])"
          type="primary"
          :disabled="!currentLibrary"
          @click="openUpload"
        >
          <template #icon>
            <n-icon><UploadOutlined /></n-icon>
          </template>
          上传文件
        </n-button>
      </template>

      <template #toolbar-right>
        <n-button-group size="small">
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button :type="viewMode === 'grid' ? 'primary' : 'default'" @click="viewMode = 'grid'">
                <n-icon><AppstoreOutlined /></n-icon>
              </n-button>
            </template>
            图标展示
          </n-tooltip>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button :type="viewMode === 'list' ? 'primary' : 'default'" @click="viewMode = 'list'">
                <n-icon><UnorderedListOutlined /></n-icon>
              </n-button>
            </template>
            列表展示
          </n-tooltip>
        </n-button-group>
      </template>

      <template #collection>
        <section class="file-browser">
          <header class="file-browser__header">
            <div class="file-browser__title-area">
              <div class="file-browser__title-row">
                <n-button quaternary circle size="small" :disabled="!currentFolder" @click="goUp">
                  <template #icon>
                    <n-icon><ArrowLeftOutlined /></n-icon>
                  </template>
                </n-button>
                <h2>{{ currentLibrary?.name || '文件库' }}</h2>
                <n-button quaternary circle size="small" @click="reload">
                  <template #icon>
                    <n-icon><ReloadOutlined /></n-icon>
                  </template>
                </n-button>
              </div>
              <n-breadcrumb class="file-browser__breadcrumb">
                <n-breadcrumb-item v-if="currentLibrary" @click="openLibraryRoot(currentLibrary.id)">
                  {{ currentLibrary.name }}
                </n-breadcrumb-item>
                <n-breadcrumb-item
                  v-for="item in breadcrumbs"
                  :key="item.id"
                  @click="openFolder(item)"
                >
                  {{ item.name }}
                </n-breadcrumb-item>
              </n-breadcrumb>
            </div>
            <div class="file-browser__meta">
              <span>{{ currentItems.length }} 个项目</span>
              <span>{{ formatBytes(usage?.used_bytes || 0) }} 已用</span>
            </div>
          </header>

          <div v-if="!currentLibrary" class="file-browser__empty">
            <n-empty description="还没有文件库，请先新建文件库" />
          </div>
          <div v-else-if="loading" class="file-browser__empty">
            <n-spin size="small" />
          </div>
          <div v-else-if="!currentItems.length" class="file-browser__empty">
            <n-empty description="当前目录为空" />
          </div>
          <div v-else-if="viewMode === 'grid'" class="file-browser__grid">
            <button
              v-for="item in currentItems"
              :key="item.key"
              class="file-tile"
              type="button"
              @dblclick="openItem(item)"
            >
              <span class="file-tile__icon" :class="`file-tile__icon--${item.kind}`">
                <n-icon size="54">
                  <FolderFilled v-if="item.kind === 'folder'" />
                  <FileTextFilled v-else />
                </n-icon>
              </span>
              <span class="file-tile__name" :title="item.name">{{ item.name }}</span>
              <span class="file-tile__meta">{{ item.kind === 'folder' ? '目录' : formatBytes(item.size_bytes || 0) }}</span>
              <span class="file-tile__actions">
                <n-button v-if="item.kind === 'file'" text size="tiny" @click.stop="download(item.file!)">下载</n-button>
                <n-button
                  v-if="item.kind === 'file' && hasPermission(['file:object:delete'])"
                  text
                  size="tiny"
                  type="error"
                  @click.stop="removeFile(item.file!)"
                >
                  删除
                </n-button>
              </span>
            </button>
          </div>
          <n-data-table
            v-else
            :columns="columns"
            :data="currentItems"
            :row-key="(row: WorkspaceItem) => row.key"
            size="small"
            :pagination="false"
          />
        </section>
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="folderDrawerVisible" width="420">
      <n-drawer-content title="新建目录">
        <n-form ref="folderFormRef" :model="folderForm" :rules="folderRules" label-placement="top">
          <n-form-item label="目录名称" path="name">
            <n-input v-model:value="folderForm.name" placeholder="例如：合同归档" />
          </n-form-item>
          <n-form-item label="说明">
            <n-input v-model:value="folderForm.description" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="folderDrawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="savingFolder" @click="submitFolder">保存</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-drawer v-model:show="uploadVisible" width="520">
      <n-drawer-content title="上传文件">
        <n-form label-placement="top">
          <n-form-item label="上传位置">
            <n-input :value="uploadLocationLabel" disabled />
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
  import { computed, h, reactive, ref } from 'vue';
  import { NButton, NIcon, NSpace, useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption, UploadFileInfo } from 'naive-ui';
  import {
    AppstoreOutlined,
    ArrowLeftOutlined,
    DownloadOutlined,
    FileTextFilled,
    FolderAddOutlined,
    FolderFilled,
    ReloadOutlined,
    UploadOutlined,
    UnorderedListOutlined,
  } from '@vicons/antd';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deleteManagedFile,
    downloadManagedFile,
    getFileWorkspace,
    saveFileFolder,
    uploadManagedFile,
    type FileFolder,
    type FileLibrary,
    type ManagedFile,
    type StorageUsage,
  } from '@/api/fileManagement';

  type ViewMode = 'grid' | 'list';
  type WorkspaceItemKind = 'folder' | 'file';

  interface WorkspaceItem {
    key: string;
    kind: WorkspaceItemKind;
    id: number;
    name: string;
    size_bytes?: number;
    update_time?: string;
    folder?: FileFolder;
    file?: ManagedFile;
  }

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const uploading = ref(false);
  const savingFolder = ref(false);
  const uploadVisible = ref(false);
  const folderDrawerVisible = ref(false);
  const viewMode = ref<ViewMode>('grid');
  const keyword = ref('');
  const selectedLibraryId = ref<number | null>(null);
  const selectedFolderId = ref<number | null>(null);
  const libraries = ref<FileLibrary[]>([]);
  const currentLibrary = ref<FileLibrary | null>(null);
  const currentFolder = ref<FileFolder | null>(null);
  const breadcrumbs = ref<FileFolder[]>([]);
  const folders = ref<FileFolder[]>([]);
  const files = ref<ManagedFile[]>([]);
  const usage = ref<StorageUsage | null>(null);
  const folderFormRef = ref<FormInst | null>(null);
  const workspaceRows = ref<WorkspaceItem[]>([]);

  const folderForm = reactive({
    name: '',
    description: '',
  });
  const uploadForm = reactive<{ file: File | null }>({
    file: null,
  });

  const folderRules: FormRules = {
    name: [{ required: true, message: '请输入目录名称', trigger: ['blur', 'input'] }],
  };

  const libraryOptions = computed<SelectOption[]>(() =>
    libraries.value.map((item) => ({ label: item.name, value: item.id }))
  );
  const currentItems = computed<WorkspaceItem[]>(() => [
    ...folders.value.map((item) => ({
      key: `folder-${item.id}`,
      kind: 'folder' as const,
      id: item.id,
      name: item.name,
      update_time: item.update_time,
      folder: item,
    })),
    ...files.value.map((item) => ({
      key: `file-${item.id}`,
      kind: 'file' as const,
      id: item.id,
      name: item.display_name || item.original_name,
      size_bytes: item.size_bytes,
      update_time: item.update_time,
      file: item,
    })),
  ]);
  const uploadLocationLabel = computed(() => {
    if (!currentLibrary.value) return '未选择文件库';
    const paths = [currentLibrary.value.name, ...breadcrumbs.value.map((item) => item.name)];
    return paths.join(' / ');
  });

  const columns: DataTableColumns<WorkspaceItem> = [
    {
      title: '名称',
      key: 'name',
      minWidth: 280,
      render(row) {
        return h(
          'button',
          {
            class: 'file-list-name',
            type: 'button',
            onDblclick: () => openItem(row),
          },
          [
            h(
              NIcon,
              { size: 24, class: row.kind === 'folder' ? 'file-list-name__folder' : 'file-list-name__file' },
              { default: () => h(row.kind === 'folder' ? FolderFilled : FileTextFilled) }
            ),
            h('span', row.name),
          ]
        );
      },
    },
    { title: '类型', key: 'kind', width: 120, render: (row) => (row.kind === 'folder' ? '目录' : '文件') },
    { title: '大小', key: 'size_bytes', width: 140, render: (row) => (row.kind === 'folder' ? '-' : formatBytes(row.size_bytes || 0)) },
    { title: '更新时间', key: 'update_time', width: 190, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 190,
      render(row) {
        if (row.kind === 'folder') {
          return h(NButton, { size: 'small', quaternary: true, onClick: () => openItem(row) }, { default: () => '打开' });
        }
        return h(
          NSpace,
          { size: 8 },
          {
            default: () => [
              h(
                NButton,
                { size: 'small', quaternary: true, onClick: () => download(row.file!) },
                { icon: () => h(NIcon, null, { default: () => h(DownloadOutlined) }), default: () => '下载' }
              ),
              hasPermission(['file:object:delete'])
                ? h(
                    NButton,
                    { size: 'small', quaternary: true, type: 'error', onClick: () => removeFile(row.file!) },
                    { default: () => '删除' }
                  )
                : null,
            ],
          }
        );
      },
    },
  ];

  const filePage = defineListPage<WorkspaceItem>({
    id: 'files.objects',
    title: '文件',
    description: '按文件库和目录管理租户文件，支持新建目录、上传、下载和视图切换。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.key,
      scrollX: 900,
      tableProps: { size: 'small' },
    },
    toolbar: {
      rightTools: ['refresh'],
    },
    pagination: false,
  });

  function handleLibraryChange(value: number | null) {
    selectedLibraryId.value = value;
    selectedFolderId.value = null;
    reload();
  }

  function openLibraryRoot(libraryId: number) {
    selectedLibraryId.value = libraryId;
    selectedFolderId.value = null;
    keyword.value = '';
    reload();
  }

  function openFolder(folder: FileFolder) {
    selectedLibraryId.value = folder.library_id;
    selectedFolderId.value = folder.id;
    keyword.value = '';
    reload();
  }

  function openItem(item: WorkspaceItem) {
    if (item.kind === 'folder' && item.folder) {
      openFolder(item.folder);
    }
  }

  function goUp() {
    const parent = breadcrumbs.value[breadcrumbs.value.length - 2];
    selectedFolderId.value = parent?.id || null;
    keyword.value = '';
    reload();
  }

  function openFolderDrawer() {
    folderForm.name = '';
    folderForm.description = '';
    folderFormRef.value?.restoreValidation();
    folderDrawerVisible.value = true;
  }

  async function submitFolder() {
    if (!currentLibrary.value) return;
    try {
      await folderFormRef.value?.validate();
    } catch {
      return;
    }
    savingFolder.value = true;
    try {
      await saveFileFolder({
        library_id: currentLibrary.value.id,
        parent_id: selectedFolderId.value,
        name: folderForm.name,
        description: folderForm.description,
      });
      message.success('目录已创建');
      folderDrawerVisible.value = false;
      await reload();
    } finally {
      savingFolder.value = false;
    }
  }

  function openUpload() {
    uploadForm.file = null;
    uploadVisible.value = true;
  }

  function handleUploadChange(options: { fileList: UploadFileInfo[] }) {
    uploadForm.file = (options.fileList[0]?.file as File | undefined) || null;
  }

  async function submitUpload() {
    if (!uploadForm.file || !currentLibrary.value) return;
    uploading.value = true;
    try {
      await uploadManagedFile({
        file: uploadForm.file,
        library_id: currentLibrary.value.id,
        folder_id: selectedFolderId.value,
      });
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

  async function removeFile(row: ManagedFile) {
    await deleteManagedFile(row.id);
    message.success('文件已删除');
    await reload();
  }

  async function reload() {
    loading.value = true;
    try {
      const payload = await getFileWorkspace({
        library_id: selectedLibraryId.value || undefined,
        folder_id: selectedFolderId.value || undefined,
        keyword: keyword.value.trim() || undefined,
      });
      libraries.value = payload.libraries || [];
      currentLibrary.value = payload.current_library || null;
      currentFolder.value = payload.current_folder || null;
      breadcrumbs.value = payload.breadcrumbs || [];
      folders.value = payload.folders || [];
      files.value = payload.files || [];
      usage.value = payload.usage || null;
      selectedLibraryId.value = currentLibrary.value?.id || null;
      selectedFolderId.value = currentFolder.value?.id || selectedFolderId.value || null;
      workspaceRows.value = currentItems.value;
    } finally {
      loading.value = false;
    }
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

  .file-object-page__library {
    width: 220px;
  }

  .file-object-page__keyword {
    width: min(320px, 100%);
  }

  .file-object-page__upload-text {
    padding: 24px 0;
    color: var(--app-text-color-2);
    text-align: center;
  }

  .file-browser {
    display: grid;
    gap: 18px;
    min-width: 0;
    padding: 4px 2px 10px;
  }

  .file-browser__header {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    justify-content: space-between;
    min-width: 0;
    padding: 0 4px 12px;
    border-bottom: 1px solid var(--app-border-color);
  }

  .file-browser__title-area {
    display: grid;
    gap: 8px;
    min-width: 0;
  }

  .file-browser__title-row {
    display: flex;
    gap: 8px;
    align-items: center;
    min-width: 0;
  }

  .file-browser__title-row h2 {
    margin: 0;
    overflow: hidden;
    color: var(--app-text-color);
    font-size: 22px;
    font-weight: 700;
    line-height: 1.3;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-browser__breadcrumb {
    min-width: 0;
  }

  .file-browser__meta {
    display: inline-flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;
    color: var(--app-text-color-2);
    font-size: 13px;
    white-space: nowrap;
  }

  .file-browser__empty {
    display: grid;
    min-height: 260px;
    place-items: center;
  }

  .file-browser__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
    gap: 22px 24px;
    align-items: start;
  }

  .file-tile {
    display: grid;
    gap: 8px;
    justify-items: center;
    min-width: 0;
    padding: 14px 10px 12px;
    color: var(--app-text-color);
    text-align: center;
    cursor: pointer;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
  }

  .file-tile:hover {
    background: var(--app-fill-color-lighter);
    border-color: var(--app-border-color);
  }

  .file-tile__icon {
    display: inline-grid;
    width: 72px;
    height: 64px;
    place-items: center;
  }

  .file-tile__icon--folder {
    color: #1677ff;
  }

  .file-tile__icon--file {
    color: #7c3aed;
  }

  .file-tile__name {
    display: -webkit-box;
    width: 100%;
    min-height: 42px;
    overflow: hidden;
    font-size: 14px;
    line-height: 1.5;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow-wrap: anywhere;
  }

  .file-tile__meta {
    min-height: 18px;
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  .file-tile__actions {
    display: inline-flex;
    gap: 8px;
    min-height: 22px;
  }

  :deep(.file-list-name) {
    display: inline-flex;
    gap: 10px;
    align-items: center;
    max-width: 100%;
    padding: 0;
    color: inherit;
    text-align: left;
    cursor: pointer;
    background: transparent;
    border: 0;
  }

  :deep(.file-list-name span:last-child) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :deep(.file-list-name__folder) {
    color: #1677ff;
  }

  :deep(.file-list-name__file) {
    color: #7c3aed;
  }

  @media (max-width: 760px) {
    .file-browser__header {
      flex-direction: column;
    }

    .file-browser__meta {
      justify-content: flex-start;
    }

    .file-browser__grid {
      grid-template-columns: repeat(auto-fill, minmax(124px, 1fr));
      gap: 16px;
    }
  }
</style>
