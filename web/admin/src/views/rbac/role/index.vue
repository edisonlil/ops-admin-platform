<template>
  <div>
    <div class="n-layout-page-header">
      <n-card :bordered="false" title="角色权限管理">
        角色由后端 RBAC 统一维护，这里支持新增、编辑、菜单授权调整与删除。
      </n-card>
    </div>

    <n-card :bordered="false" size="small" class="proCard mt-4">
      <template #header>
        <n-button type="primary" @click="handleCreate">
          <template #icon>
            <n-icon>
              <PlusOutlined />
            </n-icon>
          </template>
          新增角色
        </n-button>
      </template>

      <n-data-table
        size="small"
        :columns="columns"
        :data="rows"
        :loading="loading"
        :row-key="(row) => row.id"
        :pagination="{ pageSize: 20 }"
      />
    </n-card>

    <n-modal v-model:show="roleModalVisible" preset="card" :style="{ width: '640px' }" :bordered="false">
      <template #header>
        <span>{{ roleModalTitle }}</span>
      </template>

      <n-alert v-if="editingSystemRole" type="warning" class="mb-4">
        系统角色允许修改名称、说明和菜单权限，但不允许修改角色 Key。
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
          <n-input
            v-model:value="roleForm.key"
            placeholder="例如 ops-reviewer"
            :disabled="editingSystemRole"
          />
        </n-form-item>
        <n-form-item label="说明" path="description">
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
                cascade
                checkable
                :data="roleFormMenuTree"
                :checked-keys="roleForm.menu_keys"
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
          <n-button @click="toggleMenuTreeExpanded">全部{{ expandedMenuKeys.length ? '收起' : '展开' }}</n-button>
          <n-button @click="selectAllRoleMenus">全部选择</n-button>
          <n-button type="primary" :loading="savingRole" @click="submitRoleForm">{{ roleSubmitText }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="menuModalVisible" preset="card" :style="{ width: '640px' }" :bordered="false">
      <template #header>
        <span>分配 {{ currentRole?.name || currentRole?.key || '' }} 的菜单权限</span>
      </template>

      <div class="role-menu-tree">
        <n-spin :show="menusLoading">
          <n-tree
            block-line
            cascade
            checkable
            :data="currentRoleMenuTree"
            :checked-keys="checkedMenuKeys"
            :expanded-keys="expandedMenuKeys"
            style="max-height: 460px; overflow: auto"
            @update:checked-keys="handleCheckedMenuKeys"
            @update:expanded-keys="handleExpandedMenuKeys"
          />
        </n-spin>
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button @click="toggleMenuTreeExpanded">全部{{ expandedMenuKeys.length ? '收起' : '展开' }}</n-button>
          <n-button @click="selectAllMenus">全部选择</n-button>
          <n-button type="primary" :loading="savingMenus" @click="submitRoleMenus">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { NButton, NSpace, NTag, useDialog, useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, TreeOption } from 'naive-ui';
  import { PlusOutlined } from '@vicons/antd';
  import {
    createRbacRole,
    deleteRbacRole,
    getRbacMenus,
    getRbacRoles,
    updateRbacRole,
    updateRbacRoleMenus,
  } from '@/api/business';
  import { formatToDateTime } from '@/utils/dateUtil';

  interface MenuRow extends Recordable {
    key: string;
    label: string;
    parent_key?: string;
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
    created_at?: string;
  }

  interface RoleFormState {
    id: number | null;
    key: string;
    name: string;
    description: string;
    menu_keys: string[];
    is_system: boolean;
  }

  const message = useMessage();
  const dialog = useDialog();
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
    menu_keys: [],
    is_system: false,
  });

  const editingSystemRole = computed(() => roleFormMode.value === 'edit' && roleForm.is_system);
  const roleModalTitle = computed(() => (roleFormMode.value === 'create' ? '新增角色' : '编辑角色'));
  const roleSubmitText = computed(() => (roleFormMode.value === 'create' ? '提交' : '保存'));
  const roleFormScope = computed(() => {
    if (roleFormMode.value === 'edit' && roleForm.id) {
      return rows.value.find((row) => row.id === roleForm.id)?.role_scope || 'platform';
    }
    return 'platform';
  });
  const currentRoleScope = computed(() => currentRole.value?.role_scope || 'platform');
  const roleFormMenuTree = computed(() => buildScopedMenuTree(roleFormScope.value));
  const currentRoleMenuTree = computed(() => buildScopedMenuTree(currentRoleScope.value));

  const roleRules: FormRules = {
    name: [{ required: true, message: '请输入角色名称', trigger: ['blur', 'input'] }],
    key: [
      { required: true, message: '请输入角色 Key', trigger: ['blur', 'input'] },
      {
        pattern: /^[A-Za-z0-9_-]+$/,
        message: '角色 Key 仅支持字母、数字、下划线和中划线',
        trigger: ['blur', 'input'],
      },
    ],
  };

  const columns: DataTableColumns<RoleRow> = [
    { title: 'ID', key: 'id', width: 90 },
    { title: '角色名称', key: 'name', width: 180 },
    { title: '角色 Key', key: 'key', width: 180 },
    { title: '说明', key: 'description', minWidth: 220, ellipsis: { tooltip: true } },
    {
      title: '是否系统角色',
      key: 'is_system',
      width: 130,
      render(row) {
        return h(NTag, { size: 'small', type: row.is_system ? 'success' : 'error' }, () =>
          row.is_system ? '是' : '否'
        );
      },
    },
    {
      title: '创建时间',
      key: 'created_at',
      width: 190,
      render: (row) => formatToDateTime(row.created_at),
    },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      fixed: 'right',
      render(row) {
        return h(
          NSpace,
          { size: 8 },
          {
            default: () => [
              h(
                NButton,
                { size: 'small', type: 'primary', ghost: true, onClick: () => openMenuPermission(row) },
                () => '菜单权限'
              ),
              h(NButton, { size: 'small', onClick: () => handleEdit(row) }, () => '编辑'),
              h(
                NButton,
                {
                  size: 'small',
                  disabled: !!row.is_system,
                  onClick: () => handleDelete(row),
                },
                () => '删除'
              ),
            ],
          }
        );
      },
    },
  ];

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
        label: node.label || node.key,
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
    roleForm.menu_keys = [];
    roleForm.is_system = false;
    roleFormRef.value?.restoreValidation();
  }

  function applyRoleToForm(row: RoleRow) {
    roleForm.id = row.id;
    roleForm.key = String(row.key || '');
    roleForm.name = String(row.name || '');
    roleForm.description = String(row.description || '');
    roleForm.menu_keys = (row.menus || []).map((menu) => String(menu.key));
    roleForm.is_system = !!row.is_system;
    roleFormRef.value?.restoreValidation();
  }

  async function openMenuPermission(row: RoleRow) {
    await ensureMenusLoaded();
    currentRole.value = row;
    syncExpandedMenuKeys(currentRoleMenuTree.value);
    const availableKeys = new Set(collectTreeKeys(currentRoleMenuTree.value));
    checkedMenuKeys.value = (row.menus || [])
      .map((menu) => String(menu.key))
      .filter((key) => availableKeys.has(key));
    menuModalVisible.value = true;
  }

  function handleCheckedMenuKeys(keys: Array<string | number>) {
    checkedMenuKeys.value = keys.map((key) => String(key));
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

  function handleRoleMenuKeys(keys: Array<string | number>) {
    roleForm.menu_keys = keys.map((key) => String(key));
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
        menu_keys: roleForm.menu_keys.filter((key) => availableKeys.has(key)),
      };

      if (roleFormMode.value === 'create') {
        await createRbacRole(payload);
        message.success('角色已新增');
      } else if (roleForm.id) {
        await updateRbacRole(roleForm.id, payload);
        message.success('角色已更新');
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
      await updateRbacRoleMenus(currentRole.value.id, checkedMenuKeys.value);
      await reload();
      message.success('菜单权限已保存');
      menuModalVisible.value = false;
    } catch (error) {
      message.error(error instanceof Error ? error.message : '菜单权限保存失败');
    } finally {
      savingMenus.value = false;
    }
  }

  async function handleCreate() {
    await ensureMenusLoaded();
    roleFormMode.value = 'create';
    resetRoleForm();
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
      message.warning('系统角色不允许删除');
      return;
    }

    dialog.warning({
      title: '删除角色',
      content: `确认删除角色「${row.name || row.key}」吗？相关用户角色关联也会被移除。`,
      positiveText: '删除',
      negativeText: '取消',
      async onPositiveClick() {
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
      },
    });
  }

  async function reload() {
    loading.value = true;
    try {
      const payload = await getRbacRoles();
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
      width: 100%;
      min-height: 220px;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      padding: 10px 12px;
    }
  }
</style>
