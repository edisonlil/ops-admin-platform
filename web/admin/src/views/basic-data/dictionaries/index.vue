<template>
  <div class="basic-data-dictionary-page">
    <ListPageRuntime :schema="dictionaryPage" :rows="typeRows" :loading="loadingTypes" @refresh="reloadTypes">
      <template #filters>
        <n-input v-model:value="typeKeyword" clearable placeholder="搜索编码、名称或说明" class="basic-data-dictionary-page__filter" @keyup.enter="reloadTypes" />
        <n-select v-model:value="typeStatus" clearable placeholder="状态" :options="statusOptions" class="basic-data-dictionary-page__status" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="typeDrawerVisible" width="560">
      <n-drawer-content :title="typeForm.id ? '编辑业务字典' : '新建业务字典'">
        <n-form ref="typeFormRef" :model="typeForm" :rules="typeRules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="编码" path="code">
              <n-input v-model:value="typeForm.code" placeholder="customer_level" />
            </n-form-item-gi>
            <n-form-item-gi label="名称" path="name">
              <n-input v-model:value="typeForm.name" placeholder="客户等级" />
            </n-form-item-gi>
            <n-form-item-gi label="分类" path="category">
              <n-input v-model:value="typeForm.category" placeholder="general" />
            </n-form-item-gi>
            <n-form-item-gi label="状态" path="status">
              <n-select v-model:value="typeForm.status" :options="statusOptions" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="排序">
            <n-input-number v-model:value="typeForm.sort_order" class="basic-data-dictionary-page__number" />
          </n-form-item>
          <n-form-item label="说明">
            <n-input v-model:value="typeForm.description" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="typeDrawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="savingType" @click="submitType">保存业务字典</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-drawer v-model:show="itemDrawerVisible" width="840">
      <n-drawer-content :title="activeType ? `${activeType.name} · 字典项` : '字典项'">
        <ListPageRuntime :schema="itemPage" :rows="itemRows" :loading="loadingItems" @refresh="reloadItems">
          <template #filters>
            <n-input v-model:value="itemKeyword" clearable placeholder="搜索编码、值或显示标签" class="basic-data-dictionary-page__filter" @keyup.enter="reloadItems" />
            <n-select v-model:value="itemStatus" clearable placeholder="状态" :options="statusOptions" class="basic-data-dictionary-page__status" />
          </template>
        </ListPageRuntime>
      </n-drawer-content>
    </n-drawer>

    <n-drawer v-model:show="itemFormVisible" width="560">
      <n-drawer-content :title="itemForm.id ? '编辑字典项' : '新建字典项'">
        <n-form ref="itemFormRef" :model="itemForm" :rules="itemRules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="编码" path="code">
              <n-input v-model:value="itemForm.code" placeholder="gold" />
            </n-form-item-gi>
            <n-form-item-gi label="值" path="value">
              <n-input v-model:value="itemForm.value" placeholder="G" />
            </n-form-item-gi>
            <n-form-item-gi label="显示标签" path="label">
              <n-input v-model:value="itemForm.label" placeholder="金牌" />
            </n-form-item-gi>
            <n-form-item-gi label="状态" path="status">
              <n-select v-model:value="itemForm.status" :options="statusOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="颜色">
              <n-input v-model:value="itemForm.color" placeholder="success / warning / #1677ff" />
            </n-form-item-gi>
            <n-form-item-gi label="排序">
              <n-input-number v-model:value="itemForm.sort_order" class="basic-data-dictionary-page__number" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="扩展 JSON">
            <n-input v-model:value="itemExtraText" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" placeholder='{"score":90}' />
          </n-form-item>
          <n-form-item label="说明">
            <n-input v-model:value="itemForm.description" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="itemFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="savingItem" @click="submitItem">保存字典项</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref, watch } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deleteDictionaryItem,
    deleteDictionaryType,
    getDictionaryItems,
    getDictionaryTypes,
    saveDictionaryItem,
    saveDictionaryType,
    type DictionaryItem,
    type DictionaryType,
  } from '@/api/basicData';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loadingTypes = ref(false);
  const savingType = ref(false);
  const loadingItems = ref(false);
  const savingItem = ref(false);
  const typeDrawerVisible = ref(false);
  const itemDrawerVisible = ref(false);
  const itemFormVisible = ref(false);
  const typeFormRef = ref<FormInst | null>(null);
  const itemFormRef = ref<FormInst | null>(null);
  const typeRows = ref<DictionaryType[]>([]);
  const itemRows = ref<DictionaryItem[]>([]);
  const activeType = ref<DictionaryType | null>(null);
  const typeKeyword = ref('');
  const typeStatus = ref<string | null>(null);
  const itemKeyword = ref('');
  const itemStatus = ref<string | null>(null);
  const itemExtraText = ref('{}');

  const typeForm = reactive<Partial<DictionaryType>>({
    code: '',
    name: '',
    category: 'general',
    description: '',
    status: 'active',
    sort_order: 0,
  });

  const itemForm = reactive<Partial<DictionaryItem>>({
    code: '',
    value: '',
    label: '',
    color: '',
    description: '',
    extra: {},
    status: 'active',
    sort_order: 0,
  });

  const statusOptions: SelectOption[] = [
    { label: '启用', value: 'active' },
    { label: '停用', value: 'disabled' },
  ];

  const typeRules: FormRules = {
    code: [{ required: true, message: '请输入业务字典编码', trigger: ['blur', 'input'] }],
    name: [{ required: true, message: '请输入业务字典名称', trigger: ['blur', 'input'] }],
  };

  const itemRules: FormRules = {
    code: [{ required: true, message: '请输入字典项编码', trigger: ['blur', 'input'] }],
    value: [{ required: true, message: '请输入字典项值', trigger: ['blur', 'input'] }],
    label: [{ required: true, message: '请输入显示标签', trigger: ['blur', 'input'] }],
  };

  const typeColumns: DataTableColumns<DictionaryType> = [
    { title: '编码', key: 'code', width: 180 },
    { title: '名称', key: 'name', minWidth: 160 },
    { title: '分类', key: 'category', width: 140 },
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
    { title: '排序', key: 'sort_order', width: 90 },
    { title: '说明', key: 'description', minWidth: 220, ellipsis: { tooltip: true } },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 230,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '字典项', onClick: () => openItems(row) },
            { label: '编辑', show: hasPermission(['basic-data:dictionary:manage']), onClick: () => openEditType(row) },
            {
              label: '删除',
              tone: 'danger',
              show: hasPermission(['basic-data:dictionary:manage']),
              confirm: true,
              confirmTitle: '删除业务字典',
              confirmContent: '删除字典会同步删除其字典项。',
              onConfirm: () => removeType(row),
            },
          ],
        });
      },
    },
  ];

  const itemColumns: DataTableColumns<DictionaryItem> = [
    { title: '编码', key: 'code', width: 140 },
    { title: '值', key: 'value', width: 120 },
    { title: '显示标签', key: 'label', minWidth: 160 },
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
    { title: '颜色', key: 'color', width: 120, ellipsis: { tooltip: true } },
    { title: '排序', key: 'sort_order', width: 90 },
    { title: '说明', key: 'description', minWidth: 180, ellipsis: { tooltip: true } },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['basic-data:dictionary:manage']), onClick: () => openEditItem(row) },
            {
              label: '删除',
              tone: 'danger',
              show: hasPermission(['basic-data:dictionary:manage']),
              confirm: true,
              confirmTitle: '删除字典项',
              confirmContent: '确认删除该字典项？',
              onConfirm: () => removeItem(row),
            },
          ],
        });
      },
    },
  ];

  const dictionaryPage = computed(() =>
    defineListPage<DictionaryType>({
      id: 'basic-data.dictionaries',
      title: '业务字典',
      description: '维护业务系统可复用的枚举和值域。',
      variant: 'dense-data',
      density: 'compact',
      view: {
        type: 'table',
        columns: typeColumns,
        rowKey: (row) => row.id,
        scrollX: 1280,
        tableProps: { size: 'small' },
      },
      toolbar: {
        primaryAction: hasPermission(['basic-data:dictionary:manage'])
          ? { key: 'create', label: '新建业务字典', type: 'primary', onClick: () => openCreateType() }
          : undefined,
        rightTools: ['refresh'],
      },
      pagination: { pageSize: 20 },
    })
  );

  const itemPage = computed(() =>
    defineListPage<DictionaryItem>({
      id: 'basic-data.dictionary-items',
      title: '字典项',
      description: activeType.value ? `${activeType.value.code} · ${activeType.value.name}` : '',
      variant: 'dense-data',
      density: 'compact',
      embedded: true,
      view: {
        type: 'table',
        columns: itemColumns,
        rowKey: (row) => row.id,
        scrollX: 980,
        tableProps: { size: 'small' },
      },
      toolbar: {
        primaryAction:
          activeType.value && hasPermission(['basic-data:dictionary:manage'])
            ? { key: 'create', label: '新建字典项', type: 'primary', onClick: () => openCreateItem() }
            : undefined,
        rightTools: ['refresh'],
      },
      pagination: { pageSize: 20 },
    })
  );

  watch([typeStatus], () => reloadTypes());
  watch([itemStatus], () => reloadItems());

  function resetTypeForm() {
    Object.assign(typeForm, {
      id: undefined,
      code: '',
      name: '',
      category: 'general',
      description: '',
      status: 'active',
      sort_order: 0,
    });
    typeFormRef.value?.restoreValidation();
  }

  function resetItemForm() {
    Object.assign(itemForm, {
      id: undefined,
      code: '',
      value: '',
      label: '',
      color: '',
      description: '',
      extra: {},
      status: 'active',
      sort_order: 0,
    });
    itemExtraText.value = '{}';
    itemFormRef.value?.restoreValidation();
  }

  function openCreateType() {
    resetTypeForm();
    typeDrawerVisible.value = true;
  }

  function openEditType(row: DictionaryType) {
    Object.assign(typeForm, row);
    typeDrawerVisible.value = true;
  }

  function openItems(row: DictionaryType) {
    activeType.value = row;
    itemKeyword.value = '';
    itemStatus.value = null;
    itemDrawerVisible.value = true;
    reloadItems();
  }

  function openCreateItem() {
    resetItemForm();
    itemFormVisible.value = true;
  }

  function openEditItem(row: DictionaryItem) {
    Object.assign(itemForm, row);
    itemExtraText.value = JSON.stringify(row.extra || {}, null, 2);
    itemFormVisible.value = true;
  }

  async function submitType() {
    try {
      await typeFormRef.value?.validate();
    } catch {
      return;
    }
    savingType.value = true;
    try {
      await saveDictionaryType(typeForm);
      message.success('业务字典已保存');
      typeDrawerVisible.value = false;
      await reloadTypes();
    } finally {
      savingType.value = false;
    }
  }

  async function submitItem() {
    if (!activeType.value) return;
    try {
      await itemFormRef.value?.validate();
    } catch {
      return;
    }
    const extra = parseExtra();
    if (!extra) return;
    savingItem.value = true;
    try {
      await saveDictionaryItem(activeType.value.id, { ...itemForm, extra });
      message.success('字典项已保存');
      itemFormVisible.value = false;
      await reloadItems();
    } finally {
      savingItem.value = false;
    }
  }

  async function removeType(row: DictionaryType) {
    await deleteDictionaryType(row.id);
    message.success('业务字典已删除');
    if (activeType.value?.id === row.id) {
      activeType.value = null;
      itemRows.value = [];
      itemDrawerVisible.value = false;
    }
    await reloadTypes();
  }

  async function removeItem(row: DictionaryItem) {
    await deleteDictionaryItem(row.id);
    message.success('字典项已删除');
    await reloadItems();
  }

  async function reloadTypes() {
    loadingTypes.value = true;
    try {
      const payload = await getDictionaryTypes({
        page: 1,
        page_size: 100,
        keyword: typeKeyword.value,
        status: typeStatus.value,
      });
      typeRows.value = payload.items || [];
    } finally {
      loadingTypes.value = false;
    }
  }

  async function reloadItems() {
    if (!activeType.value) return;
    loadingItems.value = true;
    try {
      const payload = await getDictionaryItems(activeType.value.id, {
        page: 1,
        page_size: 100,
        keyword: itemKeyword.value,
        status: itemStatus.value,
      });
      itemRows.value = payload.items || [];
    } finally {
      loadingItems.value = false;
    }
  }

  function parseExtra() {
    const text = itemExtraText.value.trim();
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

  reloadTypes();
</script>

<style lang="less" scoped>
  .basic-data-dictionary-page {
    min-width: 0;
  }

  .basic-data-dictionary-page__filter {
    width: min(320px, 100%);
  }

  .basic-data-dictionary-page__status {
    width: 160px;
  }

  .basic-data-dictionary-page__number {
    width: 100%;
  }
</style>
