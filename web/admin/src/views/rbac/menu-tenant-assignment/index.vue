<template>
  <div class="tenant-menu-assignment">
    <ListPageRuntime
      :schema="assignmentPage"
      :rows="rows"
      :loading="loading"
      :pagination-total="paginationTotal"
      @refresh="reload"
      @filter-reset="resetFilters"
    >
      <template #filters="{ submit }">
        <n-input v-model:value="query" clearable placeholder="搜索租户名称或 Key" @keyup.enter="submit" />
      </template>
    </ListPageRuntime>

    <n-modal v-model:show="menuModalVisible" preset="card" :style="{ width: '720px' }" :bordered="false">
      <template #header>
        <span>{{ currentTenant ? `${currentTenant.name} / ${currentTenant.tenant_key} 菜单配置` : '租户菜单配置' }}</span>
      </template>

      <n-space vertical :size="12">
        <n-input v-model:value="menuPattern" clearable placeholder="搜索菜单名称或 Key" />
        <n-space align="center" justify="space-between">
          <n-space size="small">
            <n-button size="small" @click="toggleMenuTreeExpanded">
              {{ expandedMenuKeys.length ? '收起全部' : '展开全部' }}
            </n-button>
            <n-button size="small" :disabled="!canAssignMenus" @click="selectAllMenus">全选菜单</n-button>
            <n-button size="small" :disabled="!canAssignMenus" @click="invertMenus">反选菜单</n-button>
            <n-button size="small" :disabled="!checkedMenuKeys.length || !canAssignMenus" @click="clearMenus">清空选择</n-button>
          </n-space>
          <n-tag size="small" type="success" :bordered="false">已启用 {{ checkedMenuKeys.length }} 个菜单</n-tag>
        </n-space>

        <div class="tenant-menu-tree">
          <n-spin :show="menusLoading">
            <n-tree
              block-line
              checkable
              virtual-scroll
              :data="menuTree"
              :pattern="menuPattern"
              :checked-keys="checkedMenuKeys"
              :indeterminate-keys="checkedMenuIndeterminateKeys"
              :expanded-keys="expandedMenuKeys"
              :scrollbar-props="{ style: { height: '100%' } }"
              @update:checked-keys="handleCheckedMenuKeys"
              @update:expanded-keys="handleExpandedMenuKeys"
            />
          </n-spin>
        </div>
      </n-space>

      <template #footer>
        <n-space justify="end">
          <n-button @click="menuModalVisible = false">取消</n-button>
          <n-button :disabled="!changed" @click="resetSelection">重置</n-button>
          <n-button
            v-if="canAssignMenus"
            type="primary"
            :disabled="!currentTenant || !changed"
            :loading="saving"
            @click="saveAssignments"
          >
            保存配置
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, ref } from 'vue';
  import { NTag, useMessage } from 'naive-ui';
  import type { DataTableColumns, TreeOption } from 'naive-ui';
  import {
    getRbacMenus,
    getTenantMenuAssignments,
    getTenants,
    updateTenantMenuAssignments,
    type TenantMenuAssignmentsData,
  } from '@/api/business';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { usePermission } from '@/hooks/web/usePermission';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';

  interface TenantRow extends Recordable {
    id: number;
    tenant_key: string;
    name: string;
    status: string;
    user_count?: number;
    api_key_count?: number;
    update_time?: string;
  }

  interface MenuRow extends Recordable {
    key: string;
    label: string;
    parent_key?: string;
    menu_type?: 'directory' | 'page' | 'action' | string;
    sort_order?: number;
    children?: MenuRow[];
  }

  type TreeCheckMeta = {
    action?: 'check' | 'uncheck' | string;
    node?: TreeOption;
  };

  const message = useMessage();
  const { hasPermission } = usePermission();
  const canAssignMenus = computed(() => hasPermission(['system:menus:assign_tenants']));
  const loading = ref(false);
  const menusLoading = ref(false);
  const saving = ref(false);
  const rows = ref<TenantRow[]>([]);
  const query = ref('');
  const paginationTotal = ref(0);
  const currentState = ref<ListRuntimeState>();
  const menuModalVisible = ref(false);
  const currentTenant = ref<TenantRow | null>(null);
  const menuRows = ref<MenuRow[]>([]);
  const menuPattern = ref('');
  const expandedMenuKeys = ref<string[]>([]);
  const checkedMenuKeys = ref<string[]>([]);
  const savedMenuKeys = ref<string[]>([]);

  const menuTree = computed(() => buildMenuTree(menuRows.value.filter((menu) => menu.menu_type !== 'action')));
  const checkedMenuIndeterminateKeys = computed(() => collectIndeterminateMenuKeys(checkedMenuKeys.value, menuTree.value));
  const changed = computed(() => sortedKeyText(checkedMenuKeys.value) !== sortedKeyText(savedMenuKeys.value));

  const columns: DataTableColumns<TenantRow> = [
    { title: 'ID', key: 'id', width: 80 },
    { title: '租户名称', key: 'name', minWidth: 180, ellipsis: { tooltip: true } },
    { title: '租户 Key', key: 'tenant_key', minWidth: 160, ellipsis: { tooltip: true } },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render(row) {
        return h(AppStatusTag, {
          tone: row.status === 'active' ? 'success' : 'warning',
          label: row.status === 'active' ? '启用' : '停用',
        });
      },
    },
    { title: '成员', key: 'user_count', width: 90 },
    { title: 'API Key', key: 'api_key_count', width: 100 },
    {
      title: '更新时间',
      key: 'update_time',
      width: 190,
      render: (row) => formatToDateTime(row.update_time || ''),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            {
              label: '菜单配置',
              tone: 'primary',
              show: hasPermission(['system:menu:access']),
              onClick: () => openTenantMenus(row),
            },
          ],
        });
      },
    },
  ];

  const assignmentPage = defineListPage<TenantRow>({
    id: 'rbac.tenantMenuAssignments',
    title: '租户菜单配置',
    description: '选择租户后配置该租户启用哪些租户级菜单入口。',
    variant: 'enterprise',
    density: 'compact',
    filters: [
      {
        key: 'q',
        label: '租户搜索',
        type: 'search',
        placeholder: '搜索租户名称或 Key',
      },
    ],
    view: {
      type: 'table',
      columns,
      rowKey: (row) => Number(row.id),
      scrollX: 1080,
      sort: { remote: true },
      columnRuntime: {
        columns: [
          { key: 'id', sortable: true },
          { key: 'name', sortable: true },
          { key: 'tenant_key', sortable: true },
          { key: 'status', sortable: true },
          { key: 'user_count', sortable: true },
          { key: 'api_key_count', sortable: true },
          { key: 'update_time', sortable: true },
          { key: 'actions', required: true, sortable: false },
        ],
      },
      tableProps: {
        size: 'small',
      },
    },
    toolbar: {
      rightTools: ['refresh'],
    },
    filterBar: { showSubmit: true, showReset: true },
    pagination: { pageSize: 20 },
  });

  function sortedKeyText(keys: string[]) {
    return [...keys].sort().join(',');
  }

  function buildMenuTree(items: MenuRow[]) {
    const nodeMap = new Map<string, MenuRow>();
    const roots: MenuRow[] = [];
    items.forEach((item) => nodeMap.set(item.key, { ...item, children: [] }));
    nodeMap.forEach((node) => {
      const parentKey = String(node.parent_key || '');
      const parent = parentKey ? nodeMap.get(parentKey) : undefined;
      if (parent) parent.children?.push(node);
      else roots.push(node);
    });
    const normalize = (nodes: MenuRow[]): TreeOption[] =>
      nodes
        .sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0))
        .map((node) => ({
          key: node.key,
          label: node.label || node.key,
          children: node.children?.length ? normalize(node.children) : undefined,
        }));
    return normalize(roots);
  }

  function collectTreeKeys(nodes: TreeOption[]) {
    const keys: string[] = [];
    const visit = (items: TreeOption[]) => {
      items.forEach((item) => {
        keys.push(String(item.key));
        item.children?.length && visit(item.children);
      });
    };
    visit(nodes);
    return keys;
  }

  function collectNonLeafKeys(nodes: TreeOption[]) {
    const keys: string[] = [];
    const visit = (items: TreeOption[]) => {
      items.forEach((item) => {
        if (item.children?.length) {
          keys.push(String(item.key));
          visit(item.children);
        }
      });
    };
    visit(nodes);
    return keys;
  }

  function collectIndeterminateMenuKeys(keys: Array<string | number>, nodes: TreeOption[]) {
    const selected = new Set(keys.map((key) => String(key)));
    const indeterminateKeys: string[] = [];
    const visit = (node: TreeOption): { anySelected: boolean; fullySelected: boolean } => {
      const key = String(node.key);
      const children = node.children || [];
      const selfSelected = selected.has(key);
      if (!children.length) return { anySelected: selfSelected, fullySelected: selfSelected };
      const childStates = children.map(visit);
      const anyChildSelected = childStates.some((state) => state.anySelected);
      const allChildrenFullySelected = childStates.every((state) => state.fullySelected);
      if (anyChildSelected && (!selfSelected || !allChildrenFullySelected)) {
        indeterminateKeys.push(key);
      }
      return {
        anySelected: selfSelected || anyChildSelected,
        fullySelected: selfSelected && allChildrenFullySelected,
      };
    };
    nodes.forEach(visit);
    return indeterminateKeys;
  }

  function collectNodeAndDescendantKeys(node: TreeOption) {
    const keys: string[] = [];
    const visit = (item: TreeOption) => {
      keys.push(String(item.key));
      item.children?.forEach(visit);
    };
    visit(node);
    return keys;
  }

  function applyTreeCheckUpdate(keys: Array<string | number>, meta?: TreeCheckMeta) {
    const selected = new Set(keys.map((key) => String(key)));
    if (!meta?.node?.children?.length) return Array.from(selected);
    collectNodeAndDescendantKeys(meta.node).forEach((key) => {
      if (meta.action === 'uncheck') selected.delete(key);
      else if (meta.action === 'check') selected.add(key);
    });
    return Array.from(selected);
  }

  async function ensureMenusLoaded() {
    if (menuRows.value.length) return;
    menusLoading.value = true;
    try {
      const response = await getRbacMenus({ scope: 'tenant' });
      menuRows.value = ((response as Recordable).items || []) as MenuRow[];
      expandedMenuKeys.value = collectNonLeafKeys(menuTree.value);
    } finally {
      menusLoading.value = false;
    }
  }

  async function reload(state?: ListRuntimeState) {
    currentState.value = state || currentState.value;
    loading.value = true;
    try {
      const response = (await getTenants({ ...runtimeListParams(currentState.value), q: query.value.trim() || undefined })) as Recordable;
      rows.value = (response.items || []) as TenantRow[];
      paginationTotal.value = Number(response.pagination?.total || rows.value.length);
    } finally {
      loading.value = false;
    }
  }

  function resetFilters() {
    query.value = '';
  }

  async function openTenantMenus(row: TenantRow) {
    currentTenant.value = row;
    menuModalVisible.value = true;
    checkedMenuKeys.value = [];
    savedMenuKeys.value = [];
    await ensureMenusLoaded();
    menusLoading.value = true;
    try {
      const response = (await getTenantMenuAssignments(row.id)) as TenantMenuAssignmentsData;
      checkedMenuKeys.value = [...(response.assigned_menu_keys || [])];
      savedMenuKeys.value = [...checkedMenuKeys.value];
      expandedMenuKeys.value = collectNonLeafKeys(menuTree.value);
    } finally {
      menusLoading.value = false;
    }
  }

  function handleCheckedMenuKeys(keys: Array<string | number>, _options?: TreeOption[], meta?: TreeCheckMeta) {
    checkedMenuKeys.value = applyTreeCheckUpdate(keys, meta);
  }

  function handleExpandedMenuKeys(keys: Array<string | number>) {
    expandedMenuKeys.value = keys.map((key) => String(key));
  }

  function toggleMenuTreeExpanded() {
    expandedMenuKeys.value = expandedMenuKeys.value.length ? [] : collectNonLeafKeys(menuTree.value);
  }

  function selectAllMenus() {
    checkedMenuKeys.value = collectTreeKeys(menuTree.value);
  }

  function invertMenus() {
    const selected = new Set(checkedMenuKeys.value);
    checkedMenuKeys.value = collectTreeKeys(menuTree.value).filter((key) => !selected.has(key));
  }

  function clearMenus() {
    checkedMenuKeys.value = [];
  }

  function resetSelection() {
    checkedMenuKeys.value = [...savedMenuKeys.value];
  }

  async function saveAssignments() {
    if (!currentTenant.value) return;
    saving.value = true;
    try {
      const response = await updateTenantMenuAssignments(currentTenant.value.id, checkedMenuKeys.value);
      checkedMenuKeys.value = [...(response.item?.assigned_menu_keys || checkedMenuKeys.value)];
      savedMenuKeys.value = [...checkedMenuKeys.value];
      message.success('租户菜单配置已保存');
      menuModalVisible.value = false;
    } finally {
      saving.value = false;
    }
  }

  reload();
</script>

<style scoped>
  .tenant-menu-assignment {
    width: 100%;
  }

  .tenant-menu-tree {
    box-sizing: border-box;
    height: min(520px, calc(100vh - 300px));
    min-height: 360px;
    padding: 8px 4px;
    overflow: auto;
    border: 1px solid var(--app-border-color);
    border-radius: var(--app-card-radius);
  }

  .tenant-menu-tree :deep(.n-spin-container),
  .tenant-menu-tree :deep(.n-spin-content),
  .tenant-menu-tree :deep(.n-tree) {
    height: 100%;
  }
</style>
