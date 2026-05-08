<template>
  <div>
    <div class="n-layout-page-header">
      <n-card :bordered="false" title="菜单管理">
        菜单类型统一为目录或页面。已挂角色的菜单可以编辑基础信息，但修改菜单类型、路径、父级前需要先解绑角色。
      </n-card>
    </div>

    <n-grid class="mt-4" cols="1 s:1 m:1 l:3 xl:3 2xl:3" responsive="screen" :x-gap="12">
      <n-gi span="1">
        <n-card :segmented="{ content: true }" :bordered="false" size="small">
          <template #header>
            <n-space>
              <n-dropdown trigger="hover" :options="addMenuOptions" @select="handleAddMenu">
                <n-button type="info" ghost icon-placement="right">
                  添加菜单
                  <template #icon>
                    <div class="flex items-center">
                      <n-icon size="14">
                        <DownOutlined />
                      </n-icon>
                    </div>
                  </template>
                </n-button>
              </n-dropdown>
              <n-button type="info" ghost icon-placement="left" @click="toggleExpanded">
                全部{{ expandedKeys.length ? '收起' : '展开' }}
                <template #icon>
                  <div class="flex items-center">
                    <n-icon size="14">
                      <AlignLeftOutlined />
                    </n-icon>
                  </div>
                </template>
              </n-button>
            </n-space>
          </template>

          <div class="w-full menu-tree-panel">
            <n-input v-model:value="pattern" placeholder="输入菜单名称搜索">
              <template #suffix>
                <n-icon size="18" class="cursor-pointer">
                  <SearchOutlined />
                </n-icon>
              </template>
            </n-input>

            <div class="py-3 menu-list">
              <div v-if="loading" class="flex items-center justify-center py-4">
                <n-spin size="medium" />
              </div>
              <n-tree
                v-else
                block-line
                :data="treeRows"
                :pattern="pattern"
                :selected-keys="selectedKeys"
                :expanded-keys="expandedKeys"
                style="max-height: 650px; overflow: auto"
                @update:selected-keys="handleSelectMenu"
                @update:expanded-keys="handleExpandedKeys"
              />
            </div>
          </div>
        </n-card>
      </n-gi>

      <n-gi span="2">
        <n-card :segmented="{ content: true }" :bordered="false" size="small">
          <template #header>
            <n-space>
              <n-icon size="18">
                <FormOutlined />
              </n-icon>
              <span>{{ formMode === 'create' ? '新增菜单' : currentTitle ? `编辑菜单：${currentTitle}` : '编辑菜单' }}</span>
            </n-space>
          </template>

          <n-alert v-if="!selectedMenuKey && formMode !== 'create'" type="info" closable>
            从菜单列表选择一项后，进行编辑。
          </n-alert>

          <n-alert v-if="menuLockedByRoles" type="warning" class="mb-4">
            当前菜单已挂载角色：{{ currentBoundRoleNames }}。基础信息可以编辑，但修改菜单类型、路径、父级，或删除菜单前需要先解绑相关角色。
          </n-alert>

          <n-form
            v-if="formVisible"
            ref="formRef"
            class="py-4"
            :model="formParams"
            :rules="rules"
            label-placement="left"
            :label-width="110"
          >
            <n-form-item label="菜单类型" path="menu_type">
              <n-radio-group v-model:value="formParams.menu_type" name="menuType" :disabled="structureLockedByRoles">
                <n-space>
                  <n-radio value="directory">目录</n-radio>
                  <n-radio value="page">页面</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>
            <n-form-item label="标题" path="label">
              <n-input v-model:value="formParams.label" placeholder="请输入菜单标题" />
            </n-form-item>
            <n-form-item label="菜单 Key" path="key">
              <n-input v-model:value="formParams.key" placeholder="例如 recommend-center" />
            </n-form-item>
            <n-form-item label="父级菜单" path="parent_key">
              <n-select
                v-model:value="formParams.parent_key"
                clearable
                :options="parentMenuOptions"
                placeholder="顶级菜单"
                :disabled="structureLockedByRoles"
              />
            </n-form-item>
            <n-form-item label="路径" path="path">
              <n-input
                v-model:value="formParams.path"
                placeholder="目录如 /settings，页面如 /recommend"
                :disabled="structureLockedByRoles"
              />
            </n-form-item>
            <n-form-item label="路由名" path="route_name">
              <n-input v-model:value="formParams.route_name" placeholder="为空时默认使用菜单 Key" />
            </n-form-item>
            <n-form-item v-if="formParams.menu_type === 'page'" label="组件路径" path="component">
              <n-input v-model:value="formParams.component" placeholder="例如 /recommend/index" />
            </n-form-item>
            <n-form-item label="图标" path="icon">
              <n-input v-model:value="formParams.icon" placeholder="例如 FileSearchOutlined" />
            </n-form-item>
            <n-form-item label="菜单权限" path="permission_code">
              <n-input v-model:value="formParams.permission_code" placeholder="例如 recommendation:access" />
            </n-form-item>
            <n-form-item label="排序" path="sort_order">
              <n-input-number v-model:value="formParams.sort_order" :min="0" :max="9999" />
            </n-form-item>
            <n-form-item label="显示状态" path="is_visible">
              <n-switch v-model:value="formParams.is_visible">
                <template #checked>显示</template>
                <template #unchecked>隐藏</template>
              </n-switch>
            </n-form-item>
            <n-form-item style="margin-left: 110px">
              <n-space>
                <n-button type="primary" :loading="saving" @click="handleSave">
                  {{ formMode === 'create' ? '创建菜单' : '保存修改' }}
                </n-button>
                <n-button @click="handleReset">重置</n-button>
                <n-button v-if="formMode === 'edit'" :disabled="menuLockedByRoles" @click="handleDelete">
                  删除
                </n-button>
              </n-space>
            </n-form-item>
          </n-form>

          <n-empty v-else class="py-10" description="请选择一个菜单，或点击添加菜单" />
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { useDialog, useMessage } from 'naive-ui';
  import type { DropdownOption, FormInst, FormRules, SelectOption, TreeOption } from 'naive-ui';
  import { AlignLeftOutlined, DownOutlined, FormOutlined, SearchOutlined } from '@vicons/antd';
  import { createRbacMenu, deleteRbacMenu, getRbacMenus, updateRbacMenu } from '@/api/business';
  import { useAsyncRouteStore } from '@/store/modules/asyncRoute';
  import { useUserStore } from '@/store/modules/user';

  interface BoundRole extends Recordable {
    id: number;
    key: string;
    name: string;
  }

  interface MenuRow extends Recordable {
    id: number;
    key: string;
    label: string;
    menu_type: 'directory' | 'page';
    path?: string;
    route_name?: string;
    component?: string;
    icon?: string;
    parent_key?: string;
    permission_code?: string;
    sort_order?: number;
    is_visible?: boolean;
    bound_roles?: BoundRole[];
    children?: MenuRow[];
  }

  interface MenuFormState {
    id: number | null;
    key: string;
    label: string;
    menu_type: 'directory' | 'page';
    path: string;
    route_name: string;
    component: string;
    icon: string;
    parent_key: string;
    permission_code: string;
    sort_order: number;
    is_visible: boolean;
    bound_roles: BoundRole[];
  }

  const message = useMessage();
  const dialog = useDialog();
  const asyncRouteStore = useAsyncRouteStore();
  const userStore = useUserStore();
  const formRef = ref<FormInst | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const rows = ref<MenuRow[]>([]);
  const pattern = ref('');
  const selectedKeys = ref<string[]>([]);
  const expandedKeys = ref<string[]>([]);
  const selectedMenuKey = ref('');
  const formMode = ref<'create' | 'edit'>('edit');

  const formParams = reactive<MenuFormState>({
    id: null,
    key: '',
    label: '',
    menu_type: 'page',
    path: '',
    route_name: '',
    component: '',
    icon: '',
    parent_key: '',
    permission_code: '',
    sort_order: 0,
    is_visible: true,
    bound_roles: [],
  });

  const rules: FormRules = {
    label: { required: true, message: '请输入菜单标题', trigger: 'blur' },
    key: { required: true, message: '请输入菜单 Key', trigger: 'blur' },
    menu_type: { required: true, message: '请选择菜单类型', trigger: 'change' },
    component: {
      validator: (_rule, value: string) => {
        if (formParams.menu_type === 'page' && !String(value || '').trim()) {
          return new Error('页面菜单必须填写组件路径');
        }
        return true;
      },
      trigger: ['blur', 'input'],
    },
    path: {
      validator: (_rule, value: string) => {
        if (formParams.menu_type === 'page' && !String(value || '').trim()) {
          return new Error('页面菜单必须填写路径');
        }
        return true;
      },
      trigger: ['blur', 'input'],
    },
  };

  const treeRows = computed<TreeOption[]>(() => buildMenuTree(rows.value));
  const formVisible = computed(() => formMode.value === 'create' || !!selectedMenuKey.value);
  const currentTitle = computed(() => formParams.label || '');
  const currentBoundRoleNames = computed(() =>
    (formParams.bound_roles || []).map((role) => role.name || role.key).join('、')
  );
  const menuLockedByRoles = computed(() => formMode.value === 'edit' && (formParams.bound_roles || []).length > 0);
  const structureLockedByRoles = computed(() => menuLockedByRoles.value);
  const addMenuOptions = computed<DropdownOption[]>(() => [
    { label: '添加顶级菜单', key: 'root' },
    {
      label: '添加子菜单',
      key: 'child',
      disabled: !selectedMenuKey.value || selectedMenuRow.value?.menu_type !== 'directory',
    },
  ]);

  const selectedMenuRow = computed(() => findMenuByKey(rows.value, selectedMenuKey.value));
  const parentMenuOptions = computed<SelectOption[]>(() => {
    const blocked = new Set<string>();
    if (formMode.value === 'edit' && formParams.key) {
      const descendants = collectDescendantKeys(rows.value, formParams.key);
      descendants.forEach((key) => blocked.add(key));
      blocked.add(formParams.key);
    }
    return rows.value
      .filter((item) => item.menu_type === 'directory' && !blocked.has(item.key))
      .map((item) => ({
        label: item.label,
        value: item.key,
      }));
  });

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
    const sortByOrder = (a: MenuRow, b: MenuRow) => Number(a.sort_order || 0) - Number(b.sort_order || 0);
    const normalize = (nodes: MenuRow[]): TreeOption[] =>
      nodes.sort(sortByOrder).map((node) => ({
        key: node.key,
        label: node.label,
        children: node.children?.length ? normalize(node.children) : undefined,
      }));
    return normalize(roots);
  }

  function collectExpandedKeys(items: MenuRow[]) {
    const parentKeys = new Set<string>();
    items.forEach((item) => {
      const parentKey = String(item.parent_key || '');
      if (parentKey) parentKeys.add(parentKey);
    });
    return Array.from(parentKeys);
  }

  function findMenuByKey(items: MenuRow[], key: string): MenuRow | null {
    for (const item of items) {
      if (item.key === key) return item;
      if (item.children?.length) {
        const found = findMenuByKey(item.children, key);
        if (found) return found;
      }
    }
    return null;
  }

  function collectDescendantKeys(items: MenuRow[], key: string) {
    const childrenByParent = new Map<string, string[]>();
    items.forEach((item) => {
      const parentKey = String(item.parent_key || '');
      childrenByParent.set(parentKey, [...(childrenByParent.get(parentKey) || []), item.key]);
    });
    const keys: string[] = [];
    const visit = (parentKey: string) => {
      for (const childKey of childrenByParent.get(parentKey) || []) {
        keys.push(childKey);
        visit(childKey);
      }
    };
    visit(key);
    return keys;
  }

  function resetForm() {
    formParams.id = null;
    formParams.key = '';
    formParams.label = '';
    formParams.menu_type = 'page';
    formParams.path = '';
    formParams.route_name = '';
    formParams.component = '';
    formParams.icon = '';
    formParams.parent_key = '';
    formParams.permission_code = '';
    formParams.sort_order = 0;
    formParams.is_visible = true;
    formParams.bound_roles = [];
    formRef.value?.restoreValidation();
  }

  function syncForm(menu: MenuRow) {
    formMode.value = 'edit';
    selectedMenuKey.value = menu.key;
    selectedKeys.value = [menu.key];
    formParams.id = menu.id;
    formParams.key = menu.key;
    formParams.label = menu.label || '';
    formParams.menu_type = menu.menu_type || 'page';
    formParams.path = menu.path || '';
    formParams.route_name = menu.route_name || '';
    formParams.component = menu.component || '';
    formParams.icon = menu.icon || '';
    formParams.parent_key = menu.parent_key || '';
    formParams.permission_code = menu.permission_code || '';
    formParams.sort_order = Number(menu.sort_order || 0);
    formParams.is_visible = menu.is_visible !== false;
    formParams.bound_roles = [...(menu.bound_roles || [])];
    formRef.value?.restoreValidation();
  }

  function startCreate(parentKey = '') {
    formMode.value = 'create';
    selectedMenuKey.value = '';
    selectedKeys.value = [];
    resetForm();
    formParams.parent_key = parentKey;
    formParams.menu_type = parentKey ? 'page' : 'directory';
  }

  function handleSelectMenu(keys: string[]) {
    const key = keys[0];
    selectedKeys.value = keys;
    if (!key) {
      selectedMenuKey.value = '';
      return;
    }
    const menu = findMenuByKey(rows.value, key);
    if (menu) syncForm(menu);
  }

  function handleExpandedKeys(keys: string[]) {
    expandedKeys.value = keys;
  }

  function toggleExpanded() {
    expandedKeys.value = expandedKeys.value.length ? [] : collectExpandedKeys(rows.value);
  }

  function handleAddMenu(key: string) {
    if (key === 'root') {
      startCreate('');
      return;
    }
    const menu = selectedMenuRow.value;
    if (!menu) {
      message.warning('请先选择一个父级菜单');
      return;
    }
    if (menu.menu_type !== 'directory') {
      message.warning('只有目录类型菜单可以添加子菜单');
      return;
    }
    startCreate(menu.key);
  }

  async function handleSave() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }

    saving.value = true;
    try {
      const payload = {
        key: formParams.key.trim(),
        label: formParams.label.trim(),
        menu_type: formParams.menu_type,
        path: formParams.path.trim(),
        route_name: formParams.route_name.trim(),
        component: formParams.component.trim(),
        icon: formParams.icon.trim(),
        parent_key: formParams.parent_key.trim(),
        permission_code: formParams.permission_code.trim(),
        sort_order: Number(formParams.sort_order || 0),
        is_visible: !!formParams.is_visible,
      };

      if (formMode.value === 'create') {
        await createRbacMenu(payload);
        message.success('菜单已创建');
        startCreate('');
      } else if (formParams.id) {
        await updateRbacMenu(formParams.id, payload);
        message.success('菜单已更新');
      }

      await refreshDynamicMenus();
      await reload(formParams.key);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '菜单保存失败');
    } finally {
      saving.value = false;
    }
  }

  function handleReset() {
    if (formMode.value === 'create') {
      startCreate(formParams.parent_key);
      return;
    }
    const menu = selectedMenuRow.value;
    if (menu) syncForm(menu);
  }

  function handleDelete() {
    if (!formParams.id) return;
    dialog.warning({
      title: '删除菜单',
      content: `确认删除菜单「${formParams.label || formParams.key}」吗？`,
      positiveText: '删除',
      negativeText: '取消',
      async onPositiveClick() {
        try {
          await deleteRbacMenu(formParams.id as number);
          message.success('菜单已删除');
          startCreate('');
          await refreshDynamicMenus();
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '菜单删除失败');
          throw error;
        }
      },
    });
  }

  async function reload(selectKey = '') {
    loading.value = true;
    try {
      const payload = await getRbacMenus();
      rows.value = payload.items || [];
      expandedKeys.value = collectExpandedKeys(rows.value);
      const targetKey = selectKey || selectedMenuKey.value;
      if (targetKey) {
        const next = findMenuByKey(rows.value, targetKey);
        if (next) {
          syncForm(next);
          return;
        }
      }
      if (formMode.value !== 'create') {
        selectedKeys.value = [];
        selectedMenuKey.value = '';
        resetForm();
      }
    } finally {
      loading.value = false;
    }
  }

  async function refreshDynamicMenus() {
    const userInfo = await userStore.getInfo();
    await asyncRouteStore.generateRoutes(userInfo);
  }

  reload();
</script>
