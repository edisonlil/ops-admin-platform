<template>
  <div class="dataset-page">
    <ListPageRuntime :schema="datasetPage" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload">
      <template #filters>
        <n-input v-model:value="keyword" clearable placeholder="搜索数据集名称或编码" class="dataset-page__filter" @keyup.enter="reload()" />
        <n-select v-model:value="typeFilter" clearable placeholder="数据集类型" :options="typeOptions" class="dataset-page__select" @update:value="reload()" />
        <n-select v-model:value="statusFilter" clearable placeholder="状态" :options="statusOptions" class="dataset-page__select" @update:value="reload()" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="datasetDrawerVisible" width="560">
      <n-drawer-content :title="form.id ? '编辑数据集' : '新建数据集'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-form-item label="数据集名称" path="name">
            <n-input v-model:value="form.name" placeholder="例如：每日销售" />
          </n-form-item>
          <n-form-item label="数据集编码" path="key">
            <n-input v-model:value="form.key" placeholder="例如：sales_daily" />
          </n-form-item>
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="类型" path="dataset_type">
              <n-select v-model:value="form.dataset_type" :options="typeOptions" />
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
            <n-button @click="datasetDrawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submitDataset">保存</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-modal v-model:show="schemaModalVisible" preset="card" title="字段配置" class="dataset-page__modal">
      <n-alert type="info" :bordered="false" class="dataset-page__alert">每行一个字段对象，字段编码会作为预览数据中的列键。</n-alert>
      <n-input v-model:value="fieldJson" type="textarea" :autosize="{ minRows: 14, maxRows: 22 }" />
      <template #footer>
        <n-space justify="end">
          <n-button @click="schemaModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="submitFields">保存字段</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="rowsModalVisible" preset="card" title="手工数据" class="dataset-page__modal">
      <n-alert type="info" :bordered="false" class="dataset-page__alert">请输入 JSON 数组。首期手工数据用于仪表盘联调和静态数据集预览。</n-alert>
      <n-input v-model:value="rowsJson" type="textarea" :autosize="{ minRows: 14, maxRows: 22 }" />
      <template #footer>
        <n-space justify="end">
          <n-button @click="rowsModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="submitRows">保存数据</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="previewModalVisible" preset="card" title="数据预览" class="dataset-page__preview">
      <n-data-table :columns="previewColumns" :data="previewRows" :loading="previewLoading" :pagination="false" size="small" />
      <div class="dataset-page__preview-footer">
        <span>共 {{ previewTotal }} 行</span>
        <n-pagination v-model:page="previewPage" :page-size="10" :item-count="previewTotal" @update:page="loadPreview" />
      </div>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deleteDataset,
    getDataset,
    listDatasets,
    previewDataset,
    publishDataset,
    saveDataset,
    saveDatasetFields,
    saveDatasetRows,
    type Dataset,
    type DatasetField,
  } from '@/api/datasets';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const datasetDrawerVisible = ref(false);
  const schemaModalVisible = ref(false);
  const rowsModalVisible = ref(false);
  const previewModalVisible = ref(false);
  const previewLoading = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<Dataset[]>([]);
  const paginationTotal = ref(0);
  const keyword = ref('');
  const typeFilter = ref<string | null>(null);
  const statusFilter = ref<string | null>(null);
  const activeDataset = ref<Dataset | null>(null);
  const fieldJson = ref('');
  const rowsJson = ref('');
  const previewRows = ref<Record<string, unknown>[]>([]);
  const previewFields = ref<DatasetField[]>([]);
  const previewTotal = ref(0);
  const previewPage = ref(1);

  const form = reactive<Partial<Dataset>>({
    key: '',
    name: '',
    description: '',
    dataset_type: 'manual',
    status: 'draft',
    visibility: 'tenant',
  });

  const typeOptions: SelectOption[] = [
    { label: '手工数据', value: 'manual' },
    { label: '数据源查询', value: 'source_query' },
    { label: '外部接口契约', value: 'api_contract' },
  ];

  const statusOptions: SelectOption[] = [
    { label: '草稿', value: 'draft' },
    { label: '启用', value: 'active' },
    { label: '停用', value: 'disabled' },
  ];

  const rules: FormRules = {
    name: [{ required: true, message: '请输入数据集名称', trigger: ['blur', 'input'] }],
    key: [{ required: true, message: '请输入数据集编码', trigger: ['blur', 'input'] }],
  };

  const columns: DataTableColumns<Dataset> = [
    { title: '数据集名称', key: 'name', minWidth: 180, ellipsis: { tooltip: true } },
    { title: '编码', key: 'key', minWidth: 160, ellipsis: { tooltip: true } },
    { title: '类型', key: 'dataset_type', width: 130, render: (row) => typeLabel(row.dataset_type) },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render(row) {
        return h(AppStatusTag, {
          tone: row.status === 'active' ? 'success' : row.status === 'draft' ? 'warning' : 'neutral',
          label: statusLabel(row.status),
        });
      },
    },
    { title: '字段数', key: 'field_count', width: 90 },
    { title: '行数', key: 'row_count', width: 90 },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 270,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['datasets:dataset:manage']), onClick: () => openEdit(row) },
            { label: '字段', show: hasPermission(['datasets:dataset:manage']), onClick: () => openFields(row) },
            { label: '数据', show: hasPermission(['datasets:dataset:manage']) && row.dataset_type === 'manual', onClick: () => openRows(row) },
            { label: '发布', tone: 'primary', show: hasPermission(['datasets:dataset:publish']), onClick: () => publish(row) },
            { label: '预览', show: hasPermission(['datasets:dataset:preview']), onClick: () => openPreview(row) },
            {
              label: '删除',
              tone: 'danger',
              show: hasPermission(['datasets:dataset:manage']),
              confirm: true,
              confirmTitle: '删除数据集',
              confirmContent: `确认删除「${row.name}」吗？`,
              onConfirm: () => remove(row),
            },
          ],
        });
      },
    },
  ];

  const datasetPage = defineListPage<Dataset>({
    id: 'datasets.manage',
    title: '数据集管理',
    description: '维护仪表盘和后续数据源复用的数据集定义、字段和预览数据。',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1260,
      sort: { remote: true },
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: hasPermission(['datasets:dataset:manage'])
        ? { key: 'create', label: '新建数据集', type: 'primary', onClick: () => openCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  const previewColumns = computed<DataTableColumns<Record<string, unknown>>>(() =>
    previewFields.value.map((field) => ({
      title: field.label || field.field_key,
      key: field.field_key,
      minWidth: 120,
      ellipsis: { tooltip: true },
      render: (row) => String(row[field.field_key] ?? ''),
    }))
  );

  function resetForm() {
    Object.assign(form, {
      id: undefined,
      key: '',
      name: '',
      description: '',
      dataset_type: 'manual',
      status: 'draft',
      visibility: 'tenant',
    });
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    datasetDrawerVisible.value = true;
  }

  function openEdit(row: Dataset) {
    Object.assign(form, row);
    datasetDrawerVisible.value = true;
  }

  async function submitDataset() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      await saveDataset(form as Dataset);
      message.success('数据集已保存');
      datasetDrawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function openFields(row: Dataset) {
    activeDataset.value = row;
    const detail = await getDataset(row.id);
    const fields = detail.fields?.length ? detail.fields : defaultFields();
    fieldJson.value = JSON.stringify(fields.map(normalizeFieldForEdit), null, 2);
    schemaModalVisible.value = true;
  }

  async function submitFields() {
    if (!activeDataset.value) return;
    const fields = parseJsonArray(fieldJson.value, '字段配置');
    if (!fields) return;
    saving.value = true;
    try {
      await saveDatasetFields(activeDataset.value.id, fields as DatasetField[]);
      message.success('字段配置已保存');
      schemaModalVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  function openRows(row: Dataset) {
    activeDataset.value = row;
    rowsJson.value = JSON.stringify([], null, 2);
    rowsModalVisible.value = true;
  }

  async function submitRows() {
    if (!activeDataset.value) return;
    const items = parseJsonArray(rowsJson.value, '手工数据');
    if (!items) return;
    saving.value = true;
    try {
      await saveDatasetRows(activeDataset.value.id, items as Record<string, unknown>[]);
      message.success('手工数据已保存');
      rowsModalVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function publish(row: Dataset) {
    await publishDataset(row.id);
    message.success('数据集已发布');
    await reload();
  }

  async function remove(row: Dataset) {
    await deleteDataset(row.id);
    message.success('数据集已删除');
    await reload();
  }

  async function openPreview(row: Dataset) {
    activeDataset.value = row;
    previewPage.value = 1;
    previewRows.value = [];
    previewFields.value = [];
    previewModalVisible.value = true;
    await loadPreview();
  }

  async function loadPreview() {
    if (!activeDataset.value) return;
    previewLoading.value = true;
    try {
      const payload = await previewDataset(activeDataset.value.id, { page: previewPage.value, page_size: 10 });
      previewFields.value = payload.fields || [];
      previewRows.value = payload.items || [];
      previewTotal.value = payload.pagination?.total || previewRows.value.length;
    } finally {
      previewLoading.value = false;
    }
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const payload = await listDatasets({
        ...runtimeListParams(state),
        keyword: keyword.value,
        dataset_type: typeFilter.value || '',
        status: statusFilter.value || '',
      });
      rows.value = payload.items || [];
      paginationTotal.value = payload.pagination?.total || rows.value.length;
    } finally {
      loading.value = false;
    }
  }

  function parseJsonArray(value: string, label: string) {
    try {
      const parsed = JSON.parse(value || '[]');
      if (!Array.isArray(parsed)) {
        message.error(`${label}必须是 JSON 数组`);
        return null;
      }
      return parsed;
    } catch {
      message.error(`${label}不是有效 JSON`);
      return null;
    }
  }

  function defaultFields(): DatasetField[] {
    return [
      { field_key: 'name', label: '名称', data_type: 'text', nullable: false, visible: true, sort_order: 1 },
      { field_key: 'value', label: '数值', data_type: 'number', nullable: true, visible: true, sort_order: 2 },
    ];
  }

  function normalizeFieldForEdit(field: DatasetField) {
    return {
      field_key: field.field_key,
      label: field.label,
      data_type: field.data_type || 'text',
      semantic_type: field.semantic_type || '',
      unit: field.unit || '',
      precision: field.precision ?? null,
      nullable: field.nullable !== false,
      visible: field.visible !== false,
      sort_order: field.sort_order || 0,
      expression: field.expression || '',
      config: field.config || {},
    };
  }

  function typeLabel(value: string) {
    return String(typeOptions.find((item) => item.value === value)?.label || value || '-');
  }

  function statusLabel(value: string) {
    return String(statusOptions.find((item) => item.value === value)?.label || value || '-');
  }

  reload();
</script>

<style lang="less" scoped>
  .dataset-page {
    min-width: 0;
  }

  .dataset-page__filter {
    width: min(320px, 100%);
  }

  .dataset-page__select {
    width: 160px;
  }

  .dataset-page__alert {
    margin-bottom: 12px;
  }

  .dataset-page__preview-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-top: 16px;
  }

  :global(.dataset-page__modal) {
    width: min(760px, calc(100vw - 32px));
  }

  :global(.dataset-page__preview) {
    width: min(960px, calc(100vw - 32px));
  }
</style>
