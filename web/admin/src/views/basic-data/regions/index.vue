<template>
  <div class="basic-data-region-page">
    <ListPageRuntime :schema="regionPage" :rows="regionRows" :loading="loadingTree" @refresh="reloadAll">
      <template #filters>
        <n-input v-model:value="keyword" clearable placeholder="搜索区域名称、简称或编码" class="basic-data-region-page__filter" @keyup.enter="reloadAll" />
        <n-select v-model:value="statusFilter" clearable placeholder="状态" :options="statusOptions" class="basic-data-region-page__status" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="formVisible" width="560">
      <n-drawer-content :title="regionForm.id ? '编辑区域' : '新建区域'">
        <n-form ref="formRef" :model="regionForm" :rules="regionRules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="上级区域">
              <n-tree-select v-model:value="regionForm.parent_id" clearable filterable :options="parentOptions" placeholder="省级区域不选择上级" />
            </n-form-item-gi>
            <n-form-item-gi label="层级" path="level">
              <n-select v-model:value="regionForm.level" :options="levelOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="编码" path="code">
              <n-input v-model:value="regionForm.code" placeholder="110000" />
            </n-form-item-gi>
            <n-form-item-gi label="名称" path="name">
              <n-input v-model:value="regionForm.name" placeholder="北京市" />
            </n-form-item-gi>
            <n-form-item-gi label="简称">
              <n-input v-model:value="regionForm.short_name" placeholder="北京" />
            </n-form-item-gi>
            <n-form-item-gi label="状态">
              <n-select v-model:value="regionForm.status" :options="statusOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="排序">
              <n-input-number v-model:value="regionForm.sort_order" class="basic-data-region-page__number" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="扩展 JSON">
            <n-input v-model:value="extraText" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" placeholder='{"alias":"京"}' />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="formVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submitRegion">保存区域</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-drawer v-model:show="importVisible" width="640">
      <n-drawer-content title="导入区域">
        <n-space vertical :size="16">
          <n-alert type="info" :show-icon="false">
            CSV 字段：code,parent_code,name,short_name,level,sort_order,status。level 支持省、省份、市、城市、区、区县、县；path 由系统生成。
          </n-alert>
          <n-upload :max="1" accept=".csv" :default-upload="false" @change="handleImportFileChange">
            <n-upload-dragger>
              <div class="basic-data-region-page__upload-title">选择 CSV 文件</div>
              <div class="basic-data-region-page__upload-subtitle">先校验，再确认导入</div>
            </n-upload-dragger>
          </n-upload>
          <n-space>
            <n-button :disabled="!importFile" :loading="importing" @click="previewImport">校验导入</n-button>
            <n-button type="primary" :disabled="!canConfirmImport" :loading="importing" @click="confirmImport">确认导入</n-button>
          </n-space>
          <n-descriptions v-if="importSummary" bordered size="small" :column="4">
            <n-descriptions-item label="新增">{{ importSummary.created_count }}</n-descriptions-item>
            <n-descriptions-item label="更新">{{ importSummary.updated_count }}</n-descriptions-item>
            <n-descriptions-item label="跳过">{{ importSummary.skipped_count }}</n-descriptions-item>
            <n-descriptions-item label="错误">{{ importSummary.error_count }}</n-descriptions-item>
          </n-descriptions>
          <n-alert v-if="importSummary?.errors?.length" type="error" title="错误">
            <div v-for="item in importSummary.errors" :key="`error-${item.row}-${item.message}`">
              第 {{ item.row || '-' }} 行：{{ item.message }}
            </div>
          </n-alert>
          <n-alert v-if="importSummary?.warnings?.length" type="warning" title="提示">
            <div v-for="item in importSummary.warnings" :key="`warning-${item.row}-${item.message}`">
              第 {{ item.row || '-' }} 行：{{ item.message }}
            </div>
          </n-alert>
        </n-space>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref, watch } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption, TreeOption, UploadFileInfo } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import {
    deleteRegion,
    getRegionTree,
    importRegions,
    saveRegion,
    type Region,
    type RegionImportSummary,
  } from '@/api/basicData';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loadingTree = ref(false);
  const saving = ref(false);
  const importing = ref(false);
  const formVisible = ref(false);
  const importVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const regionRows = ref<Region[]>([]);
  const selectedKeys = ref<Array<string | number>>([]);
  const activeRegion = ref<Region | null>(null);
  const keyword = ref('');
  const statusFilter = ref<string | null>(null);
  const extraText = ref('{}');
  const importFile = ref<File | null>(null);
  const importSummary = ref<RegionImportSummary | null>(null);

  const regionForm = reactive<Partial<Region>>({
    parent_id: null,
    code: '',
    name: '',
    short_name: '',
    level: 'province',
    status: 'active',
    sort_order: 0,
    extra: {},
  });

  const statusOptions: SelectOption[] = [
    { label: '启用', value: 'active' },
    { label: '停用', value: 'disabled' },
  ];
  const levelOptions: SelectOption[] = [
    { label: '省', value: 'province' },
    { label: '市', value: 'city' },
    { label: '区县', value: 'district' },
  ];
  const regionRules: FormRules = {
    code: [{ required: true, message: '请输入区域编码', trigger: ['blur', 'input'] }],
    name: [{ required: true, message: '请输入区域名称', trigger: ['blur', 'input'] }],
    level: [{ required: true, message: '请选择区域层级', trigger: ['blur', 'change'] }],
  };

  const flatRegions = computed(() => flattenRegions(regionRows.value));
  const filteredRows = computed(() => {
    const text = keyword.value.trim().toLowerCase();
    const status = statusFilter.value;
    return flatRegions.value.filter((item) => {
      if (status && item.status !== status) return false;
      if (!text) return true;
      return [item.code, item.name, item.short_name].some((value) => String(value || '').toLowerCase().includes(text));
    });
  });
  const treeOptions = computed<TreeOption[]>(() => buildTreeOptions(regionRows.value));
  const childRows = computed(() => {
    if (!activeRegion.value) return filteredRows.value.filter((item) => !item.parent_id);
    return filteredRows.value.filter((item) => item.parent_id === activeRegion.value?.id);
  });
  const parentOptions = computed<TreeOption[]>(() => buildTreeOptions(regionRows.value, Number(regionForm.id || 0)));
  const activeTitle = computed(() => activeRegion.value?.name || '省级区域');
  const activeDescription = computed(() => (activeRegion.value ? `${activeRegion.value.code} / ${levelLabel(activeRegion.value.level)}` : '查看和维护省、市、区三级区域'));
  const canConfirmImport = computed(() => Boolean(importFile.value && importSummary.value && importSummary.value.error_count === 0));

  const columns: DataTableColumns<Region> = [
    { title: '编码', key: 'code', width: 140 },
    { title: '名称', key: 'name', minWidth: 160 },
    { title: '简称', key: 'short_name', minWidth: 120 },
    { title: '层级', key: 'level', width: 90, render: (row) => levelLabel(row.level) },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render(row) {
        return h(AppStatusTag, {
          tone: row.status === 'active' ? 'success' : 'neutral',
          label: row.status === 'active' ? '启用' : '停用',
        });
      },
    },
    { title: '排序', key: 'sort_order', width: 90 },
    { title: '路径', key: 'path', minWidth: 220, ellipsis: { tooltip: true } },
    {
      title: '操作',
      key: 'actions',
      width: 170,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '新增下级', show: hasPermission(['basic-data:region:manage']) && row.level !== 'district', onClick: () => openCreateChild(row) },
            { label: '编辑', show: hasPermission(['basic-data:region:manage']), onClick: () => openEdit(row) },
            {
              label: '删除',
              tone: 'danger',
              show: hasPermission(['basic-data:region:manage']),
              confirm: true,
              confirmTitle: '删除区域',
              confirmContent: `确认删除“${row.name || row.code}”？下级区域也会同步删除。`,
              onConfirm: () => removeRegion(row),
            },
          ],
        });
      },
    },
  ];

  const regionPage = computed(() =>
    defineListPage<Region>({
      id: 'basic-data.regions',
      title: '区域管理',
      description: '维护省、市、区三级区域，供系统作为数据字典级联使用。',
      variant: 'dense-data',
      density: 'compact',
      view: {
        type: 'split-list',
        split: {
          masterWidth: 320,
          minHeight: 520,
          master: {
            title: '区域树',
            description: `${filteredRows.value.length} 个区域`,
            primaryAction: hasPermission(['basic-data:region:manage'])
              ? { key: 'create-root', label: '新建省级区域', type: 'primary', onClick: () => openCreateRoot() }
              : undefined,
            view: {
              type: 'tree',
              treeData: treeOptions.value,
              selectedKeys: selectedKeys.value,
              treeProps: { defaultExpandAll: true },
              onUpdateSelectedKeys: handleSelect,
            },
            pagination: false,
          },
          detail: {
            title: activeTitle.value,
            description: activeDescription.value,
            rows: childRows.value,
            loading: loadingTree.value,
            refresh: reloadAll,
            primaryAction:
              hasPermission(['basic-data:region:manage']) && (!activeRegion.value || activeRegion.value.level !== 'district')
                ? { key: 'create-child', label: activeRegion.value ? '新建下级区域' : '新建省级区域', type: 'primary', onClick: () => openCreateChild(activeRegion.value) }
                : undefined,
            actions: hasPermission(['basic-data:region:import'])
              ? [{ key: 'import', label: '导入', onClick: () => openImport() }]
              : [],
            view: {
              type: 'table',
              columns,
              rowKey: (row) => row.id,
              scrollX: 1120,
              tableProps: { size: 'small' },
              columnRuntime: { disabledFreezeKeys: ['actions'] },
            },
            pagination: { pageSize: 20 },
          },
        },
      },
      toolbar: { rightTools: ['refresh'] },
      pagination: false,
    })
  );

  watch([statusFilter], () => reloadAll());

  function resetForm() {
    Object.assign(regionForm, {
      id: undefined,
      parent_id: null,
      code: '',
      name: '',
      short_name: '',
      level: 'province',
      status: 'active',
      sort_order: 0,
      extra: {},
    });
    extraText.value = '{}';
    formRef.value?.restoreValidation();
  }

  function openCreateRoot() {
    resetForm();
    formVisible.value = true;
  }

  function openCreateChild(parent: Region | null) {
    resetForm();
    if (parent) {
      regionForm.parent_id = parent.id;
      regionForm.level = parent.level === 'province' ? 'city' : 'district';
    }
    formVisible.value = true;
  }

  function openEdit(row: Region) {
    Object.assign(regionForm, row);
    extraText.value = JSON.stringify(row.extra || {}, null, 2);
    formVisible.value = true;
  }

  async function submitRegion() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    const extra = parseExtra();
    if (!extra) return;
    saving.value = true;
    try {
      const saved = await saveRegion({ ...regionForm, extra });
      message.success('区域已保存');
      formVisible.value = false;
      await reloadAll(Number(saved.item?.id || regionForm.id || 0));
    } finally {
      saving.value = false;
    }
  }

  async function removeRegion(row: Region) {
    await deleteRegion(row.id);
    message.success('区域已删除');
    if (activeRegion.value?.id === row.id) {
      activeRegion.value = null;
      selectedKeys.value = [];
    }
    await reloadAll();
  }

  function openImport() {
    importFile.value = null;
    importSummary.value = null;
    importVisible.value = true;
  }

  function handleImportFileChange(options: { fileList: UploadFileInfo[] }) {
    importFile.value = (options.fileList[0]?.file as File | undefined) || null;
    importSummary.value = null;
  }

  async function previewImport() {
    if (!importFile.value) return;
    importing.value = true;
    try {
      importSummary.value = await importRegions(importFile.value, { dry_run: true });
    } finally {
      importing.value = false;
    }
  }

  async function confirmImport() {
    if (!importFile.value) return;
    importing.value = true;
    try {
      importSummary.value = await importRegions(importFile.value, { dry_run: false });
      message.success('区域导入完成');
      await reloadAll();
    } finally {
      importing.value = false;
    }
  }

  async function reloadAll(preferredId?: number) {
    loadingTree.value = true;
    try {
      const payload = await getRegionTree({ include_disabled: true });
      regionRows.value = payload.items || [];
      syncActive(preferredId);
    } finally {
      loadingTree.value = false;
    }
  }

  function syncActive(preferredId?: number) {
    const flat = flattenRegions(regionRows.value);
    const preferred = preferredId ? flat.find((item) => item.id === preferredId) : null;
    const existing = activeRegion.value ? flat.find((item) => item.id === activeRegion.value?.id) : null;
    const next = preferred || existing || null;
    activeRegion.value = next;
    selectedKeys.value = next ? [next.id] : [];
  }

  function handleSelect(keys: Array<string | number>) {
    const id = Number(keys[0] || 0);
    const row = flatRegions.value.find((item) => item.id === id) || null;
    activeRegion.value = row;
    selectedKeys.value = row ? [row.id] : [];
  }

  function flattenRegions(items: Region[]): Region[] {
    return items.flatMap((item) => [item, ...flattenRegions(item.children || [])]);
  }

  function buildTreeOptions(items: Region[], excludedId = 0): TreeOption[] {
    return items
      .filter((item) => item.id !== excludedId && !isDescendant(item, excludedId))
      .map((item) => ({
        key: item.id,
        label: `${item.name} ${item.code}`,
        children: item.children?.length ? buildTreeOptions(item.children, excludedId) : undefined,
      }));
  }

  function isDescendant(item: Region, ancestorId: number): boolean {
    if (!ancestorId) return false;
    return Boolean(item.children?.some((child) => child.id === ancestorId || isDescendant(child, ancestorId)));
  }

  function levelLabel(level?: string) {
    return levelOptions.find((item) => item.value === level)?.label || level || '-';
  }

  function parseExtra() {
    const text = extraText.value.trim();
    if (!text) return {};
    try {
      const parsed = JSON.parse(text);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        message.error('扩展 JSON 必须是对象');
        return null;
      }
      return parsed as Record<string, unknown>;
    } catch {
      message.error('扩展 JSON 格式不正确');
      return null;
    }
  }

  reloadAll();
</script>

<style lang="less" scoped>
  .basic-data-region-page {
    min-width: 0;
  }

  .basic-data-region-page__filter {
    width: min(320px, 100%);
  }

  .basic-data-region-page__status {
    width: 160px;
  }

  .basic-data-region-page__number {
    width: 100%;
  }

  .basic-data-region-page__upload-title {
    font-size: 14px;
    font-weight: 600;
  }

  .basic-data-region-page__upload-subtitle {
    margin-top: 4px;
    color: var(--app-text-color-3, #64748b);
    font-size: 12px;
  }
</style>
