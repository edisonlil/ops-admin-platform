<template>
  <div class="basic-data-dictionary-page">
    <ListPageRuntime :schema="dictionaryPage" :rows="typeRows" :loading="loadingTypes" @refresh="reloadAll" @filter-reset="resetFilters">
      <template #filters="{ submit }">
        <n-input
          v-model:value="typeKeyword"
          clearable
          placeholder="搜索字典编码、名称或说明"
          @keyup.enter="submit"
        />
        <n-select
          v-model:value="typeStatus"
          clearable
          placeholder="状态"
          :options="statusOptions"
          @update:value="submit"
        />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="typeDrawerVisible" width="560">
      <n-drawer-content :title="typeForm.id ? '编辑业务字典' : '新建业务字典'">
        <n-form ref="typeFormRef" :model="typeForm" :rules="typeRules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="上级分类">
              <n-select
                v-model:value="typeForm.parent_id"
                clearable
                filterable
                :options="parentTypeOptions"
                placeholder="不选择则为根分类"
              />
            </n-form-item-gi>
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
            <n-form-item-gi label="状态" path="status">
              <n-select v-model:value="itemForm.status" :options="statusOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="颜色">
              <n-color-picker
                v-model:value="itemForm.color"
                clearable
                :show-alpha="false"
                :modes="['hex']"
                :swatches="dictionaryColorSwatches"
                placeholder="不选择则自动分配"
              />
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
  import type { DataTableColumns, FormInst, FormRules, SelectOption, TreeOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
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
  const itemFormVisible = ref(false);
  const typeFormRef = ref<FormInst | null>(null);
  const itemFormRef = ref<FormInst | null>(null);
  const typeRows = ref<DictionaryType[]>([]);
  const itemRows = ref<DictionaryItem[]>([]);
  const itemPaginationTotal = ref(0);
  const activeType = ref<DictionaryType | null>(null);
  const selectedTypeKeys = ref<Array<string | number>>([]);
  const typeKeyword = ref('');
  const typeStatus = ref<string | null>(null);
  const itemKeyword = ref('');
  const itemStatus = ref<string | null>(null);
  const itemExtraText = ref('{}');
  const itemRuntimeState = ref<ListRuntimeState>({});

  const typeForm = reactive<Partial<DictionaryType>>({
    parent_id: null,
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
  const dictionaryColorSwatches = [
    '#2563EB',
    '#059669',
    '#D97706',
    '#DC2626',
    '#7C3AED',
    '#0891B2',
    '#DB2777',
    '#475569',
  ];
  const dictionaryColorAliases: Record<string, string> = {
    success: '#059669',
    warning: '#D97706',
    error: '#DC2626',
    danger: '#DC2626',
    info: '#2563EB',
    neutral: '#475569',
  };

  const typeRules: FormRules = {
    code: [{ required: true, message: '请输入业务字典编码', trigger: ['blur', 'input'] }],
    name: [{ required: true, message: '请输入业务字典名称', trigger: ['blur', 'input'] }],
  };

  const itemRules: FormRules = {
    code: [{ required: true, message: '请输入字典项编码', trigger: ['blur', 'input'] }],
    value: [{ required: true, message: '请输入字典项值', trigger: ['blur', 'input'] }],
  };

  const typeTree = computed<TreeOption[]>(() => buildTypeTree(typeRows.value));
  const parentTypeOptions = computed<SelectOption[]>(() =>
    typeRows.value
      .filter((item) => item.id !== typeForm.id)
      .filter((item) => !typeForm.id || !isTypeDescendant(item.id, typeForm.id))
      .map((item) => ({ label: item.name, value: item.id }))
  );

  const activeTypeTitle = computed(() => activeType.value?.name || '字典项');
  const activeTypeDescription = computed(() =>
    activeType.value ? `${activeType.value.code} / ${activeType.value.category || 'general'}` : '请选择左侧业务字典'
  );

  const itemColumns: DataTableColumns<DictionaryItem> = [
    { title: '编码', key: 'code', width: 160 },
    { title: '值', key: 'value', minWidth: 180 },
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
    {
      title: '颜色',
      key: 'color',
      width: 120,
      render(row) {
        return h('span', { class: 'basic-data-dictionary-page__color-cell' }, [
          h('span', {
            class: 'basic-data-dictionary-page__color-swatch',
            style: { backgroundColor: resolveDisplayColor(row.color) },
          }),
          h('span', { class: 'basic-data-dictionary-page__color-text' }, row.color || '-'),
        ]);
      },
    },
    { title: '排序', key: 'sort_order', width: 90 },
    { title: '说明', key: 'description', minWidth: 220, ellipsis: { tooltip: true } },
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
    defineListPage<DictionaryItem>({
      id: 'basic-data.dictionaries',
      title: '业务字典',
      description: '维护业务系统可复用的枚举、层级字典和取值范围。',
      variant: 'dense-data',
      density: 'compact',
      view: {
        type: 'split-list',
        split: {
          masterWidth: 320,
          minHeight: 520,
          master: {
            title: '字典分类',
            description: `${typeRows.value.length} 个业务字典`,
            primaryAction: hasPermission(['basic-data:dictionary:manage'])
              ? { key: 'create-type', label: '新建业务字典', type: 'primary', onClick: () => openCreateType() }
              : undefined,
            view: {
              type: 'tree',
              treeData: typeTree.value,
              selectedKeys: selectedTypeKeys.value,
              treeProps: { defaultExpandAll: true },
              treeNodeActions: (node) => {
                const row = typeRows.value.find((entry) => entry.id === Number(node.key));
                if (!row || !hasPermission(['basic-data:dictionary:manage'])) return [];
                return [
                  { key: 'edit-type', label: '编辑分类', onClick: () => openEditType(row) },
                  {
                    key: 'delete-type',
                    label: '删除分类',
                    type: 'error',
                    confirm: true,
                    confirmTitle: '删除字典分类',
                    confirmContent: `确认删除字典分类「${row.name || row.code}」？删除后其字典项也会同步删除。`,
                    onClick: () => removeType(row),
                  },
                ];
              },
              onUpdateSelectedKeys: handleTypeSelect,
            },
            pagination: false,
          },
          detail: {
            title: activeTypeTitle.value,
            description: activeTypeDescription.value,
            rows: itemRows.value,
            loading: loadingItems.value,
            refresh: reloadItems,
            paginationTotal: itemPaginationTotal.value,
            primaryAction:
              activeType.value && hasPermission(['basic-data:dictionary:manage'])
                ? { key: 'create-item', label: '新建字典项', type: 'primary', onClick: () => openCreateItem() }
                : undefined,
            view: {
              type: 'table',
              columns: itemColumns,
              sort: { remote: true },
              rowKey: (row) => row.id,
              scrollX: 1160,
              tableProps: { size: 'small' },
              columnRuntime: {
                disabledFreezeKeys: ['actions'],
                columns: [
                  { key: 'code', label: '编码', sortable: true },
                  { key: 'value', label: '值', sortable: true },
                  { key: 'status', label: '状态', sortable: true },
                  { key: 'color', label: '颜色' },
                  { key: 'sort_order', label: '排序', sortable: true },
                  { key: 'description', label: '描述' },
                  { key: 'actions', label: '操作', required: true },
                ],
              },
            },
            pagination: { pageSize: 20 },
          },
        },
      },
      toolbar: { rightTools: ['refresh'] },
      filterBar: { showSubmit: true, showReset: true },
      pagination: false,
    })
  );

  watch([typeStatus], () => reloadTypes());
  watch([itemStatus], () => reloadItems());

  function resetTypeForm() {
    Object.assign(typeForm, {
      id: undefined,
      parent_id: null,
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

  function handleTypeSelect(keys: Array<string | number>) {
    const id = Number(keys[0] || 0);
    const nextType = typeRows.value.find((row) => row.id === id) || null;
    selectedTypeKeys.value = nextType ? [nextType.id] : [];
    activeType.value = nextType;
    itemKeyword.value = '';
    itemStatus.value = null;
    itemRows.value = [];
    if (nextType) reloadItems();
  }

  function openCreateItem() {
    if (!activeType.value) return;
    resetItemForm();
    itemFormVisible.value = true;
  }

  function openEditItem(row: DictionaryItem) {
    Object.assign(itemForm, row);
    itemForm.color = normalizeColorValue(row.color);
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
      const saved = await saveDictionaryType(typeForm);
      message.success('业务字典已保存');
      typeDrawerVisible.value = false;
      await reloadTypes(Number(saved.item?.id || typeForm.id || 0));
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
      await saveDictionaryItem(activeType.value.id, { ...itemForm, color: resolveItemColor(), extra });
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
      selectedTypeKeys.value = [];
      itemRows.value = [];
    }
    await reloadTypes();
  }

  async function removeItem(row: DictionaryItem) {
    await deleteDictionaryItem(row.id);
    message.success('字典项已删除');
    await reloadItems();
  }

  async function reloadAll() {
    await reloadTypes(activeType.value?.id);
    if (activeType.value) await reloadItems();
  }

  function resetFilters() {
    typeKeyword.value = '';
    typeStatus.value = null;
  }

  async function reloadTypes(preferredTypeId?: number) {
    loadingTypes.value = true;
    try {
      const payload = await getDictionaryTypes({
        page: 1,
        page_size: 100,
        keyword: typeKeyword.value,
        status: typeStatus.value,
      });
      typeRows.value = payload.items || [];
      syncActiveType(preferredTypeId);
    } finally {
      loadingTypes.value = false;
    }
  }

  async function reloadItems(state?: ListRuntimeState) {
    if (!activeType.value) return;
    if (state) {
      itemRuntimeState.value = state;
    }
    loadingItems.value = true;
    try {
      const payload = await getDictionaryItems(activeType.value.id, {
        ...runtimeListParams(state || itemRuntimeState.value, { pageSize: 20 }),
        keyword: itemKeyword.value,
        status: itemStatus.value,
      });
      itemRows.value = payload.items || [];
      itemPaginationTotal.value = payload.pagination?.total || itemRows.value.length;
    } finally {
      loadingItems.value = false;
    }
  }

  function syncActiveType(preferredTypeId?: number) {
    const preferred = preferredTypeId ? typeRows.value.find((row) => row.id === preferredTypeId) : null;
    const existing = activeType.value ? typeRows.value.find((row) => row.id === activeType.value?.id) : null;
    const next = preferred || existing || typeRows.value[0] || null;
    activeType.value = next;
    selectedTypeKeys.value = next ? [next.id] : [];
    if (next) reloadItems();
    else itemRows.value = [];
  }

  function buildTypeTree(items: DictionaryType[]): TreeOption[] {
    const nodes = new Map<number, TreeOption & { parent_id?: number | null }>();
    items.forEach((item) => {
      nodes.set(item.id, {
        key: item.id,
        label: item.name,
        parent_id: item.parent_id || null,
        children: [],
      });
    });
    const roots: TreeOption[] = [];
    nodes.forEach((node) => {
      const parentId = Number(node.parent_id || 0);
      const parent = parentId ? nodes.get(parentId) : null;
      if (parent && parent.key !== node.key) {
        (parent.children ||= []).push(node);
      } else {
        roots.push(node);
      }
    });
    nodes.forEach((node) => {
      if (!node.children?.length) delete node.children;
      delete node.parent_id;
    });
    return roots;
  }

  function isTypeDescendant(candidateId: number, ancestorId: number): boolean {
    let current = typeRows.value.find((item) => item.id === candidateId);
    const visited = new Set<number>();
    while (current?.parent_id) {
      if (current.parent_id === ancestorId) return true;
      if (visited.has(current.parent_id)) return false;
      visited.add(current.parent_id);
      current = typeRows.value.find((item) => item.id === current?.parent_id);
    }
    return false;
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

  function resolveItemColor() {
    const color = normalizeColorValue(itemForm.color);
    if (color) return color;
    return dictionaryColorSwatches[Math.floor(Math.random() * dictionaryColorSwatches.length)];
  }

  function normalizeColorValue(value?: string) {
    const color = String(value || '').trim();
    return dictionaryColorAliases[color.toLowerCase()] || color;
  }

  function resolveDisplayColor(value?: string) {
    return normalizeColorValue(value) || '#CBD5E1';
  }

  reloadTypes();
</script>

<style lang="less" scoped>
  .basic-data-dictionary-page {
    min-width: 0;
  }

  .basic-data-dictionary-page__number {
    width: 100%;
  }

  .basic-data-dictionary-page__color-cell {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    gap: 8px;
    min-width: 0;
  }

  .basic-data-dictionary-page__color-swatch {
    width: 16px;
    height: 16px;
    flex: 0 0 auto;
    border: 1px solid color-mix(in srgb, var(--app-border-color, #d9e1ec) 70%, transparent);
    border-radius: 4px;
  }

  .basic-data-dictionary-page__color-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
