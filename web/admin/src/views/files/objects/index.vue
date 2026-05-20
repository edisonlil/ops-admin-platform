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
        <div v-if="selectedFile || selectedFolder" class="file-object-page__selection-tools">
          <n-checkbox :checked="true" @update:checked="clearSelectedFile" />
          <span class="file-object-page__selected-name" :title="selectedResourceName">
            {{ selectedResourceName }}
          </span>
          <n-popover
            v-model:show="tagPopoverVisible"
            trigger="click"
            placement="bottom"
            :width="360"
            content-class="file-tag-popover"
          >
            <template #trigger>
              <n-button size="small">
                <template #icon>
                  <n-icon><PlusOutlined /></n-icon>
                </template>
                标签
              </n-button>
            </template>
            <div class="file-tag-picker">
              <header class="file-tag-picker__header">
                <strong>所有标签</strong>
                <n-button quaternary circle size="small" @click="focusTagInput">
                  <template #icon>
                    <n-icon><PlusOutlined /></n-icon>
                  </template>
                </n-button>
              </header>
              <n-dynamic-tags
                ref="tagInputRef"
                v-model:value="selectedFileTagDraft"
                size="small"
                round
                :max="12"
              />
              <n-empty v-if="!selectedFileTagDraft.length" size="small" description="还没有标签" />
              <footer class="file-tag-picker__footer">
                <n-button size="small" @click="tagPopoverVisible = false">取消</n-button>
                <n-button size="small" type="primary" :loading="savingMetadata" @click="saveSelectedFileTags">保存</n-button>
              </footer>
            </div>
          </n-popover>
          <n-button v-if="selectedFile" size="small" secondary @click="openMetadataDrawer(selectedFile)">元数据</n-button>
        </div>
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
              <span>{{ displayItems.length }} 个项目</span>
              <span>{{ formatBytes(currentUsage?.used_bytes || 0) }} 已用</span>
            </div>
          </header>

          <div v-if="!currentLibrary" class="file-browser__empty">
            <n-empty description="还没有文件库，请先新建文件库" />
          </div>
          <div v-else-if="loading" class="file-browser__empty">
            <n-spin size="small" />
          </div>
          <div v-else-if="!displayItems.length" class="file-browser__empty">
            <n-empty description="当前目录为空" />
          </div>
          <div v-else-if="viewMode === 'grid'" class="file-browser__grid">
            <button
              v-for="item in displayItems"
              :key="item.key"
              class="file-tile"
              :class="{ 'file-tile--selected': isSelectedItem(item) }"
              type="button"
              @click="selectItem(item)"
              @dblclick="openItem(item)"
            >
              <span class="file-tile__icon" :class="`file-tile__icon--${item.kind}`">
                <n-icon size="42">
                  <FolderFilled v-if="item.kind === 'folder'" />
                  <FileTextFilled v-else />
                </n-icon>
              </span>
              <span class="file-tile__name" :title="item.name">{{ item.name }}</span>
              <span v-if="itemTags(item).length" class="file-tag-strip">
                <span v-for="tag in itemTags(item).slice(0, 3)" :key="tag" class="file-tag-chip">{{ tag }}</span>
              </span>
              <span class="file-tile__meta">{{ formatBytes(item.size_bytes || 0) }}</span>
              <span class="file-tile__actions">
                <n-button v-if="item.kind === 'file'" text size="tiny" @click.stop="preview(item.file!)">预览</n-button>
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
            :columns="listColumns"
            :data="displayItems"
            :row-key="(row: WorkspaceItem) => row.key"
            size="small"
            remote
            :max-height="fileBodyMaxHeight"
            :pagination="false"
            @update:sorter="handleListSorterUpdate"
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

    <n-drawer v-model:show="metadataDrawerVisible" width="520">
      <n-drawer-content :title="metadataDrawerTitle">
        <n-form label-placement="top">
          <n-form-item label="标签">
            <n-dynamic-tags v-model:value="metadataForm.tag_codes" round />
          </n-form-item>
          <n-form-item label="元数据">
            <div class="metadata-editor">
              <div v-for="(row, index) in metadataRows" :key="row.id" class="metadata-editor__row">
                <n-input v-model:value="row.key" placeholder="字段名" />
                <n-input v-model:value="row.value" placeholder="字段值" />
                <n-button quaternary circle type="error" @click="removeMetadataRow(index)">×</n-button>
              </div>
              <n-button size="small" secondary @click="addMetadataRow">
                <template #icon>
                  <n-icon><PlusOutlined /></n-icon>
                </template>
                添加字段
              </n-button>
            </div>
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="metadataDrawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="savingMetadata" @click="submitMetadata">保存</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-drawer v-model:show="previewVisible" :width="previewDrawerWidth" @after-leave="clearPreview">
      <n-drawer-content :title="previewTitle">
        <div class="file-preview">
          <div v-if="previewLoading" class="file-preview__state">
            <n-spin size="small" />
          </div>
          <n-empty v-else-if="previewError" :description="previewError" class="file-preview__state">
            <template #extra>
              <n-button v-if="previewFile" size="small" @click="download(previewFile)">下载</n-button>
            </template>
          </n-empty>
          <img
            v-else-if="previewMode === 'image' && previewBlobUrl"
            class="file-preview__image"
            :src="previewBlobUrl"
            :alt="previewTitle"
          />
          <iframe
            v-else-if="previewMode === 'pdf' && previewBlobUrl"
            class="file-preview__frame"
            :src="previewBlobUrl"
            title="文件预览"
          />
          <iframe
            v-else-if="previewMode === 'external' && previewExternalUrl"
            class="file-preview__frame"
            :src="previewExternalUrl"
            title="文件预览"
          />
          <div v-else-if="isMarkdownPreview" class="file-preview__markdown" v-html="markdownHtml"></div>
          <pre v-else-if="previewMode === 'text'" class="file-preview__text">{{ previewText }}</pre>
          <audio
            v-else-if="previewMode === 'audio' && previewBlobUrl"
            class="file-preview__media"
            :src="previewBlobUrl"
            controls
          />
          <video
            v-else-if="previewMode === 'video' && previewBlobUrl"
            class="file-preview__video"
            :src="previewBlobUrl"
            controls
          />
          <n-empty v-else description="暂不支持预览" class="file-preview__state">
            <template #extra>
              <n-button v-if="previewFile" size="small" @click="download(previewFile)">下载</n-button>
            </template>
          </n-empty>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, onBeforeUnmount, reactive, ref } from 'vue';
  import { NButton, NIcon, NSpace, useMessage } from 'naive-ui';
  import type { DataTableColumns, DataTableSortState, FormInst, FormRules, SelectOption, UploadFileInfo } from 'naive-ui';
  import MarkdownIt from 'markdown-it';
  import {
    AppstoreOutlined,
    ArrowLeftOutlined,
    DownloadOutlined,
    FileTextFilled,
    FolderAddOutlined,
    FolderFilled,
    PlusOutlined,
    ReloadOutlined,
    UploadOutlined,
    UnorderedListOutlined,
  } from '@vicons/antd';
  import { defineListPage, ListPageRuntime, runtimeSortParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deleteManagedFile,
    downloadManagedFile,
    fetchFilePreviewBlob,
    fetchFilePreviewText,
    getFilePreviewMetadata,
    getFileWorkspace,
    saveFileFolder,
    updateFileFolderMetadata,
    updateManagedFileMetadata,
    uploadManagedFile,
    type FilePreviewMode,
    type FileFolder,
    type FileLibrary,
    type ManagedFile,
    type StorageUsage,
  } from '@/api/fileManagement';

  type ViewMode = 'grid' | 'list';
  type WorkspaceItemKind = 'folder' | 'file';

  const markdownRenderer = new MarkdownIt({
    html: false,
    linkify: true,
    breaks: true,
  });

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

  type WorkspacePayloadItem =
    | (FileFolder & { kind: 'folder'; name: string })
    | (ManagedFile & { kind: 'file'; name: string });

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const uploading = ref(false);
  const savingFolder = ref(false);
  const uploadVisible = ref(false);
  const metadataDrawerVisible = ref(false);
  const tagPopoverVisible = ref(false);
  const folderDrawerVisible = ref(false);
  const previewVisible = ref(false);
  const previewLoading = ref(false);
  const previewError = ref('');
  const previewFile = ref<ManagedFile | null>(null);
  const previewMode = ref<FilePreviewMode>('unsupported');
  const previewText = ref('');
  const previewBlobUrl = ref('');
  const previewExternalUrl = ref('');
  const viewMode = ref<ViewMode>('grid');
  const fileBodyMaxHeight = 'calc(100vh - var(--app-header-height, 64px) - var(--app-tabs-height, 44px) - 290px)';
  const keyword = ref('');
  const selectedLibraryId = ref<number | null>(null);
  const selectedFolderId = ref<number | null>(null);
  const libraries = ref<FileLibrary[]>([]);
  const currentLibrary = ref<FileLibrary | null>(null);
  const currentFolder = ref<FileFolder | null>(null);
  const breadcrumbs = ref<FileFolder[]>([]);
  const folders = ref<FileFolder[]>([]);
  const files = ref<ManagedFile[]>([]);
  const currentUsage = ref<StorageUsage | null>(null);
  const folderFormRef = ref<FormInst | null>(null);
  const workspaceRows = ref<WorkspaceItem[]>([]);
  const listSortState = ref<ListRuntimeState>({});
  const selectedFile = ref<ManagedFile | null>(null);
  const selectedFolder = ref<FileFolder | null>(null);
  const selectedFileTagDraft = ref<string[]>([]);
  const savingMetadata = ref(false);
  const tagInputRef = ref<{ activate?: () => void } | null>(null);
  const metadataRows = ref<Array<{ id: number; key: string; value: string }>>([]);
  const metadataForm = reactive<{ file: ManagedFile | null; tag_codes: string[] }>({
    file: null,
    tag_codes: [],
  });
  let metadataRowSeq = 0;
  let workspaceReloadSeq = 0;

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
      size_bytes: item.size_bytes || 0,
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
  const displayItems = computed(() => (workspaceRows.value.length ? workspaceRows.value : currentItems.value));
  const uploadLocationLabel = computed(() => {
    if (!currentLibrary.value) return '未选择文件库';
    const paths = [currentLibrary.value.name, ...breadcrumbs.value.map((item) => item.name)];
    return paths.join(' / ');
  });
  const previewTitle = computed(() => previewFile.value?.display_name || previewFile.value?.original_name || '文件预览');
  const previewDrawerWidth = computed(() => (previewMode.value === 'text' ? 'min(760px, 100vw)' : 'min(980px, 100vw)'));
  const isMarkdownPreview = computed(() => previewMode.value === 'text' && isMarkdownFile(previewFile.value));
  const markdownHtml = computed(() => markdownRenderer.render(previewText.value || ''));
  const metadataDrawerTitle = computed(() => `编辑元数据：${metadataForm.file?.display_name || metadataForm.file?.original_name || ''}`);

  const selectedResourceName = computed(() => {
    if (selectedFile.value) return selectedFile.value.display_name || selectedFile.value.original_name;
    if (selectedFolder.value) return selectedFolder.value.name;
    return '';
  });

  const currentListSortField = computed(() => listSortState.value.sort?.sort_by || '');
  const currentListSortOrder = computed(() => {
    const direction = listSortState.value.sort?.sort_dir;
    return direction === 'asc' ? 'ascend' : direction === 'desc' ? 'descend' : false;
  });

  const baseColumns: DataTableColumns<WorkspaceItem> = [
    {
      title: '名称',
      key: 'name',
      minWidth: 280,
      sorter: true,
      render(row) {
        return h(
          'button',
          {
            class: 'file-list-name',
            type: 'button',
            onClick: () => selectItem(row),
            onDblclick: () => openItem(row),
          },
          [
            h(
              NIcon,
              { size: 24, class: row.kind === 'folder' ? 'file-list-name__folder' : 'file-list-name__file' },
              { default: () => h(row.kind === 'folder' ? FolderFilled : FileTextFilled) }
            ),
            h('span', row.name),
            itemTags(row).length
              ? h(
                  'span',
                  { class: 'file-list-name__tags' },
                  itemTags(row).slice(0, 3).map((tag) => h('span', { class: 'file-tag-chip' }, tag))
                )
              : null,
          ]
        );
      },
    },
    { title: '类型', key: 'kind', width: 120, render: (row) => (row.kind === 'folder' ? '目录' : '文件') },
    {
      title: '大小',
      key: 'size_bytes',
      width: 140,
      sorter: true,
      render: (row) => formatBytes(row.size_bytes || 0),
    },
    {
      title: '更新时间',
      key: 'update_time',
      width: 190,
      sorter: true,
      render: (row) => formatToDateTime(row.update_time || ''),
    },
    {
      title: '操作',
      key: 'actions',
      width: 240,
      render(row) {
        if (row.kind === 'folder') {
          return h(NButton, { size: 'small', text: true, onClick: () => openItem(row) }, { default: () => '打开' });
        }
        return h(
          NSpace,
          { size: 8, wrap: false, class: 'file-list-actions' },
          {
            default: () => [
              h(
                NButton,
                { size: 'small', text: true, onClick: () => preview(row.file!) },
                { default: () => '预览' }
              ),
              h(
                NButton,
                { size: 'small', text: true, onClick: () => download(row.file!) },
                { icon: () => h(NIcon, null, { default: () => h(DownloadOutlined) }), default: () => '下载' }
              ),
              hasPermission(['file:object:delete'])
                ? h(
                    NButton,
                    { size: 'small', text: true, type: 'error', onClick: () => removeFile(row.file!) },
                    { default: () => '删除' }
                  )
                : null,
            ],
          }
        );
      },
    },
  ];

  const listColumns = computed<DataTableColumns<WorkspaceItem>>(() =>
    baseColumns.map((column) => {
      if (!('key' in column)) return column;
      const sortField = column.key === 'name' ? 'display_name' : String(column.key);
      if (!['display_name', 'size_bytes', 'update_time'].includes(sortField)) return column;
      return {
        ...column,
        sortOrder: currentListSortField.value === sortField ? currentListSortOrder.value : false,
      };
    })
  );

  const filePage = defineListPage<WorkspaceItem>({
    id: 'files.objects',
    title: '文件',
    description: '按文件库和目录管理租户文件，支持新建目录、上传、下载和视图切换。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns: baseColumns,
      rowKey: (row) => row.key,
      scrollX: 900,
      sort: { remote: true },
      columnRuntime: {
        columns: [
          { key: 'name', label: 'name', sortable: true, sortField: 'display_name' },
          { key: 'kind', label: 'kind' },
          { key: 'size_bytes', label: 'size_bytes', sortable: true },
          { key: 'update_time', label: 'update_time', sortable: true },
          { key: 'actions', label: 'actions', required: true },
        ],
      },
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
      return;
    }
    if (item.kind === 'file' && item.file) {
      preview(item.file);
    }
  }

  function itemTags(item: WorkspaceItem) {
    return item.kind === 'folder' ? item.folder?.tag_codes || [] : item.file?.tag_codes || [];
  }

  function isSelectedItem(item: WorkspaceItem) {
    if (item.kind === 'folder') return selectedFolder.value?.id === item.folder?.id;
    return selectedFile.value?.id === item.file?.id;
  }

  function selectItem(item: WorkspaceItem) {
    if (item.kind === 'folder' && item.folder) {
      selectedFolder.value = item.folder;
      selectedFile.value = null;
      selectedFileTagDraft.value = [...(item.folder.tag_codes || [])];
      return;
    }
    if (item.kind === 'file' && item.file) {
      selectedFile.value = item.file;
      selectedFolder.value = null;
      selectedFileTagDraft.value = [...(item.file.tag_codes || [])];
    }
  }

  function clearSelectedFile(value: boolean) {
    if (value) return;
    selectedFile.value = null;
    selectedFolder.value = null;
    selectedFileTagDraft.value = [];
    tagPopoverVisible.value = false;
  }

  function focusTagInput() {
    tagInputRef.value?.activate?.();
  }

  async function saveSelectedFileTags() {
    if (!selectedFile.value && !selectedFolder.value) return;
    savingMetadata.value = true;
    try {
      if (selectedFolder.value) {
        const response = await updateFileFolderMetadata(selectedFolder.value.id, {
          metadata: selectedFolder.value.metadata || {},
          tag_codes: selectedFileTagDraft.value,
        });
        patchFolder(response.item);
        selectedFolder.value = response.item;
      } else if (selectedFile.value) {
        const response = await updateManagedFileMetadata(selectedFile.value.id, {
          metadata: selectedFile.value.metadata || {},
          tag_codes: selectedFileTagDraft.value,
        });
        patchFile(response.item);
        selectedFile.value = response.item;
      }
      tagPopoverVisible.value = false;
      message.success('标签已保存');
    } finally {
      savingMetadata.value = false;
    }
  }

  function openMetadataDrawer(file: ManagedFile) {
    metadataForm.file = file;
    metadataForm.tag_codes = [...(file.tag_codes || [])];
    metadataRows.value = Object.entries(file.metadata || {}).map(([key, value]) => ({
      id: ++metadataRowSeq,
      key,
      value: value == null ? '' : String(value),
    }));
    metadataDrawerVisible.value = true;
  }

  function addMetadataRow() {
    metadataRows.value.push({ id: ++metadataRowSeq, key: '', value: '' });
  }

  function removeMetadataRow(index: number) {
    metadataRows.value.splice(index, 1);
  }

  async function submitMetadata() {
    if (!metadataForm.file) return;
    const metadata: Record<string, unknown> = {};
    metadataRows.value.forEach((row) => {
      const key = row.key.trim();
      if (!key) return;
      metadata[key] = parseMetadataValue(row.value);
    });
    savingMetadata.value = true;
    try {
      const response = await updateManagedFileMetadata(metadataForm.file.id, {
        metadata,
        tag_codes: metadataForm.tag_codes,
      });
      patchFile(response.item);
      selectedFile.value = response.item;
      selectedFileTagDraft.value = [...(response.item.tag_codes || [])];
      metadataDrawerVisible.value = false;
      message.success('元数据已保存');
    } finally {
      savingMetadata.value = false;
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

  function patchFile(file: ManagedFile) {
    const replace = (item: ManagedFile) => (item.id === file.id ? file : item);
    files.value = files.value.map(replace);
    workspaceRows.value = workspaceRows.value.map((row) =>
      row.kind === 'file' && row.file?.id === file.id
        ? {
            ...row,
            name: file.display_name || file.original_name,
            file,
          }
        : row
    );
  }

  function patchFolder(folder: FileFolder) {
    const replace = (item: FileFolder) => (item.id === folder.id ? { ...item, ...folder } : item);
    folders.value = folders.value.map(replace);
    breadcrumbs.value = breadcrumbs.value.map(replace);
    if (currentFolder.value?.id === folder.id) {
      currentFolder.value = { ...currentFolder.value, ...folder };
    }
    workspaceRows.value = workspaceRows.value.map((row) =>
      row.kind === 'folder' && row.folder?.id === folder.id
        ? {
            ...row,
            name: folder.name,
            folder: { ...row.folder, ...folder },
          }
        : row
    );
  }

  function parseMetadataValue(value: string) {
    const text = value.trim();
    if (text === 'true') return true;
    if (text === 'false') return false;
    if (text && !Number.isNaN(Number(text))) return Number(text);
    return value;
  }

  async function download(row: ManagedFile) {
    await downloadManagedFile(row);
  }

  async function preview(row: ManagedFile) {
    revokePreviewBlob();
    previewFile.value = row;
    previewMode.value = 'unsupported';
    previewText.value = '';
    previewExternalUrl.value = '';
    previewError.value = '';
    previewVisible.value = true;
    previewLoading.value = true;
    try {
      const { preview: metadata } = await getFilePreviewMetadata(row.id);
      previewMode.value = metadata.mode;
      if (!metadata.previewable) {
        previewError.value = previewUnsupportedText(metadata.reason);
        return;
      }
      if (metadata.mode === 'text') {
        previewText.value = await fetchFilePreviewText(row.id);
        return;
      }
      if (metadata.mode === 'external') {
        previewExternalUrl.value = metadata.url;
        return;
      }
      const blob = await fetchFilePreviewBlob(row.id);
      previewBlobUrl.value = URL.createObjectURL(blob);
    } catch (error) {
      previewError.value = error instanceof Error ? error.message : '预览失败';
    } finally {
      previewLoading.value = false;
    }
  }

  function clearPreview() {
    revokePreviewBlob();
    previewLoading.value = false;
    previewError.value = '';
    previewText.value = '';
    previewExternalUrl.value = '';
    previewFile.value = null;
    previewMode.value = 'unsupported';
  }

  function revokePreviewBlob() {
    if (previewBlobUrl.value) {
      URL.revokeObjectURL(previewBlobUrl.value);
      previewBlobUrl.value = '';
    }
  }

  function previewUnsupportedText(reason: string) {
    if (reason === 'text_file_too_large') return '文本文件过大，请下载后查看';
    return '该文件类型暂不支持在线预览';
  }

  function isMarkdownFile(file: ManagedFile | null) {
    const extension = String(file?.extension || '').toLowerCase();
    const mimeType = String(file?.mime_type || '').toLowerCase();
    return extension === 'md' || extension === 'markdown' || mimeType === 'text/markdown';
  }

  async function removeFile(row: ManagedFile) {
    await deleteManagedFile(row.id);
    message.success('文件已删除');
    await reload();
  }

  async function reload(state?: ListRuntimeState | Event) {
    const nextState = isListRuntimeState(state) ? state : listSortState.value;
    if (isListRuntimeState(state)) {
      listSortState.value = state;
    }
    const reloadSeq = ++workspaceReloadSeq;
    loading.value = true;
    try {
      const payload = await getFileWorkspace({
        library_id: selectedLibraryId.value || undefined,
        folder_id: selectedFolderId.value || undefined,
        keyword: keyword.value.trim() || undefined,
        ...runtimeSortParams(nextState),
      });
      if (reloadSeq !== workspaceReloadSeq) return;
      libraries.value = payload.libraries || [];
      currentLibrary.value = payload.current_library || null;
      currentFolder.value = payload.current_folder || null;
      breadcrumbs.value = payload.breadcrumbs || [];
      folders.value = payload.folders || [];
      files.value = payload.files || [];
      workspaceRows.value = (payload.items?.length ? payload.items.map(mapWorkspacePayloadItem) : currentItems.value);
      if (selectedFile.value) {
        selectedFile.value = files.value.find((item) => item.id === selectedFile.value?.id) || null;
        selectedFileTagDraft.value = [...(selectedFile.value?.tag_codes || [])];
      }
      if (selectedFolder.value) {
        selectedFolder.value =
          folders.value.find((item) => item.id === selectedFolder.value?.id) ||
          breadcrumbs.value.find((item) => item.id === selectedFolder.value?.id) ||
          (currentFolder.value?.id === selectedFolder.value.id ? currentFolder.value : null);
        selectedFileTagDraft.value = [...(selectedFolder.value?.tag_codes || [])];
      }
      currentUsage.value = payload.current_usage || payload.usage || null;
      selectedLibraryId.value = currentLibrary.value?.id || null;
      selectedFolderId.value = currentFolder.value?.id || selectedFolderId.value || null;
    } finally {
      if (reloadSeq === workspaceReloadSeq) {
        loading.value = false;
      }
    }
  }

  function formatBytes(value: number) {
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
    return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
  }

  function handleListSorterUpdate(sorter: DataTableSortState | DataTableSortState[] | null) {
    const state = Array.isArray(sorter) ? sorter[0] : sorter;
    if (!state || state.columnKey === undefined) {
      reload({ sort: {} });
      return;
    }
    const sortBy = state.columnKey === 'name' ? 'display_name' : String(state.columnKey);
    const sortDir = resolveNextSortDir(sortBy, state.order);
    if (!sortDir) {
      reload({ sort: {} });
      return;
    }
    reload({
      sort: {
        sort_by: sortBy,
        sort_dir: sortDir,
      },
    });
  }

  function resolveNextSortDir(sortBy: string, emittedOrder: DataTableSortState['order']) {
    if (emittedOrder === 'ascend') return 'asc';
    if (emittedOrder === 'descend') return 'desc';
    if (currentListSortField.value !== sortBy) return 'asc';
    if (listSortState.value.sort?.sort_dir === 'asc') return 'desc';
    if (listSortState.value.sort?.sort_dir === 'desc') return undefined;
    return 'asc';
  }

  function isListRuntimeState(value: unknown): value is ListRuntimeState {
    if (!value || typeof value !== 'object') return false;
    return 'sort' in value || 'pagination' in value;
  }

  function mapWorkspacePayloadItem(item: WorkspacePayloadItem): WorkspaceItem {
    if (item.kind === 'folder') {
      return {
        key: `folder-${item.id}`,
        kind: 'folder',
        id: item.id,
        name: item.name,
        size_bytes: item.size_bytes || 0,
        update_time: item.update_time,
        folder: item,
      };
    }
    return {
      key: `file-${item.id}`,
      kind: 'file',
      id: item.id,
      name: item.display_name || item.original_name || item.name,
      size_bytes: item.size_bytes,
      update_time: item.update_time,
      file: item,
    };
  }

  reload();
  onBeforeUnmount(revokePreviewBlob);
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

  .file-object-page__selection-tools {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    max-width: min(560px, 100%);
    height: 32px;
    padding: 0 8px;
    background: var(--app-fill-color-lighter);
    border: 1px solid var(--app-border-color);
    border-radius: 6px;
  }

  .file-object-page__selected-name {
    max-width: 220px;
    overflow: hidden;
    color: var(--app-text-color);
    font-size: 13px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-tag-picker {
    display: grid;
    gap: 12px;
    min-width: 0;
  }

  .file-tag-picker__header,
  .file-tag-picker__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .file-tag-picker__header strong {
    color: var(--app-text-color);
    font-size: 15px;
  }

  .file-tag-picker__footer {
    justify-content: flex-end;
    padding-top: 4px;
  }

  .metadata-editor {
    display: grid;
    gap: 10px;
    width: 100%;
  }

  .metadata-editor__row {
    display: grid;
    grid-template-columns: minmax(110px, 0.55fr) minmax(150px, 1fr) 32px;
    gap: 8px;
    align-items: center;
  }

  .file-tag-strip,
  :deep(.file-list-name__tags) {
    display: inline-flex;
    gap: 4px;
    min-width: 0;
  }

  .file-tag-chip {
    display: inline-flex;
    align-items: center;
    max-width: 72px;
    height: 20px;
    padding: 0 7px;
    overflow: hidden;
    color: #1d4ed8;
    font-size: 12px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 999px;
  }

  .file-browser {
    --file-browser-title-size: var(--app-font-size-lg, 16px);
    --file-browser-body-max-height: calc(100vh - var(--app-header-height, 64px) - var(--app-tabs-height, 44px) - 290px);

    display: grid;
    gap: 12px;
    min-width: 0;
    padding: 2px 2px 8px;
  }

  .file-browser__header {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    justify-content: space-between;
    min-width: 0;
    padding: 0 4px 8px;
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
    font-size: var(--file-browser-title-size);
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
    grid-template-columns: repeat(auto-fill, 112px);
    gap: 12px 16px;
    align-items: start;
    justify-content: start;
    max-height: max(260px, var(--file-browser-body-max-height));
    overflow: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .file-tile {
    display: grid;
    gap: 5px;
    justify-items: center;
    min-width: 0;
    width: 112px;
    min-height: 118px;
    padding: 8px 6px 6px;
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

  .file-tile--selected {
    background: #eaf2ff;
    border-color: #9ec5ff;
  }

  .file-tile__icon {
    display: inline-grid;
    width: 52px;
    height: 44px;
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
    min-height: 36px;
    overflow: hidden;
    font-size: 13px;
    line-height: 1.38;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow-wrap: anywhere;
  }

  .file-tile .file-tag-strip {
    width: 100%;
    justify-content: center;
    min-height: 20px;
    overflow: hidden;
  }

  .file-tile__meta {
    min-height: 16px;
    color: var(--app-text-color-2);
    font-size: 12px;
  }

  .file-tile__actions {
    display: inline-flex;
    gap: 8px;
    min-height: 0;
  }

  .file-tile__actions:empty {
    display: none;
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

  :deep(.file-list-name__tags) {
    max-width: 230px;
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

  :deep(.file-list-actions) {
    flex-wrap: nowrap;
    align-items: center;
    white-space: nowrap;
  }

  :deep(.file-list-actions .n-button) {
    --n-padding: 0;
  }

  .file-preview {
    display: grid;
    min-height: min(680px, calc(100vh - 170px));
  }

  .file-preview__state {
    display: grid;
    min-height: 360px;
    place-items: center;
  }

  .file-preview__image {
    display: block;
    max-width: 100%;
    max-height: min(680px, calc(100vh - 180px));
    margin: auto;
    object-fit: contain;
  }

  .file-preview__frame {
    width: 100%;
    height: min(720px, calc(100vh - 170px));
    background: var(--app-fill-color-lighter);
    border: 1px solid var(--app-border-color);
    border-radius: 6px;
  }

  .file-preview__text {
    max-height: min(680px, calc(100vh - 170px));
    min-height: 360px;
    padding: 14px;
    overflow: auto;
    color: var(--app-text-color);
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    background: var(--app-fill-color-lighter);
    border: 1px solid var(--app-border-color);
    border-radius: 6px;
  }

  :deep(.file-preview__markdown) {
    max-height: min(680px, calc(100vh - 170px));
    min-height: 360px;
    padding: 18px 22px;
    overflow: auto;
    color: var(--app-text-color);
    font-size: 14px;
    line-height: 1.75;
    background: var(--app-fill-color-lighter);
    border: 1px solid var(--app-border-color);
    border-radius: 6px;
  }

  :deep(.file-preview__markdown h1),
  :deep(.file-preview__markdown h2),
  :deep(.file-preview__markdown h3),
  :deep(.file-preview__markdown h4) {
    margin: 1.1em 0 0.55em;
    color: var(--app-text-color);
    font-weight: 700;
    line-height: 1.35;
  }

  :deep(.file-preview__markdown h1:first-child),
  :deep(.file-preview__markdown h2:first-child),
  :deep(.file-preview__markdown h3:first-child),
  :deep(.file-preview__markdown h4:first-child) {
    margin-top: 0;
  }

  :deep(.file-preview__markdown h1) {
    font-size: 24px;
  }

  :deep(.file-preview__markdown h2) {
    font-size: 20px;
  }

  :deep(.file-preview__markdown h3) {
    font-size: 17px;
  }

  :deep(.file-preview__markdown p),
  :deep(.file-preview__markdown ul),
  :deep(.file-preview__markdown ol),
  :deep(.file-preview__markdown blockquote),
  :deep(.file-preview__markdown pre) {
    margin: 0.7em 0;
  }

  :deep(.file-preview__markdown ul),
  :deep(.file-preview__markdown ol) {
    padding-left: 1.5em;
  }

  :deep(.file-preview__markdown code) {
    padding: 2px 5px;
    font-size: 13px;
    background: var(--app-fill-color);
    border-radius: 4px;
  }

  :deep(.file-preview__markdown pre) {
    padding: 12px;
    overflow: auto;
    background: var(--app-fill-color);
    border-radius: 6px;
  }

  :deep(.file-preview__markdown pre code) {
    padding: 0;
    background: transparent;
  }

  :deep(.file-preview__markdown blockquote) {
    padding-left: 12px;
    color: var(--app-text-color-2);
    border-left: 3px solid var(--app-border-color);
  }

  :deep(.file-preview__markdown table) {
    width: 100%;
    border-collapse: collapse;
  }

  :deep(.file-preview__markdown th),
  :deep(.file-preview__markdown td) {
    padding: 6px 8px;
    border: 1px solid var(--app-border-color);
  }

  .file-preview__media,
  .file-preview__video {
    align-self: center;
    width: 100%;
    max-height: min(680px, calc(100vh - 180px));
  }

  @media (max-width: 760px) {
    .file-browser__header {
      flex-direction: column;
    }

    .file-browser__meta {
      justify-content: flex-start;
    }

    .file-browser__grid {
      grid-template-columns: repeat(auto-fill, 104px);
      gap: 10px 12px;
    }

    .file-tile {
      width: 104px;
    }

    .metadata-editor__row {
      grid-template-columns: 1fr;
    }

    .file-preview,
    .file-preview__state {
      min-height: 320px;
    }
  }
</style>
