<template>
  <div>
    <ListPageRuntime :schema="menuListPage" :rows="rows" :loading="loading" @refresh="reload">
      <template #collection>
        <n-grid cols="1 s:1 m:1 l:3 xl:3 2xl:3" responsive="screen" :x-gap="12" :y-gap="12">
          <n-gi span="1" class="menu-tree-column">
            <n-card class="menu-tree-card" :segmented="{ content: true }" :bordered="false" size="small">
              <template #header>
                <n-space>
                  <n-dropdown trigger="hover" :options="addMenuOptions" @select="handleAddMenu">
                    <button class="menu-panel-action" type="button">
                      新增菜单
                      <n-icon size="14">
                        <DownOutlined />
                      </n-icon>
                    </button>
                  </n-dropdown>
                  <button class="menu-panel-action" type="button" @click="toggleExpanded">
                    {{ expandedKeys.length ? '收起全部' : '展开全部' }}
                    <n-icon size="14">
                      <AlignLeftOutlined />
                    </n-icon>
                  </button>
                </n-space>
              </template>

              <div class="w-full menu-tree-panel">
                <n-radio-group
                  :value="activeScope"
                  class="menu-scope-switch"
                  name="menuScopeSwitch"
                  @update:value="handleScopeChange"
                >
                  <n-radio-button value="platform">平台菜单</n-radio-button>
                  <n-radio-button value="tenant">租户菜单</n-radio-button>
                </n-radio-group>

                <n-input v-model:value="pattern" placeholder="搜索菜单名称">
                  <template #suffix>
                    <n-icon size="18" class="cursor-pointer">
                      <SearchOutlined />
                    </n-icon>
                  </template>
                </n-input>

                <div class="py-3 menu-list">
                  <div v-if="loading" class="menu-list-loading">
                    <n-spin size="medium" />
                  </div>
                  <n-tree
                    v-else
                    block-line
                    :data="treeRows"
                    :pattern="pattern"
                    virtual-scroll
                    :scrollbar-props="{ style: { height: '100%' } }"
                    :selected-keys="selectedKeys"
                    :expanded-keys="expandedKeys"
                    class="menu-tree"
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
                请从左侧选择菜单，或点击新增菜单开始配置。
              </n-alert>

              <n-alert v-if="menuLockedByRoles" type="warning" class="mb-4">
                当前菜单已绑定角色：{{ currentBoundRoleNames }}。绑定后仍可调整父级和排序，菜单类型与路径保持只读。
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
                      <n-radio value="action">按钮/操作</n-radio>
                    </n-space>
                  </n-radio-group>
                </n-form-item>
                <n-form-item label="菜单范围" path="menu_scope">
                  <n-radio-group v-model:value="formParams.menu_scope" name="menuScope" disabled>
                    <n-space>
                      <n-radio value="platform">平台</n-radio>
                      <n-radio value="tenant">租户</n-radio>
                    </n-space>
                  </n-radio-group>
                </n-form-item>
                <n-form-item label="名称" path="label">
                  <n-input v-model:value="formParams.label" placeholder="请输入菜单名称" />
                </n-form-item>
                <n-form-item label="菜单 Key" path="key">
                  <n-input v-model:value="formParams.key" placeholder="例如 recommend-center" />
                </n-form-item>
                <n-form-item label="父级菜单" path="parent_key">
                  <n-select
                    :value="formParams.parent_key"
                    clearable
                    :options="parentMenuOptions"
                    placeholder="选择父级菜单"
                    @update:value="handleParentKeyChange"
                  />
                </n-form-item>
                <n-form-item v-if="formParams.menu_type !== 'action'" label="路径" path="path">
                  <n-input
                    v-model:value="formParams.path"
                    placeholder="目录可填 /settings，页面例如 /recommend"
                    :disabled="structureLockedByRoles"
                  />
                </n-form-item>
                <n-form-item v-if="formParams.menu_type !== 'action'" label="路由名称" path="route_name">
                  <n-input v-model:value="formParams.route_name" placeholder="页面路由名称 Key" />
                </n-form-item>
                <n-form-item v-if="formParams.menu_type === 'page'" label="组件路径" path="component">
                  <n-input v-model:value="formParams.component" placeholder="例如 /recommend/index" />
                </n-form-item>
                <n-form-item v-if="formParams.menu_type !== 'action'" label="图标" path="icon">
                  <div class="menu-icon-field">
                    <button class="menu-icon-trigger" type="button" @click="openIconPicker">
                      <span class="menu-icon-trigger__preview">
                        <n-icon v-if="selectedIconOption" size="18">
                          <component :is="selectedIconOption.iconComponent" />
                        </n-icon>
                      </span>
                      <span class="menu-icon-trigger__text">
                        <span class="menu-icon-trigger__label">{{ selectedIconOption?.label || '选择菜单图标' }}</span>
                        <span v-if="formParams.icon" class="menu-icon-trigger__key">{{ formParams.icon }}</span>
                      </span>
                    </button>
                    <n-button v-if="formParams.icon" quaternary size="small" @click="clearIcon">清除</n-button>
                  </div>
                </n-form-item>
                <n-form-item label="权限码" path="permission_code">
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
                <n-form-item class="menu-form-actions">
                  <n-space>
                    <n-button
                      v-if="formMode === 'create' ? hasPermission(['system:menus:create']) : hasPermission(['system:menus:update'])"
                      type="primary"
                      :loading="saving"
                      @click="handleSave"
                    >
                      {{ formMode === 'create' ? '创建菜单' : '保存修改' }}
                    </n-button>
                    <n-button @click="handleReset">重置</n-button>
                    <n-button
                      v-if="formMode === 'edit' && hasPermission(['system:menus:delete'])"
                      :disabled="menuLockedByRoles"
                      @click="handleDelete"
                    >
                      删除
                    </n-button>
                  </n-space>
                </n-form-item>
              </n-form>

              <n-empty v-else class="py-10" description="请选择菜单或新建菜单" />
            </n-card>
          </n-gi>
        </n-grid>
      </template>
    </ListPageRuntime>

    <n-modal v-model:show="iconPickerVisible" preset="card" title="图标选择器" class="menu-icon-picker">
      <n-input v-model:value="iconSearch" clearable placeholder="搜索图标名称或 key">
        <template #prefix>
          <n-icon size="16">
            <SearchOutlined />
          </n-icon>
        </template>
      </n-input>
      <div class="menu-icon-grid" role="listbox">
        <button
          v-for="option in filteredIconOptions"
          :key="option.value"
          class="menu-icon-cell"
          :class="{ 'is-selected': formParams.icon === option.value }"
          type="button"
          :title="`${option.label} ${option.value}`"
          role="option"
          :aria-selected="formParams.icon === option.value"
          @click="selectIcon(option.value)"
        >
          <n-icon size="22">
            <component :is="option.iconComponent" />
          </n-icon>
          <span>{{ option.label }}</span>
        </button>
      </div>
      <template #footer>
        <n-space justify="space-between" align="center">
          <span class="menu-icon-picker__hint">{{ filteredIconOptions.length }} 个可选图标</span>
          <n-button @click="iconPickerVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { useDialog, useMessage } from 'naive-ui';
  import type { DropdownOption, FormInst, FormRules, SelectOption, TreeOption } from 'naive-ui';
  import {
    ApiOutlined,
    ApartmentOutlined,
    AppstoreOutlined,
    BgColorsOutlined,
    BellOutlined,
    BookOutlined,
    BugOutlined,
    BuildOutlined,
    CalendarOutlined,
    CloudOutlined,
    CodeOutlined,
    ControlOutlined,
    DashboardOutlined,
    DatabaseOutlined,
    DeploymentUnitOutlined,
    DesktopOutlined,
    EditOutlined,
    ExperimentOutlined,
    FileDoneOutlined,
    FileSearchOutlined,
    FileTextOutlined,
    FolderOutlined,
    HomeOutlined,
    InboxOutlined,
    KeyOutlined,
    LockOutlined,
    MailOutlined,
    MenuOutlined,
    MessageOutlined,
    NotificationOutlined,
    PartitionOutlined,
    PieChartOutlined,
    ProfileOutlined,
    ProjectOutlined,
    ReadOutlined,
    SafetyCertificateOutlined,
    ScheduleOutlined,
    SettingOutlined,
    ShopOutlined,
    SlidersOutlined,
    SolutionOutlined,
    TeamOutlined,
    ToolOutlined,
    UserOutlined,
    UsergroupAddOutlined,
    AlignLeftOutlined,
    DownOutlined,
    FormOutlined,
    SearchOutlined,
  } from '@vicons/antd';
  import { createRbacMenu, deleteRbacMenu, getRbacMenus, updateRbacMenu } from '@/api/business';
  import { usePermission } from '@/hooks/web/usePermission';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';

  interface BoundRole extends Recordable {
    id: number;
    key: string;
    name: string;
  }

  interface MenuRow extends Recordable {
    id: number;
    key: string;
    label: string;
    menu_scope?: 'platform' | 'tenant' | string;
    menu_type: 'directory' | 'page' | 'action';
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
    menu_scope: 'platform' | 'tenant';
    menu_type: 'directory' | 'page' | 'action';
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

  type MenuScope = 'platform' | 'tenant';

  const message = useMessage();
  const dialog = useDialog();
  const { hasPermission } = usePermission();
  const formRef = ref<FormInst | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const rows = ref<MenuRow[]>([]);
  const activeScope = ref<MenuScope>('platform');
  const pattern = ref('');
  const selectedKeys = ref<string[]>([]);
  const expandedKeys = ref<string[]>([]);
  const selectedMenuKey = ref('');
  const formMode = ref<'create' | 'edit'>('edit');
  const iconPickerVisible = ref(false);
  const iconSearch = ref('');

  const formParams = reactive<MenuFormState>({
    id: null,
    key: '',
    label: '',
    menu_scope: 'platform',
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

  const menuListPage = defineListPage<MenuRow>({
    id: 'rbac.menus',
    title: '菜单管理',
    description: '管理后台菜单结构、路由配置和权限码。',
    variant: 'enterprise',
    density: 'comfortable',
    view: {
      type: 'split-list',
      itemKey: 'key',
    },
    toolbar: {
      rightTools: ['refresh'],
    },
    pagination: false,
  });

  const rules: FormRules = {
    label: { required: true, message: '请输入菜单名称', trigger: 'blur' },
    key: { required: true, message: '请输入菜单 Key', trigger: 'blur' },
    menu_type: { required: true, message: '请选择菜单类型', trigger: 'change' },
    menu_scope: { required: true, message: '请选择菜单范围', trigger: 'change' },
    component: {
      validator: (_rule, value: string) => {
        if (formParams.menu_type === 'page' && !String(value || '').trim()) {
          return new Error('页面菜单必须配置组件路径');
        }
        return true;
      },
      trigger: ['blur', 'input'],
    },
    path: {
      validator: (_rule, value: string) => {
        if (formParams.menu_type === 'page' && !String(value || '').trim()) {
          return new Error('页面菜单必须配置路径');
        }
        return true;
      },
      trigger: ['blur', 'input'],
    },
  };

  const treeRows = computed<TreeOption[]>(() => buildMenuTree(rows.value));
  const formVisible = computed(() => formMode.value === 'create' || !!selectedMenuKey.value);
  const currentTitle = computed(() => formParams.label || '');
  const activeScopeLabel = computed(() => (activeScope.value === 'tenant' ? '租户' : '平台'));
  const currentBoundRoleNames = computed(() => (formParams.bound_roles || []).map((role) => role.name || role.key).join('、'));
  const menuLockedByRoles = computed(() => formMode.value === 'edit' && (formParams.bound_roles || []).length > 0);
  const structureLockedByRoles = computed(() => menuLockedByRoles.value);
  const addMenuOptions = computed<DropdownOption[]>(() => [
    { label: `新增${activeScopeLabel.value}根菜单`, key: 'root', disabled: !hasPermission(['system:menus:create']) },
    {
      label: '新增子菜单',
      key: 'child',
      disabled: !hasPermission(['system:menus:create']) || !selectedMenuKey.value || selectedMenuRow.value?.menu_type === 'action',
    },
  ]);

  const iconOptions = [
    { label: '接口', value: 'ApiOutlined', iconComponent: ApiOutlined },
    { label: '租户', value: 'ApartmentOutlined', iconComponent: ApartmentOutlined },
    { label: '应用', value: 'AppstoreOutlined', iconComponent: AppstoreOutlined },
    { label: '主题', value: 'BgColorsOutlined', iconComponent: BgColorsOutlined },
    { label: '通知', value: 'BellOutlined', iconComponent: BellOutlined },
    { label: '文册', value: 'BookOutlined', iconComponent: BookOutlined },
    { label: '问题', value: 'BugOutlined', iconComponent: BugOutlined },
    { label: '构建', value: 'BuildOutlined', iconComponent: BuildOutlined },
    { label: '日历', value: 'CalendarOutlined', iconComponent: CalendarOutlined },
    { label: '云端', value: 'CloudOutlined', iconComponent: CloudOutlined },
    { label: '代码', value: 'CodeOutlined', iconComponent: CodeOutlined },
    { label: '控制', value: 'ControlOutlined', iconComponent: ControlOutlined },
    { label: '看板', value: 'DashboardOutlined', iconComponent: DashboardOutlined },
    { label: '数据', value: 'DatabaseOutlined', iconComponent: DatabaseOutlined },
    { label: '部署', value: 'DeploymentUnitOutlined', iconComponent: DeploymentUnitOutlined },
    { label: '桌面', value: 'DesktopOutlined', iconComponent: DesktopOutlined },
    { label: '编辑', value: 'EditOutlined', iconComponent: EditOutlined },
    { label: '实验', value: 'ExperimentOutlined', iconComponent: ExperimentOutlined },
    { label: '完成', value: 'FileDoneOutlined', iconComponent: FileDoneOutlined },
    { label: '记录', value: 'FileSearchOutlined', iconComponent: FileSearchOutlined },
    { label: '文档', value: 'FileTextOutlined', iconComponent: FileTextOutlined },
    { label: '文件夹', value: 'FolderOutlined', iconComponent: FolderOutlined },
    { label: '首页', value: 'HomeOutlined', iconComponent: HomeOutlined },
    { label: '收件', value: 'InboxOutlined', iconComponent: InboxOutlined },
    { label: '密钥', value: 'KeyOutlined', iconComponent: KeyOutlined },
    { label: '锁定', value: 'LockOutlined', iconComponent: LockOutlined },
    { label: '邮件', value: 'MailOutlined', iconComponent: MailOutlined },
    { label: '菜单', value: 'MenuOutlined', iconComponent: MenuOutlined },
    { label: '消息', value: 'MessageOutlined', iconComponent: MessageOutlined },
    { label: '公告', value: 'NotificationOutlined', iconComponent: NotificationOutlined },
    { label: '分区', value: 'PartitionOutlined', iconComponent: PartitionOutlined },
    { label: '图表', value: 'PieChartOutlined', iconComponent: PieChartOutlined },
    { label: '档案', value: 'ProfileOutlined', iconComponent: ProfileOutlined },
    { label: '项目', value: 'ProjectOutlined', iconComponent: ProjectOutlined },
    { label: '阅读', value: 'ReadOutlined', iconComponent: ReadOutlined },
    { label: '权限', value: 'SafetyCertificateOutlined', iconComponent: SafetyCertificateOutlined },
    { label: '计划', value: 'ScheduleOutlined', iconComponent: ScheduleOutlined },
    { label: '设置', value: 'SettingOutlined', iconComponent: SettingOutlined },
    { label: '商店', value: 'ShopOutlined', iconComponent: ShopOutlined },
    { label: '滑块', value: 'SlidersOutlined', iconComponent: SlidersOutlined },
    { label: '方案', value: 'SolutionOutlined', iconComponent: SolutionOutlined },
    { label: '角色', value: 'TeamOutlined', iconComponent: TeamOutlined },
    { label: '工具', value: 'ToolOutlined', iconComponent: ToolOutlined },
    { label: '用户', value: 'UserOutlined', iconComponent: UserOutlined },
    { label: '用户组', value: 'UsergroupAddOutlined', iconComponent: UsergroupAddOutlined },
  ];

  const selectedIconOption = computed(() => iconOptions.find((option) => option.value === formParams.icon));
  const filteredIconOptions = computed(() => {
    const keyword = iconSearch.value.trim().toLowerCase();
    if (!keyword) return iconOptions;
    return iconOptions.filter((option) =>
      [option.label, option.value].some((item) => String(item || '').toLowerCase().includes(keyword))
    );
  });

  function normalizeMenuScope(value: unknown): MenuScope {
    return value === 'tenant' ? 'tenant' : 'platform';
  }

  function syncExpandedKeys() {
    expandedKeys.value = collectExpandedKeys(rows.value);
  }

  function upsertMenuRow(menu: MenuRow) {
    const normalizedMenu = {
      ...menu,
      menu_scope: normalizeMenuScope(menu.menu_scope),
      children: undefined,
    };
    const index = rows.value.findIndex((item) => item.id === normalizedMenu.id || item.key === normalizedMenu.key);
    const previousKey = index >= 0 ? rows.value[index].key : '';
    if (index >= 0) {
      rows.value = rows.value.map((item, itemIndex) => {
        if (itemIndex === index) return normalizedMenu;
        if (previousKey && previousKey !== normalizedMenu.key && item.parent_key === previousKey) {
          return { ...item, parent_key: normalizedMenu.key };
        }
        return item;
      });
    } else {
      rows.value = [...rows.value, normalizedMenu];
    }
    syncExpandedKeys();
    syncForm(normalizedMenu);
  }

  function removeMenuRow(key: string) {
    const removedKeys = new Set([key, ...collectDescendantKeys(rows.value, key)]);
    rows.value = rows.value.filter((item) => !removedKeys.has(item.key));
    syncExpandedKeys();
  }

  const selectedMenuRow = computed(() => findMenuByKey(rows.value, selectedMenuKey.value));
  const parentMenuOptions = computed<SelectOption[]>(() => {
    const blocked = new Set<string>();
    if (formMode.value === 'edit' && formParams.key) {
      const descendants = collectDescendantKeys(rows.value, formParams.key);
      descendants.forEach((key) => blocked.add(key));
      blocked.add(formParams.key);
    }
    return rows.value
      .filter((item) => item.menu_type !== 'action' && item.menu_scope === formParams.menu_scope && !blocked.has(item.key))
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
        label: node.menu_type === 'action' ? `操作：${node.label}` : node.label,
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
    formParams.menu_scope = activeScope.value;
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
    formParams.menu_scope = menu.menu_scope === 'tenant' ? 'tenant' : 'platform';
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
    const parent = parentKey ? findMenuByKey(rows.value, parentKey) : null;
    formParams.menu_scope = parent?.menu_scope === 'tenant' ? 'tenant' : activeScope.value;
    formParams.menu_type = parent?.menu_type === 'page' ? 'action' : parentKey ? 'page' : 'directory';
  }

  async function handleScopeChange(value: string | number) {
    const nextScope: MenuScope = value === 'tenant' ? 'tenant' : 'platform';
    if (nextScope === activeScope.value) return;
    activeScope.value = nextScope;
    pattern.value = '';
    selectedKeys.value = [];
    selectedMenuKey.value = '';
    formMode.value = 'edit';
    resetForm();
    await reload();
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

  function openIconPicker() {
    iconSearch.value = '';
    iconPickerVisible.value = true;
  }

  function selectIcon(icon: string) {
    formParams.icon = icon;
    iconPickerVisible.value = false;
  }

  function clearIcon() {
    formParams.icon = '';
  }

  function trimFormText(value: unknown) {
    return String(value || '').trim();
  }

  function handleParentKeyChange(value: string | null) {
    formParams.parent_key = trimFormText(value);
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
    if (menu.menu_type === 'action') {
      message.warning('按钮/操作权限不能新增子节点');
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
        key: trimFormText(formParams.key),
        label: trimFormText(formParams.label),
        menu_scope: formParams.menu_scope,
        menu_type: formParams.menu_type,
        path: formParams.menu_type === 'action' ? '' : trimFormText(formParams.path),
        route_name: formParams.menu_type === 'action' ? '' : trimFormText(formParams.route_name),
        component: formParams.menu_type === 'action' ? '' : trimFormText(formParams.component),
        icon: formParams.menu_type === 'action' ? '' : trimFormText(formParams.icon),
        parent_key: trimFormText(formParams.parent_key),
        permission_code: trimFormText(formParams.permission_code),
        sort_order: Number(formParams.sort_order || 0),
        is_visible: !!formParams.is_visible,
      };

      if (formMode.value === 'create') {
        const result = await createRbacMenu(payload);
        const savedMenu = (result as { item?: MenuRow }).item;
        if (savedMenu) upsertMenuRow(savedMenu);
        message.success('菜单创建成功');
      } else if (formParams.id) {
        const result = await updateRbacMenu(formParams.id, payload);
        const savedMenu = (result as { item?: MenuRow }).item;
        if (savedMenu) upsertMenuRow(savedMenu);
        message.success('菜单保存成功');
      }
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
      content: `确认删除菜单「${formParams.label || formParams.key}」？`,
      positiveText: '删除',
      negativeText: '取消',
      async onPositiveClick() {
        try {
          const deletedKey = formParams.key;
          await deleteRbacMenu(formParams.id as number);
          removeMenuRow(deletedKey);
          message.success('菜单已删除');
          startCreate('');
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
      const payload = await getRbacMenus({ scope: activeScope.value });
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

  reload();
</script>

<style lang="less" scoped>
  .menu-panel-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-width: 0;
    height: var(--app-table-action-button-height, 34px);
    padding: 0 var(--app-table-action-button-padding-x, 12px);
    color: var(--app-table-action-default-text, var(--app-primary-color));
    font: inherit;
    font-size: var(--app-font-size-base, 14px);
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
    background: var(--app-table-action-default-bg, var(--app-surface-bg));
    border: 1px solid var(--app-table-action-default-border, var(--app-border-color));
    border-radius: var(--app-table-action-button-radius, var(--app-card-radius));
    transition: color 0.16s ease, background-color 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;

    &:hover,
    &:focus-visible {
      color: var(--app-primary-hover-color, var(--app-primary-color));
      background: var(--app-table-toolbar-icon-hover-bg, var(--app-primary-soft-bg));
      border-color: var(--app-primary-color);
      outline: none;
    }

    &:active {
      color: var(--app-primary-pressed-color, var(--app-primary-color));
      border-color: var(--app-primary-pressed-color, var(--app-primary-color));
    }
  }

  .menu-tree-column {
    min-height: 0;
  }

  .menu-tree-card {
    min-height: 0;
    overflow: hidden;
  }

  .menu-tree-card :deep(.n-card__content) {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
  }

  .menu-tree-panel {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
  }

  .menu-scope-switch {
    width: 100%;
  }

  .menu-list {
    box-sizing: border-box;
    display: flex;
    height: min(560px, calc(100vh - var(--app-header-height, 64px) - var(--app-tabs-height, 44px) - 220px));
    min-height: 360px;
    overflow: hidden;
  }

  .menu-list-loading {
    display: flex;
    flex: 1 1 auto;
    align-items: flex-start;
    justify-content: center;
    min-width: 0;
    min-height: 0;
    padding-top: 32px;
  }

  .menu-tree {
    flex: 1 1 auto;
    min-height: 0;
  }

  .menu-tree :deep(.n-scrollbar),
  .menu-tree :deep(.n-scrollbar-container),
  .menu-tree :deep(.n-scrollbar-content) {
    height: 100%;
  }

  @media (min-width: 1024px) {
    .menu-tree-column {
      min-height: min(760px, calc(100vh - var(--app-header-height, 64px) - var(--app-tabs-height, 44px) - 140px));
      position: relative;
    }

    .menu-tree-card {
      position: absolute;
      inset: 0;
    }

    .menu-list {
      flex: 1 1 auto;
      height: auto;
      min-height: 0;
    }
  }

  .menu-icon-field {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    align-items: center;
  }

  .menu-icon-trigger {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    gap: 10px;
    align-items: center;
    width: 100%;
    min-width: 0;
    height: 40px;
    padding: 0 12px;
    color: var(--app-text-color-base);
    text-align: left;
    cursor: pointer;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color);
    border-radius: var(--app-input-radius, 4px);
    transition: border-color 0.16s ease, box-shadow 0.16s ease;
  }

  .menu-icon-trigger:hover,
  .menu-icon-trigger:focus-visible {
    border-color: var(--app-primary-color);
    outline: none;
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--app-primary-color) 12%, transparent);
  }

  .menu-icon-trigger__preview {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    color: var(--app-icon-color);
  }

  .menu-icon-trigger__text {
    display: flex;
    flex-direction: column;
    min-width: 0;
    line-height: 1.25;
  }

  .menu-icon-trigger__label,
  .menu-icon-trigger__key {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .menu-icon-trigger__key,
  .menu-icon-picker__hint {
    color: var(--app-text-color-secondary);
    font-size: 12px;
  }

  .menu-icon-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
    gap: 8px;
    max-height: min(440px, 58vh);
    padding: 14px 2px 2px;
    overflow: auto;
  }

  .menu-icon-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    min-width: 0;
    height: 66px;
    color: var(--app-text-color-secondary);
    cursor: pointer;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color);
    border-radius: 6px;
    transition: color 0.16s ease, background-color 0.16s ease, border-color 0.16s ease;

    span {
      max-width: 100%;
      overflow: hidden;
      font-size: 12px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    &:hover,
    &:focus-visible,
    &.is-selected {
      color: var(--app-primary-color);
      background: var(--app-primary-soft-bg);
      border-color: var(--app-primary-color);
      outline: none;
    }
  }

  .menu-form-actions {
    margin-left: var(--app-page-detail-label-width, 110px);
  }

  :deep(.menu-icon-picker) {
    width: min(760px, calc(100vw - 32px));
  }
</style>
