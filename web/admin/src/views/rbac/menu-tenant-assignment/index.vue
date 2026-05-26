<template>
  <div class="menu-tenant-assignment">
    <n-grid cols="1 m:3 xl:4" responsive="screen" :x-gap="12" :y-gap="12">
      <n-gi span="1">
        <n-card :bordered="false" size="small" class="menu-panel">
          <template #header>
            <n-space align="center" justify="space-between">
              <span>租户菜单</span>
              <n-button text size="small" :loading="menusLoading" @click="loadMenus">刷新</n-button>
            </n-space>
          </template>
          <n-input v-model:value="menuPattern" clearable placeholder="搜索菜单名称或 Key" />
          <n-space class="menu-panel__actions" size="small">
            <n-button size="small" quaternary @click="toggleMenuTreeExpanded">
              {{ expandedMenuKeys.length ? '收起全部' : '展开全部' }}
            </n-button>
          </n-space>
          <div class="menu-panel__tree">
            <n-spin :show="menusLoading">
              <n-tree
                block-line
                :data="menuTree"
                :pattern="menuPattern"
                :selected-keys="selectedMenuKey ? [selectedMenuKey] : []"
                :expanded-keys="expandedMenuKeys"
                virtual-scroll
                :scrollbar-props="{ style: { height: '100%' } }"
                class="menu-tree"
                @update:selected-keys="handleSelectMenu"
                @update:expanded-keys="(keys) => (expandedMenuKeys = keys.map(String))"
              />
            </n-spin>
          </div>
        </n-card>
      </n-gi>

      <n-gi span="1 m:2 xl:3">
        <ListPageRuntime
          :schema="assignmentPage"
          :rows="rows"
          :loading="loading"
          :pagination-total="paginationTotal"
          @refresh="reload"
        >
          <template #header-actions>
            <n-space>
              <n-button :disabled="!selectedMenuKey || !changed" @click="resetSelection">重置</n-button>
              <n-button
                v-if="hasPermission(['system:menus:assign_tenants'])"
                type="primary"
                :disabled="!selectedMenuKey || !changed"
                :loading="saving"
                @click="saveAssignments"
              >
                保存分配
              </n-button>
            </n-space>
          </template>
          <template #toolbar-left>
            <div class="assignment-context">
              <template v-if="selectedMenu">
                <span class="assignment-context__menu">
                  {{ selectedMenu.label || selectedMenu.key }}
                  <span class="assignment-context__key">{{ selectedMenu.key }}</span>
                </span>
                <span>已选 {{ selectedTenantIds.length }} 个租户</span>
                <span>本页 {{ selectedCurrentPageCount }}/{{ rows.length }}</span>
              </template>
              <span v-else>请选择左侧租户菜单</span>
            </div>
          </template>
        </ListPageRuntime>
      </n-gi>
    </n-grid>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, onMounted, ref } from 'vue';
  import { NCheckbox, NTag, useMessage } from 'naive-ui';
  import type { DataTableColumns, TreeOption } from 'naive-ui';
  import {
    getMenuTenantAssignments,
    getRbacMenus,
    updateMenuTenantAssignments,
    type MenuTenantAssignmentRow,
  } from '@/api/business';
  import { usePermission } from '@/hooks/web/usePermission';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';

  interface MenuRow extends Recordable {
    key: string;
    label: string;
    parent_key?: string;
    menu_type?: 'directory' | 'page' | 'action' | string;
    sort_order?: number;
    children?: MenuRow[];
  }

  const message = useMessage();
  const { hasPermission } = usePermission();
  const menusLoading = ref(false);
  const loading = ref(false);
  const saving = ref(false);
  const menuRows = ref<MenuRow[]>([]);
  const rows = ref<MenuTenantAssignmentRow[]>([]);
  const paginationTotal = ref(0);
  const selectedMenuKey = ref('');
  const menuPattern = ref('');
  const expandedMenuKeys = ref<string[]>([]);
  const selectedTenantIds = ref<number[]>([]);
  const savedTenantIds = ref<number[]>([]);
  const currentState = ref<ListRuntimeState>();

  const selectedMenu = computed(() => menuRows.value.find((item) => item.key === selectedMenuKey.value) || null);
  const canAssignTenants = computed(() => hasPermission(['system:menus:assign_tenants']));
  const currentPageTenantIds = computed(() => rows.value.map((row) => row.tenant_id));
  const selectedCurrentPageCount = computed(
    () => currentPageTenantIds.value.filter((tenantId) => selectedTenantIds.value.includes(tenantId)).length
  );
  const changed = computed(() => {
    const current = [...selectedTenantIds.value].sort((a, b) => a - b).join(',');
    const saved = [...savedTenantIds.value].sort((a, b) => a - b).join(',');
    return current !== saved;
  });

  const columns: DataTableColumns<MenuTenantAssignmentRow> = [
    {
      title: '启用',
      key: 'is_enabled',
      width: 84,
      fixed: 'left',
      render(row) {
        return h(NCheckbox, {
          checked: selectedTenantIds.value.includes(row.tenant_id),
          disabled: !hasPermission(['system:menus:assign_tenants']),
          onUpdateChecked: (checked: boolean) => toggleTenant(row.tenant_id, checked),
        });
      },
    },
    { title: '租户名称', key: 'tenant_name', minWidth: 180, ellipsis: { tooltip: true } },
    { title: '租户 Key', key: 'tenant_key', minWidth: 160, ellipsis: { tooltip: true } },
    {
      title: '租户状态',
      key: 'tenant_status',
      width: 120,
      render(row) {
        const active = row.tenant_status === 'active';
        return h(NTag, { size: 'small', type: active ? 'success' : 'warning', bordered: false }, () => (active ? '启用' : '停用'));
      },
    },
    {
      title: '分配状态',
      key: 'assignment',
      width: 130,
      render(row) {
        const enabled = selectedTenantIds.value.includes(row.tenant_id);
        return h(NTag, { size: 'small', type: enabled ? 'success' : 'default', bordered: false }, () => (enabled ? '已分配' : '未分配'));
      },
    },
    {
      title: '更新时间',
      key: 'update_time',
      width: 190,
      render: (row) => formatToDateTime(row.update_time),
    },
  ];

  const assignmentPage = defineListPage<MenuTenantAssignmentRow>({
    id: 'rbac.menuTenantAssignments',
    title: '菜单租户分配',
    description: '按菜单控制哪些租户可以使用对应的租户级菜单入口。',
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
      rowKey: (row) => row.tenant_id,
      scrollX: 920,
      sort: { remote: true },
      columnRuntime: {
        columns: [
          { key: 'is_enabled', required: true, sortable: false },
          { key: 'tenant_name', sortable: true },
          { key: 'tenant_key', sortable: true },
          { key: 'tenant_status', sortable: true },
          { key: 'assignment', sortable: false },
          { key: 'update_time', sortable: true },
        ],
      },
      tableProps: {
        size: 'small',
      },
    },
    toolbar: {
      batchActions: [
        { key: 'select-page', label: '本页全选', onClick: selectCurrentPage },
        { key: 'invert-page', label: '本页反选', onClick: invertCurrentPage },
        { key: 'clear-page', label: '清除本页', onClick: clearCurrentPage },
      ],
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  const menuTree = computed(() => buildMenuTree(menuRows.value.filter((menu) => menu.menu_type !== 'action')));

  function buildMenuTree(items: MenuRow[]) {
    const nodeMap = new Map<string, MenuRow>();
    const roots: MenuRow[] = [];
    items.forEach((item) => nodeMap.set(item.key, { ...item, children: [] }));
    nodeMap.forEach((node) => {
      const parentKey = String(node.parent_key || '');
      const parent = parentKey ? nodeMap.get(parentKey) : undefined;
      if (parent) {
        parent.children?.push(node);
      } else {
        roots.push(node);
      }
    });
    const normalize = (nodes: MenuRow[]): TreeOption[] =>
      nodes
        .sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0))
        .map((node) => ({
          key: node.key,
          label: `${node.label || node.key}`,
          children: node.children?.length ? normalize(node.children) : undefined,
        }));
    return normalize(roots);
  }

  function collectTreeKeys(nodes: TreeOption[]) {
    const keys: string[] = [];
    const visit = (items: TreeOption[]) => {
      items.forEach((item) => {
        keys.push(String(item.key));
        if (item.children?.length) visit(item.children);
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

  function syncExpandedMenuKeys() {
    expandedMenuKeys.value = collectNonLeafKeys(menuTree.value);
  }

  async function loadMenus() {
    menusLoading.value = true;
    try {
      const response = await getRbacMenus({ scope: 'tenant' });
      menuRows.value = ((response as Recordable).items || []) as MenuRow[];
      syncExpandedMenuKeys();
      if (!selectedMenuKey.value && menuRows.value.length) {
        const firstPage = menuRows.value.find((item) => item.menu_type !== 'action') || menuRows.value[0];
        selectedMenuKey.value = firstPage.key;
        await reload();
      }
    } finally {
      menusLoading.value = false;
    }
  }

  async function reload(state?: ListRuntimeState) {
    currentState.value = state || currentState.value;
    if (!selectedMenuKey.value) {
      rows.value = [];
      paginationTotal.value = 0;
      selectedTenantIds.value = [];
      savedTenantIds.value = [];
      return;
    }
    loading.value = true;
    try {
      const params = runtimeListParams(currentState.value);
      const response = await getMenuTenantAssignments(selectedMenuKey.value, params);
      rows.value = response.items || [];
      paginationTotal.value = Number(response.pagination?.total || 0);
      selectedTenantIds.value = [...(response.assigned_tenant_ids || [])].sort((a, b) => a - b);
      savedTenantIds.value = [...selectedTenantIds.value];
    } finally {
      loading.value = false;
    }
  }

  function handleSelectMenu(keys: Array<string | number>) {
    const nextKey = String(keys[0] || '');
    if (!nextKey || nextKey === selectedMenuKey.value) return;
    selectedMenuKey.value = nextKey;
    selectedTenantIds.value = [];
    savedTenantIds.value = [];
    reload();
  }

  function toggleTenant(tenantId: number, enabled: boolean) {
    const next = new Set(selectedTenantIds.value);
    if (enabled) {
      next.add(tenantId);
    } else {
      next.delete(tenantId);
    }
    selectedTenantIds.value = [...next].sort((a, b) => a - b);
  }

  function selectCurrentPage() {
    if (!selectedMenuKey.value || !canAssignTenants.value) return;
    rows.value.forEach((row) => toggleTenant(row.tenant_id, true));
  }

  function invertCurrentPage() {
    if (!selectedMenuKey.value || !canAssignTenants.value) return;
    rows.value.forEach((row) => toggleTenant(row.tenant_id, !selectedTenantIds.value.includes(row.tenant_id)));
  }

  function clearCurrentPage() {
    if (!selectedMenuKey.value || !canAssignTenants.value) return;
    rows.value.forEach((row) => toggleTenant(row.tenant_id, false));
  }

  function toggleMenuTreeExpanded() {
    expandedMenuKeys.value = expandedMenuKeys.value.length ? [] : collectNonLeafKeys(menuTree.value);
  }

  function resetSelection() {
    selectedTenantIds.value = [...savedTenantIds.value];
  }

  async function saveAssignments() {
    if (!selectedMenuKey.value) return;
    saving.value = true;
    try {
      await updateMenuTenantAssignments(selectedMenuKey.value, selectedTenantIds.value);
      message.success('菜单租户分配已保存');
      await reload(currentState.value);
    } finally {
      saving.value = false;
    }
  }

  onMounted(loadMenus);
</script>

<style scoped>
  .menu-tenant-assignment {
    width: 100%;
  }

  .menu-panel {
    min-height: 520px;
  }

  .menu-panel__actions {
    margin-top: 10px;
  }

  .menu-panel__tree {
    height: calc(100vh - 270px);
    min-height: 360px;
    margin-top: 12px;
    overflow: auto;
  }

  .menu-panel__tree :deep(.n-spin-container),
  .menu-panel__tree :deep(.n-spin-content),
  .menu-tree {
    height: 100%;
  }

  .assignment-context {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    align-items: center;
    min-height: 28px;
    color: var(--text-color-2);
    font-size: 13px;
  }

  .assignment-context__menu {
    color: var(--text-color-1);
    font-weight: 500;
  }

  .assignment-context__key {
    margin-left: 6px;
    color: var(--text-color-3);
    font-weight: 400;
  }
</style>
