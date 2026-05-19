<template>
  <div>
    <ListPageRuntime :schema="roleListPage" :rows="rows" :loading="loading" @refresh="reload">
      <template #header-actions>
        <n-button v-if="hasPermission(['system:roles:create'])" @click="handleCreate('tenant')">
          新增租户角色
        </n-button>
      </template>
    </ListPageRuntime>

    <n-modal v-model:show="roleModalVisible" preset="card" :style="{ width: '640px' }" :bordered="false">
      <template #header>
        <span>{{ roleModalTitle }}</span>
      </template>

      <n-alert v-if="editingSystemRole" type="warning" class="mb-4">
        系统角色只能调整名称和菜单权限，角色 Key 受到保护。
      </n-alert>

      <n-form
        ref="roleFormRef"
        :model="roleForm"
        :rules="roleRules"
        label-placement="left"
        :label-width="96"
      >
        <n-form-item label="角色名称" path="name">
          <n-input v-model:value="roleForm.name" placeholder="请输入角色名称" />
        </n-form-item>
        <n-form-item label="角色 Key" path="key">
          <n-input v-model:value="roleForm.key" placeholder="例如 ops-reviewer" :disabled="editingSystemRole" />
        </n-form-item>
        <n-form-item label="角色范围" path="role_scope">
          <n-radio-group v-model:value="roleForm.role_scope" :disabled="true">
            <n-radio-button value="platform">平台角色</n-radio-button>
            <n-radio-button value="tenant">租户角色</n-radio-button>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input
            v-model:value="roleForm.description"
            type="textarea"
            placeholder="请输入角色说明"
            :autosize="{ minRows: 3, maxRows: 5 }"
          />
        </n-form-item>
        <n-form-item label="菜单权限" path="menu_keys">
          <div class="role-menu-tree role-menu-tree--form">
            <n-spin :show="menusLoading">
              <n-tree
                block-line
                checkable
                :data="roleFormMenuTree"
                :checked-keys="roleForm.menu_keys"
                :indeterminate-keys="roleFormIndeterminateKeys"
                :expanded-keys="expandedMenuKeys"
                style="max-height: 300px; overflow: auto"
                @update:checked-keys="handleRoleMenuKeys"
                @update:expanded-keys="handleExpandedMenuKeys"
              />
            </n-spin>
          </div>
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="roleModalVisible = false">取消</n-button>
          <n-button @click="toggleMenuTreeExpanded">
            {{ expandedMenuKeys.length ? '收起全部' : '展开全部' }}
          </n-button>
          <n-button @click="selectAllRoleMenus">全选菜单</n-button>
          <n-button type="primary" :loading="savingRole" @click="submitRoleForm">{{ roleSubmitText }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="menuModalVisible" preset="card" :style="{ width: '640px' }" :bordered="false">
      <template #header>
        <span>配置 {{ currentRole?.name || currentRole?.key || '' }} 的菜单权限</span>
      </template>

      <div class="role-menu-tree">
        <n-spin :show="menusLoading">
          <n-tree
            block-line
            checkable
            :data="currentRoleMenuTree"
            :checked-keys="checkedMenuKeys"
            :indeterminate-keys="checkedMenuIndeterminateKeys"
            :expanded-keys="expandedMenuKeys"
            style="max-height: 460px; overflow: auto"
            @update:checked-keys="handleCheckedMenuKeys"
            @update:expanded-keys="handleExpandedMenuKeys"
          />
        </n-spin>
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button @click="toggleMenuTreeExpanded">
            {{ expandedMenuKeys.length ? '收起全部' : '展开全部' }}
          </n-button>
          <n-button @click="selectAllMenus">全选菜单</n-button>
          <n-button type="primary" :loading="savingMenus" @click="submitRoleMenus">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, TreeOption } from 'naive-ui';
  import {
    createRbacRole,
    deleteRbacRole,
    getRbacMenus,
    getRbacRoles,
    updateRbacRole,
    updateRbacRoleMenus,
  } from '@/api/business';
  import AppStatusGroup from '@/components/Application/AppStatusGroup.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { usePermission } from '@/hooks/web/usePermission';
  import { defineListPage, ListPageRuntime, runtimeSortParams, type ListRuntimeState } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';

  interface MenuRow extends Recordable {
    key: string;
    label: string;
    parent_key?: string;
    menu_type?: 'directory' | 'page' | 'action' | string;
    menu_scope?: 'platform' | 'tenant' | string;
    sort_order?: number;
    children?: MenuRow[];
  }

  interface RoleRow extends Recordable {
    id: number;
    key: string;
    name: string;
    description?: string;
    is_system?: boolean;
    menus?: MenuRow[];
    permissions?: Recordable[];
    role_scope?: 'platform' | 'tenant' | string;
    create_time?: string;
  }

  interface RoleFormState {
    id: number | null;
    key: string;
    name: string;
    description: string;
    role_scope: 'platform' | 'tenant';
    menu_keys: string[];
    is_system: boolean;
  }

  type TreeCheckMeta = {
    action?: 'check' | 'uncheck' | string;
    node?: TreeOption;
  };

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const menusLoading = ref(false);
  const savingMenus = ref(false);
  const savingRole = ref(false);
  const rows = ref<RoleRow[]>([]);
  const menuRows = ref<MenuRow[]>([]);
  const roleFormRef = ref<FormInst | null>(null);
  const roleModalVisible = ref(false);
  const menuModalVisible = ref(false);
  const currentRole = ref<RoleRow | null>(null);
  const checkedMenuKeys = ref<string[]>([]);
  const expandedMenuKeys = ref<string[]>([]);
  const roleFormMode = ref<'create' | 'edit'>('create');
  const roleForm = reactive<RoleFormState>({
    id: null,
    key: '',
    name: '',
    description: '',
    role_scope: 'platform',
    menu_keys: [],
    is_system: false,
  });

  const editingSystemRole = computed(() => roleFormMode.value === 'edit' && roleForm.is_system);
  const roleModalTitle = computed(() => {
    if (roleFormMode.value === 'edit') {
      return '编辑角色';
    }
    return roleForm.role_scope === 'tenant' ? '新增租户角色' : '新增角色';
  });
  const roleSubmitText = computed(() => (roleFormMode.value === 'create' ? '创建' : '保存'));
  const roleFormScope = computed(() => roleForm.role_scope);
  const currentRoleScope = computed(() => currentRole.value?.role_scope || 'platform');
  const roleFormMenuTree = computed(() => buildScopedMenuTree(roleFormScope.value));
  const currentRoleMenuTree = computed(() => buildScopedMenuTree(currentRoleScope.value));
  const roleFormIndeterminateKeys = computed(() => collectIndeterminateMenuKeys(roleForm.menu_keys, roleFormMenuTree.value));
  const checkedMenuIndeterminateKeys = computed(() => collectIndeterminateMenuKeys(checkedMenuKeys.value, currentRoleMenuTree.value));

  const roleRules: FormRules = {
    name: [{ required: true, message: '请输入角色名称', trigger: ['blur', 'input'] }],
    key: [
      { required: true, message: '请输入角色 Key', trigger: ['blur', 'input'] },
      {
        pattern: /^[A-Za-z0-9_-]+$/,
        message: '角色 Key 只能包含字母、数字、下划线和中划线',
        trigger: ['blur', 'input'],
      },
    ],
  };

  const columns: DataTableColumns<RoleRow> = [
    { title: 'ID', key: 'id', width: 80 },
    { title: '角色名称', key: 'name', width: 200 },
    { title: '角色 Key', key: 'key', width: 180 },
    { title: '描述', key: 'description', minWidth: 260, ellipsis: { tooltip: true } },
    {
      title: '状态',
      key: 'status',
      width: 240,
      render(row) {
        return h(AppStatusGroup, {
          items: [
            { statusKey: row.is_system ? 'system' : 'custom' },
            { statusKey: row.role_scope === 'tenant' ? 'tenant' : 'platform' },
            { statusKey: row.menus?.length ? 'assigned' : 'unassigned' },
          ],
        });
      },
    },
    {
      title: '创建时间',
      key: 'create_time',
      width: 200,
      render: (row) => formatToDateTime(row.create_time),
    },
    {
      title: '操作',
      key: 'actions',
      width: 280,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '菜单权限', tone: 'primary', show: hasPermission(['system:roles:assign_menus']), onClick: () => openMenuPermission(row) },
            { label: '编辑', show: hasPermission(['system:roles:update']), onClick: () => handleEdit(row) },
            {
              label: '删除',
              tone: 'danger',
              show: hasPermission(['system:roles:delete']),
              disabled: !!row.is_system,
              confirm: true,
              confirmTitle: '删除角色',
              confirmContent: `确认删除角色「${row.name || row.key}」？删除后不可恢复。`,
              positiveText: '删除',
              onConfirm: () => handleDelete(row),
            },
          ],
        });
      },
    },
  ];

  const roleListPage = defineListPage<RoleRow>({
    id: 'rbac.roles',
    title: '角色权限',
    description: '管理 RBAC 角色、角色范围和菜单权限。',
    variant: 'enterprise',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1440,
      sort: { remote: true },
      columnRuntime: {
        columns: [
          { key: 'id', sortable: true },
          { key: 'name', sortable: true },
          { key: 'key', sortable: true },
          { key: 'description', sortable: false },
          { key: 'status', sortable: false },
          { key: 'create_time', sortable: false },
          { key: 'actions', required: true, sortable: false },
        ],
      },
      tableProps: {
        size: 'small',
      },
    },
    toolbar: {
      primaryAction: hasPermission(['system:roles:create'])
        ? { key: 'create', label: '新增角色', type: 'primary', onClick: () => handleCreate('platform') }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function buildMenuTree(items: MenuRow[]) {
    const nodeMap = new Map<string, MenuRow>();
    const roots: MenuRow[] = [];

    items.forEach((item) => {
      nodeMap.set(item.key, { ...item, children: [] });
    });

    nodeMap.forEach((node) => {
      const parentKey = String(node.parent_key || '');
      const parent = parentKey ? nodeMap.get(parentKey) : undefined;
      if (parent) {
        parent.children?.push(node);
      } else {
        roots.push(node);
      }
    });

    const sortByOrder = (a: MenuRow, b: MenuRow) => Number(a.sort_order || 0) - Number(b.sort_order || 0);
    const normalize = (nodes: MenuRow[]): TreeOption[] =>
      nodes.sort(sortByOrder).map((node) => ({
        key: node.key,
        label: node.menu_type === 'action' ? `操作：${node.label || node.key}` : node.label || node.key,
        children: node.children?.length ? normalize(node.children) : undefined,
      }));

    return normalize(roots);
  }

  function buildScopedMenuTree(roleScope: string) {
    const scope = roleScope === 'tenant' ? 'tenant' : 'platform';
    return buildMenuTree(menuRows.value.filter((menu) => String(menu.menu_scope || 'tenant') === scope));
  }

  function collectTreeKeys(nodes: TreeOption[]) {
    const keys: string[] = [];
    const visit = (items: TreeOption[]) => {
      items.forEach((item) => {
        keys.push(String(item.key));
        if (item.children?.length) {
          visit(item.children);
        }
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

      if (!children.length) {
        return { anySelected: selfSelected, fullySelected: selfSelected };
      }

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

  function withAncestorMenuKeys(keys: Array<string | number>) {
    const selected = new Set(keys.map((key) => String(key)));
    const byKey = new Map(menuRows.value.map((menu) => [String(menu.key), menu]));
    Array.from(selected).forEach((key) => {
      let parentKey = String(byKey.get(key)?.parent_key || '');
      while (parentKey) {
        selected.add(parentKey);
        parentKey = String(byKey.get(parentKey)?.parent_key || '');
      }
    });
    return Array.from(selected);
  }

  async function ensureMenusLoaded() {
    if (menuRows.value.length) {
      return;
    }
    menusLoading.value = true;
    try {
      const payload = await getRbacMenus();
      menuRows.value = payload.items || [];
    } finally {
      menusLoading.value = false;
    }
  }

  function syncExpandedMenuKeys(nodes: TreeOption[]) {
    expandedMenuKeys.value = collectNonLeafKeys(nodes);
  }

  function resetRoleForm() {
    roleForm.id = null;
    roleForm.key = '';
    roleForm.name = '';
    roleForm.description = '';
    roleForm.role_scope = 'platform';
    roleForm.menu_keys = [];
    roleForm.is_system = false;
    roleFormRef.value?.restoreValidation();
  }

  function applyRoleToForm(row: RoleRow) {
    roleForm.id = row.id;
    roleForm.key = String(row.key || '');
    roleForm.name = String(row.name || '');
    roleForm.description = String(row.description || '');
    roleForm.role_scope = row.role_scope === 'tenant' ? 'tenant' : 'platform';
    roleForm.menu_keys = (row.menus || []).map((menu) => String(menu.key));
    roleForm.is_system = !!row.is_system;
    roleFormRef.value?.restoreValidation();
  }

  async function openMenuPermission(row: RoleRow) {
    await ensureMenusLoaded();
    currentRole.value = row;
    syncExpandedMenuKeys(currentRoleMenuTree.value);
    const availableKeys = new Set(collectTreeKeys(currentRoleMenuTree.value));
    const assignedMenuKeys = (row.menus || [])
      .map((menu) => String(menu.key))
      .filter((key) => availableKeys.has(key));
    checkedMenuKeys.value = assignedMenuKeys;
    menuModalVisible.value = true;
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
    if (!meta?.node?.children?.length) {
      return Array.from(selected);
    }

    collectNodeAndDescendantKeys(meta.node).forEach((key) => {
      if (meta.action === 'uncheck') {
        selected.delete(key);
      } else if (meta.action === 'check') {
        selected.add(key);
      }
    });
    return Array.from(selected);
  }

  function handleCheckedMenuKeys(keys: Array<string | number>, _options?: TreeOption[], meta?: TreeCheckMeta) {
    checkedMenuKeys.value = applyTreeCheckUpdate(keys, meta);
  }

  function handleExpandedMenuKeys(keys: Array<string | number>) {
    expandedMenuKeys.value = keys.map((key) => String(key));
  }

  function toggleMenuTreeExpanded() {
    const tree = menuModalVisible.value ? currentRoleMenuTree.value : roleFormMenuTree.value;
    expandedMenuKeys.value = expandedMenuKeys.value.length ? [] : collectNonLeafKeys(tree);
  }

  function selectAllMenus() {
    checkedMenuKeys.value = collectTreeKeys(currentRoleMenuTree.value);
  }

  function selectAllRoleMenus() {
    roleForm.menu_keys = collectTreeKeys(roleFormMenuTree.value);
  }

  function handleRoleMenuKeys(keys: Array<string | number>, _options?: TreeOption[], meta?: TreeCheckMeta) {
    roleForm.menu_keys = applyTreeCheckUpdate(keys, meta);
  }

  async function submitRoleForm() {
    try {
      await roleFormRef.value?.validate();
    } catch {
      return;
    }

    savingRole.value = true;
    try {
      const availableKeys = new Set(collectTreeKeys(roleFormMenuTree.value));
      const payload = {
        key: roleForm.key.trim(),
        name: roleForm.name.trim(),
        description: roleForm.description.trim(),
        menu_keys: withAncestorMenuKeys(roleForm.menu_keys).filter((key) => availableKeys.has(key)),
      };

      if (roleFormMode.value === 'create') {
        await createRbacRole({ ...payload, role_scope: roleForm.role_scope });
        message.success('角色创建成功');
      } else if (roleForm.id) {
        await updateRbacRole(roleForm.id, payload);
        message.success('角色保存成功');
      }

      roleModalVisible.value = false;
      resetRoleForm();
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '角色保存失败');
    } finally {
      savingRole.value = false;
    }
  }

  async function submitRoleMenus() {
    if (!currentRole.value) {
      return;
    }
    savingMenus.value = true;
    try {
      const availableKeys = new Set(collectTreeKeys(currentRoleMenuTree.value));
      const menuKeys = withAncestorMenuKeys(checkedMenuKeys.value).filter((key) => availableKeys.has(key));
      await updateRbacRoleMenus(currentRole.value.id, menuKeys);
      await reload();
      message.success('菜单权限保存成功');
      menuModalVisible.value = false;
    } catch (error) {
      message.error(error instanceof Error ? error.message : '菜单权限保存失败');
    } finally {
      savingMenus.value = false;
    }
  }

  async function handleCreate(roleScope: 'platform' | 'tenant' = 'platform') {
    await ensureMenusLoaded();
    roleFormMode.value = 'create';
    resetRoleForm();
    roleForm.role_scope = roleScope;
    syncExpandedMenuKeys(roleFormMenuTree.value);
    roleModalVisible.value = true;
  }

  async function handleEdit(row: RoleRow) {
    await ensureMenusLoaded();
    roleFormMode.value = 'edit';
    applyRoleToForm(row);
    syncExpandedMenuKeys(roleFormMenuTree.value);
    const availableKeys = new Set(collectTreeKeys(roleFormMenuTree.value));
    roleForm.menu_keys = roleForm.menu_keys.filter((key) => availableKeys.has(key));
    roleModalVisible.value = true;
  }

  function handleDelete(row: RoleRow) {
    if (row.is_system) {
      message.warning('系统角色不能删除');
      return;
    }

    return (async () => {
      try {
        await deleteRbacRole(row.id);
        if (currentRole.value?.id === row.id) {
          currentRole.value = null;
          menuModalVisible.value = false;
        }
        await reload();
        message.success('角色已删除');
      } catch (error) {
        message.error(error instanceof Error ? error.message : '角色删除失败');
        throw error;
      }
    })();
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const payload = await getRbacRoles(runtimeSortParams(state));
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>

<style lang="less" scoped>
  .role-menu-tree {
    min-height: 320px;
    padding: 8px 2px;

    &--form {
      box-sizing: border-box;
      width: 100%;
      min-height: 220px;
      padding: 10px 12px;
      border: 1px solid var(--app-border-color);
      border-radius: var(--app-card-radius);
    }
  }
</style>
