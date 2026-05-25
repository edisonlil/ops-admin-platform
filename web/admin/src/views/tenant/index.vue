<template>
  <div class="tenant-page">
    <ListPageRuntime v-if="isPlatformTenantManagement" :schema="tenantListPage" :rows="tenants" :loading="loading" :pagination-total="tenantPaginationTotal" @refresh="reload">
      <template #filters>
        <n-input v-model:value="query" clearable placeholder="搜索租户 Key / 名称" class="tenant-page__search" @keyup.enter="reload" />
        <n-button @click="reload">查询</n-button>
      </template>
    </ListPageRuntime>

    <ListPageRuntime v-else :schema="memberListPage" :rows="tenantUsers" :loading="usersLoading || loading" :pagination-total="tenantUsersPaginationTotal" @refresh="loadTenantUsers" />
    <input ref="memberImportInputRef" type="file" accept=".xlsx" style="display: none" @change="handleMemberImportFileChange" />
    <n-modal v-model:show="tenantModalVisible" preset="card" :style="{ width: '560px' }" :bordered="false">
      <template #header>{{ tenantFormMode === 'create' ? '新增租户' : '编辑租户' }}</template>
      <n-form ref="tenantFormRef" :model="tenantForm" :rules="tenantRules" label-placement="left" :label-width="96">
        <n-form-item label="租户 Key" path="key">
          <n-input v-model:value="tenantForm.key" :disabled="tenantFormMode === 'edit'" placeholder="例如 docs-team" />
        </n-form-item>
        <n-form-item label="租户名称" path="name">
          <n-input v-model:value="tenantForm.name" placeholder="请输入租户名称" />
        </n-form-item>
        <n-form-item label="状态" path="status">
          <n-select v-model:value="tenantForm.status" :options="statusOptions" />
        </n-form-item>
        <n-form-item label="备注" path="remark">
          <n-input v-model:value="tenantForm.remark" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
        </n-form-item>
        <n-form-item v-if="tenantFormMode === 'edit' && canAssignTenantTheme" label="外观主题">
          <n-select v-model:value="tenantForm.theme_id" clearable filterable :loading="themesLoading" :options="themeOptions" placeholder="选择租户外观主题" />
        </n-form-item>
        <template v-if="tenantFormMode === 'create'">
          <n-form-item label="管理员账号">
            <n-input v-model:value="tenantAdminForm.username" placeholder="默认租户管理员账号" />
          </n-form-item>
          <n-form-item label="管理员密码">
            <n-input v-model:value="tenantAdminForm.password" type="password" show-password-on="mousedown" />
          </n-form-item>
        </template>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="tenantModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="savingTenant" @click="submitTenant">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-drawer v-model:show="detailVisible" :width="920" placement="right" to=".appearance-root">
      <n-drawer-content class="tenant-detail-drawer" :title="activeTenant ? `${activeTenant.name} / ${activeTenant.tenant_key}` : '租户详情'">
        <n-tabs type="line" animated>
          <n-tab-pane name="base" tab="基础信息">
            <n-descriptions v-if="activeTenant" bordered :column="2" size="small">
              <n-descriptions-item label="租户 Key">{{ activeTenant.tenant_key }}</n-descriptions-item>
              <n-descriptions-item label="状态">
                <AppStatusTag :status-key="activeTenant.status === 'active' ? 'active' : 'suspended'" />
              </n-descriptions-item>
              <n-descriptions-item label="租户名称">{{ activeTenant.name }}</n-descriptions-item>
              <n-descriptions-item label="更新时间">{{ formatToDateTime(activeTenant.update_time || '') }}</n-descriptions-item>
              <n-descriptions-item label="备注" :span="2">{{ activeTenant.remark || '-' }}</n-descriptions-item>
            </n-descriptions>
          </n-tab-pane>
          <n-tab-pane name="users" tab="成员">
            <ListPageRuntime :schema="drawerUserListPage" :rows="tenantUsers" :loading="usersLoading" :pagination-total="tenantUsersPaginationTotal" @refresh="loadTenantUsers" />
          </n-tab-pane>
          <n-tab-pane name="keys" tab="API Key">
            <ListPageRuntime :schema="drawerKeyListPage" :rows="tenantKeys" :loading="keysLoading" :pagination-total="tenantKeysPaginationTotal" @refresh="loadTenantKeys" />
          </n-tab-pane>
          <n-tab-pane name="init" tab="初始化">
            <n-result status="success" title="租户初始化由后端受控脚本保证">
              <template #footer>
                <span class="tenant-drawer-note">RBAC、默认角色、默认菜单和租户基础数据由显式初始化流程完成。</span>
              </template>
            </n-result>
          </n-tab-pane>
        </n-tabs>
      </n-drawer-content>
    </n-drawer>

    <n-modal v-model:show="userModalVisible" preset="card" :style="{ width: '680px' }" :bordered="false">
      <template #header>{{ userFormMode === 'create' ? '新增成员' : '编辑成员' }}</template>
      <n-form ref="userFormRef" :model="userForm" :rules="userRules" label-placement="left" :label-width="112">
        <n-form-item label="用户名" path="username">
          <n-input v-model:value="userForm.username" />
        </n-form-item>
        <n-form-item label="姓名" path="full_name">
          <n-input v-model:value="userForm.full_name" placeholder="请输入成员姓名" />
        </n-form-item>
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="userForm.email" placeholder="请输入邮箱" />
        </n-form-item>
        <n-form-item :label="userFormMode === 'create' ? '初始密码' : '新密码'" path="password">
          <n-input v-model:value="userForm.password" type="password" show-password-on="mousedown" />
        </n-form-item>
        <n-form-item label="角色" path="role_keys">
          <n-select v-model:value="userForm.role_keys" multiple filterable clearable :options="roleOptions" />
        </n-form-item>
        <n-form-item label="所属部门">
          <n-tree-select
            v-model:value="userForm.department_ids"
            multiple
            clearable
            filterable
            cascade
            checkable
            block-line
            default-expand-all
            :options="departmentTreeOptions"
            placeholder="选择成员所属部门"
            @update:value="handleDepartmentIdsChange"
          />
        </n-form-item>
        <n-form-item label="主部门">
          <n-tree-select
            v-model:value="userForm.primary_department_id"
            clearable
            filterable
            block-line
            default-expand-all
            :options="primaryDepartmentTreeOptions"
            placeholder="用于本部门数据权限计算"
          />
        </n-form-item>
        <n-form-item label="直属上级">
          <n-select v-model:value="userForm.manager_user_id" clearable filterable :options="managerUserOptions" placeholder="选择直属上级" />
        </n-form-item>
        <n-form-item label="启用" path="is_active">
          <n-switch v-model:value="userForm.is_active" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="userModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="savingUser" @click="submitUser">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="keyCreateVisible" preset="dialog" title="新增 API Key" positive-text="创建" @positive-click="createKey">
      <n-input v-model:value="newKeyName" placeholder="Key 名称" />
    </n-modal>

    <n-modal v-model:show="keyEditVisible" preset="dialog" title="编辑 API Key" positive-text="保存" @positive-click="saveKeyEdit">
      <n-input v-model:value="editKeyName" placeholder="Key 名称" />
    </n-modal>

    <AppCreatedApiKeyModal v-model:show="createdKeyVisible" :api-key="createdKey" />
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, onBeforeUnmount, reactive, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption, TreeSelectOption } from 'naive-ui';
  import {
    activateTenant,
    createCurrentTenantApiKey,
    createCurrentTenantUser,
    createTenant,
    createTenantApiKey,
    createTenantUser,
    disableCurrentTenantUser,
    disableTenantUser,
    downloadCurrentTenantUserImportTemplate,
    downloadTenantUserImportTemplate,
    enableCurrentTenantUser,
    enableTenantUser,
    exportCurrentTenantUsers,
    exportTenantUsers,
    getCurrentTenantApiKeys,
    getCurrentTenantUserImportJob,
    getCurrentTenantRoles,
    getCurrentTenantUsers,
    getDepartments,
    getRbacRoles,
    getTenantApiKeys,
    getTenantUserImportJob,
    getTenantUsers,
    getTenants,
    importCurrentTenantUsers,
    importTenantUsers,
    revokeCurrentTenantApiKey,
    revokeTenantApiKey,
    suspendTenant,
    updateCurrentTenantUser,
    updateCurrentTenantApiKey,
    updateTenant,
    updateTenantApiKey,
    updateTenantUser,
  } from '@/api/business';
  import type { ImportJob } from '@/api/business';
  import { assignTenantAppearanceTheme, getAppearanceThemes, getTenantAppearanceTheme } from '@/api/appearance';
  import AppCreatedApiKeyModal from '@/components/Application/AppCreatedApiKeyModal.vue';
  import AppStatusGroup from '@/components/Application/AppStatusGroup.vue';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { usePermission } from '@/hooks/web/usePermission';
  import { useUserStore } from '@/store/modules/user';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';

  interface TenantRow extends Recordable {
    id: number;
    tenant_key: string;
    name: string;
    status: string;
    remark?: string;
    user_count?: number;
    api_key_count?: number;
    update_time?: string;
  }

  interface TenantUserRow extends Recordable {
    id: number;
    username: string;
    full_name?: string;
    email?: string;
    roles?: Array<{ key?: string; name?: string }>;
    departments?: DepartmentRow[];
    department_ids?: number[];
    primary_department_id?: number | null;
    manager_user_id?: number | null;
    is_active?: boolean;
    is_superuser?: boolean;
    is_tenant_admin?: boolean;
  }

  interface TenantApiKeyRow extends Recordable {
    id: number;
    name?: string;
    prefix?: string;
    is_active?: boolean;
    creator?: string;
    create_time?: string;
  }

  interface DepartmentRow extends Recordable {
    id: number;
    parent_id?: number | null;
    code: string;
    name: string;
  }

  const message = useMessage();
  const { hasPermission } = usePermission();
  const userStore = useUserStore();
  const route = useRoute();
  const query = ref('');
  const loading = ref(false);
  const tenants = ref<TenantRow[]>([]);
  const tenantPaginationTotal = ref(0);
  const tenantModalVisible = ref(false);
  const tenantFormMode = ref<'create' | 'edit'>('create');
  const savingTenant = ref(false);
  const tenantFormRef = ref<FormInst | null>(null);
  const tenantForm = reactive({ id: 0, key: '', name: '', status: 'active', remark: '', theme_id: null as number | null });
  const tenantAdminForm = reactive({ username: '', password: '' });
  const detailVisible = ref(false);
  const activeTenant = ref<TenantRow | null>(null);
  const tenantUsers = ref<TenantUserRow[]>([]);
  const tenantKeys = ref<TenantApiKeyRow[]>([]);
  const tenantUsersPaginationTotal = ref(0);
  const tenantKeysPaginationTotal = ref(0);
  const departments = ref<DepartmentRow[]>([]);
  const usersLoading = ref(false);
  const keysLoading = ref(false);
  const userModalVisible = ref(false);
  const userFormMode = ref<'create' | 'edit'>('create');
  const savingUser = ref(false);
  const userFormRef = ref<FormInst | null>(null);
  const memberImportInputRef = ref<HTMLInputElement | null>(null);
  const memberImportJob = ref<ImportJob | null>(null);
  const memberImportPollingTimer = ref<number | null>(null);
  const roleOptions = ref<SelectOption[]>([]);
  const themeOptions = ref<SelectOption[]>([]);
  const themesLoading = ref(false);
  const userForm = reactive({
    id: 0,
    username: '',
    full_name: '',
    email: '',
    password: '',
    role_keys: [] as string[],
    department_ids: [] as number[],
    primary_department_id: null as number | null,
    manager_user_id: null as number | null,
    is_active: true,
    is_superuser: false,
  });
  const keyCreateVisible = ref(false);
  const keyEditVisible = ref(false);
  const editingKey = ref<TenantApiKeyRow | null>(null);
  const editKeyName = ref('');
  const createdKeyVisible = ref(false);
  const createdKey = ref('');
  const newKeyName = ref('');

  const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);
  const isTenantUserManagement = computed(() => String(route.name || '') === 'tenant-user-management');
  const isPlatformTenantManagement = computed(() => isPlatformAdmin.value && !isTenantUserManagement.value);
  const canCreateTenant = computed(() => hasPermission(['tenant:create']));
  const canUpdateTenant = computed(() => hasPermission(['tenant:update']));
  const canActivateTenant = computed(() => hasPermission(['tenant:activate']));
  const canSuspendTenant = computed(() => hasPermission(['tenant:suspend']));
  const canAssignTenantTheme = computed(() => hasPermission(['tenant:theme:assign']));
  const canCreateTenantUser = computed(() => hasPermission(['tenant:users:create']));
  const canUpdateTenantUser = computed(() => hasPermission(['tenant:users:update']));
  const canToggleTenantUser = (active: boolean) => hasPermission([active ? 'tenant:users:disable' : 'tenant:users:enable']);
  const canCreateTenantApiKey = computed(() => hasPermission(['tenant:api_keys:create']));
  const canRevokeTenantApiKey = computed(() => hasPermission(['tenant:api_keys:revoke']));
  const memberImportJobRunning = computed(() => !!memberImportJob.value?.is_active);

  const statusOptions = [
    { label: '启用', value: 'active' },
    { label: '停用', value: 'suspended' },
  ];

  const tenantRules: FormRules = {
    key: [{ required: true, message: '请输入租户 Key', trigger: ['blur', 'input'] }],
    name: [{ required: true, message: '请输入租户名称', trigger: ['blur', 'input'] }],
  };

  const userRules = computed<FormRules>(() => ({
    username: [{ required: true, message: '请输入用户名', trigger: ['blur', 'input'] }],
    full_name: [{ required: true, message: '请输入姓名', trigger: ['blur', 'input'] }],
    email: [
      {
        validator: (_rule, value: string) => !value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value).trim()),
        message: '请输入正确的邮箱',
        trigger: ['blur', 'input'],
      },
    ],
    password: userFormMode.value === 'create' ? [{ required: true, message: '请输入初始密码', trigger: ['blur', 'input'] }] : [],
  }));

  const departmentTreeOptions = computed<TreeSelectOption[]>(() => buildDepartmentTreeOptions());
  const primaryDepartmentTreeOptions = computed<TreeSelectOption[]>(() => buildDepartmentTreeOptions(new Set(userForm.department_ids)));
  const managerUserOptions = computed<SelectOption[]>(() =>
    tenantUsers.value
      .filter((user) => Number(user.id) !== Number(userForm.id))
      .map((user) => ({ label: `${user.full_name || user.username} (${user.username})`, value: user.id }))
  );

  const tenantColumns: DataTableColumns<TenantRow> = [
    { title: 'ID', key: 'id', width: 80 },
    { title: '租户 Key', key: 'tenant_key', minWidth: 160 },
    { title: '租户名称', key: 'name', minWidth: 180 },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render(row) {
        return h(AppStatusTag, { tone: row.status === 'active' ? 'success' : 'warning', label: row.status === 'active' ? '启用' : '停用' });
      },
    },
    { title: '成员', key: 'user_count', width: 90 },
    { title: 'API Key', key: 'api_key_count', width: 100 },
    { title: '更新时间', key: 'update_time', width: 190, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 250,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '详情', onClick: () => openDetail(row) },
            { label: '编辑', show: canUpdateTenant.value, onClick: () => openEdit(row) },
            {
              label: row.status === 'active' ? '停用' : '启用',
              tone: row.status === 'active' ? 'danger' : 'primary',
              show: row.status === 'active' ? canSuspendTenant.value : canActivateTenant.value,
              confirm: true,
              confirmTitle: row.status === 'active' ? '停用租户' : '启用租户',
              confirmContent: `确认${row.status === 'active' ? '停用' : '启用'}租户 ${row.name}？`,
              onConfirm: () => toggleTenant(row),
            },
          ],
        });
      },
    },
  ];

  const userColumns: DataTableColumns<TenantUserRow> = [
    { title: '用户名', key: 'username', minWidth: 160 },
    { title: '姓名', key: 'full_name', minWidth: 150 },
    { title: '邮箱', key: 'email', minWidth: 220, render: (row) => row.email || '-' },
    {
      title: '角色',
      key: 'roles',
      minWidth: 220,
      render(row) {
        const roles = row.roles || [];
        return h(AppStatusGroup, {
          items: roles.length
            ? roles.map((role) => ({ key: String(role.key || role.name), label: String(role.name || role.key), tone: 'info' }))
            : [{ statusKey: 'unassigned' }],
        });
      },
    },
    { title: '部门', key: 'departments', minWidth: 220, render: (row) => departmentNames(row.department_ids || []) },
    { title: '直属上级', key: 'manager_user_id', minWidth: 160, render: (row) => managerUserName(row.manager_user_id || null) },
    {
      title: '状态',
      key: 'is_active',
      width: 90,
      render(row) {
        return h(AppStatusTag, { tone: row.is_active ? 'success' : 'error', label: row.is_active ? '启用' : '停用' });
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: canUpdateTenantUser.value, onClick: () => openUserEdit(row) },
            {
              label: row.is_active ? '停用' : '启用',
              tone: row.is_active ? 'danger' : 'primary',
              show: canToggleTenantUser(!!row.is_active),
              confirm: true,
              confirmTitle: row.is_active ? '停用成员' : '启用成员',
              confirmContent: `确认${row.is_active ? '停用' : '启用'}成员 ${row.username}？`,
              onConfirm: () => toggleUser(row),
            },
          ],
        });
      },
    },
  ];

  const keyColumns: DataTableColumns<TenantApiKeyRow> = [
    { title: '名称', key: 'name', minWidth: 180 },
    { title: '前缀', key: 'prefix', width: 150 },
    {
      title: '状态',
      key: 'is_active',
      width: 90,
      render(row) {
        return h(AppStatusTag, { tone: row.is_active ? 'success' : 'neutral', label: row.is_active ? '有效' : '已撤销' });
      },
    },
    { title: '创建人', key: 'creator', width: 120 },
    { title: '创建时间', key: 'create_time', width: 190, render: (row) => formatToDateTime(row.create_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: canCreateTenantApiKey.value, disabled: !row.is_active, onClick: () => openKeyEdit(row) },
            { label: '复制', onClick: () => copyApiKey(row) },
            {
              label: '撤销',
              tone: 'danger',
              show: canRevokeTenantApiKey.value,
              disabled: !row.is_active,
              confirm: true,
              confirmTitle: '撤销 API Key',
              confirmContent: `确认撤销 API Key ${row.name || row.prefix}？`,
              onConfirm: () => revokeKey(row),
            },
          ],
        });
      },
    },
  ];

  const tenantListPage = computed(() =>
    defineListPage<TenantRow>({
      id: 'tenant.platform',
      title: '租户管理',
      description: '管理平台租户、成员用户与租户级 API Key。',
      variant: 'dense-data',
      density: 'compact',
      view: { type: 'table', columns: tenantColumns, rowKey: (row) => Number(row.id), scrollX: 1160, sort: { remote: true }, tableProps: { size: 'small' } },
      toolbar: {
        primaryAction: canCreateTenant.value ? { key: 'create', label: '新增租户', type: 'primary', onClick: () => openCreate() } : undefined,
        rightTools: ['refresh'],
      },
      pagination: { pageSize: 20 },
    })
  );

  const memberListPage = computed(() =>
    defineListPage<TenantUserRow>({
      id: 'tenant.members',
      title: '成员管理',
      description: '管理当前租户的成员账号、角色、所属部门和启用状态。',
      variant: 'dense-data',
      density: 'compact',
      view: { type: 'table', columns: userColumns, rowKey: (row) => Number(row.id), scrollX: 1140, sort: { remote: true }, columnRuntime: { columns: userColumnRuntime }, tableProps: { size: 'small' } },
      toolbar: {
        primaryAction: canCreateTenantUser.value ? { key: 'create', label: '新增成员', type: 'primary', onClick: () => openUserCreate() } : undefined,
        batchActions: [
          { key: 'template', label: '下载模板', onClick: () => handleMemberDownloadTemplate() },
          {
            key: 'import',
            label: memberImportJobRunning.value ? '导入中' : '导入成员',
            type: memberImportJobRunning.value ? 'warning' : 'primary',
            disabled: !canCreateTenantUser.value || memberImportJobRunning.value,
            onClick: () => memberImportInputRef.value?.click(),
          },
          { key: 'export', label: '导出成员', onClick: () => handleMemberExport() },
        ],
        rightTools: ['refresh'],
      },
      pagination: { pageSize: 20 },
    })
  );

  const drawerUserListPage = computed(() =>
    defineListPage<TenantUserRow>({
      id: 'tenant.drawer.members',
      title: '成员',
      description: '管理此租户下的成员账号、角色、所属部门和启用状态。',
      embedded: true,
      variant: 'dense-data',
      density: 'compact',
      view: { type: 'table', columns: userColumns, rowKey: (row) => Number(row.id), scrollX: 1140, sort: { remote: true }, columnRuntime: { columns: userColumnRuntime }, tableProps: { size: 'small' } },
      toolbar: {
        primaryAction: canCreateTenantUser.value ? { key: 'create', label: '新增成员', type: 'primary', onClick: () => openUserCreate() } : undefined,
        batchActions: [
          { key: 'template', label: '下载模板', onClick: () => handleMemberDownloadTemplate() },
          {
            key: 'import',
            label: memberImportJobRunning.value ? '导入中' : '导入成员',
            type: memberImportJobRunning.value ? 'warning' : 'primary',
            disabled: !canCreateTenantUser.value || memberImportJobRunning.value,
            onClick: () => memberImportInputRef.value?.click(),
          },
          { key: 'export', label: '导出成员', onClick: () => handleMemberExport() },
        ],
        rightTools: ['refresh'],
      },
      pagination: { pageSize: 20 },
    })
  );

  const drawerKeyListPage = computed(() =>
    defineListPage<TenantApiKeyRow>({
      id: 'tenant.drawer.api-keys',
      title: 'API Key',
      description: '管理此租户可用于外部集成和自动化访问的 API Key。',
      embedded: true,
      variant: 'dense-data',
      density: 'compact',
      view: { type: 'table', columns: keyColumns, rowKey: (row) => Number(row.id), scrollX: 700, sort: { remote: true }, tableProps: { size: 'small' } },
      toolbar: {
        primaryAction: canCreateTenantApiKey.value ? { key: 'create', label: '新增 Key', type: 'primary', onClick: () => (keyCreateVisible.value = true) } : undefined,
        rightTools: ['refresh'],
      },
      pagination: { pageSize: 20 },
    })
  );

  const userColumnRuntime = [
    { key: 'username', sortable: true },
    { key: 'full_name', sortable: true },
    { key: 'email', sortable: true },
    { key: 'roles', sortable: false },
    { key: 'departments', sortable: false },
    { key: 'manager_user_id', sortable: false },
    { key: 'is_active', sortable: true },
    { key: 'actions', required: true, sortable: false },
  ];

  function resetTenantForm() {
    Object.assign(tenantForm, { id: 0, key: '', name: '', status: 'active', remark: '', theme_id: null });
    Object.assign(tenantAdminForm, { username: '', password: '' });
    tenantFormRef.value?.restoreValidation();
  }

  function resetUserForm() {
    Object.assign(userForm, { id: 0, username: '', full_name: '', email: '', password: '', role_keys: [], department_ids: [], primary_department_id: null, manager_user_id: null, is_active: true, is_superuser: false });
    userFormRef.value?.restoreValidation();
  }

  function openCreate() {
    tenantFormMode.value = 'create';
    resetTenantForm();
    tenantModalVisible.value = true;
  }

  async function openEdit(row: TenantRow) {
    tenantFormMode.value = 'edit';
    Object.assign(tenantForm, { id: row.id, key: row.tenant_key, name: row.name, status: row.status, remark: row.remark || '' });
    await ensureThemes();
    try {
      const payload = await getTenantAppearanceTheme(row.id);
      tenantForm.theme_id = payload.theme?.id ? Number(payload.theme.id) : null;
    } catch {
      tenantForm.theme_id = null;
    }
    tenantModalVisible.value = true;
  }

  async function ensureThemes() {
    if (themeOptions.value.length) return;
    themesLoading.value = true;
    try {
      const payload = await getAppearanceThemes();
      themeOptions.value = (payload.items || []).filter((theme) => theme.status === 'published').map((theme) => ({ label: theme.name || `主题 ${theme.id}`, value: Number(theme.id) }));
    } finally {
      themesLoading.value = false;
    }
  }

  async function submitTenant() {
    try {
      await tenantFormRef.value?.validate();
    } catch {
      return;
    }
    savingTenant.value = true;
    try {
      const payload = {
        key: tenantForm.key,
        name: tenantForm.name,
        status: tenantForm.status,
        remark: tenantForm.remark,
        ...(tenantFormMode.value === 'create' ? { admin_username: tenantAdminForm.username, admin_password: tenantAdminForm.password } : {}),
      };
      if (tenantFormMode.value === 'create') await createTenant(payload);
      else {
        await updateTenant(tenantForm.id, payload);
        if (canAssignTenantTheme.value) await assignTenantAppearanceTheme(tenantForm.id, tenantForm.theme_id || null);
      }
      tenantModalVisible.value = false;
      await reload();
      message.success('租户已保存');
    } finally {
      savingTenant.value = false;
    }
  }

  function toggleTenant(row: TenantRow) {
    return (async () => {
      if (row.status === 'active') await suspendTenant(row.id);
      else await activateTenant(row.id);
      await reload();
    })();
  }

  function toggleUser(row: TenantUserRow) {
    const nextActive = !row.is_active;
    return (async () => {
      if (!activeTenant.value) return;
      if (isPlatformTenantManagement.value) {
        if (nextActive) await enableTenantUser(activeTenant.value.id, row.id);
        else await disableTenantUser(activeTenant.value.id, row.id);
      } else if (nextActive) await enableCurrentTenantUser(row.id);
      else await disableCurrentTenantUser(row.id);
      await loadTenantUsers();
      message.success(`成员已${nextActive ? '启用' : '停用'}`);
    })();
  }

  async function handleMemberDownloadTemplate() {
    if (!activeTenant.value) return;
    try {
      if (isPlatformTenantManagement.value) await downloadTenantUserImportTemplate(activeTenant.value.id);
      else await downloadCurrentTenantUserImportTemplate();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '成员导入模板下载失败');
    }
  }

  async function handleMemberExport() {
    if (!activeTenant.value) return;
    try {
      if (isPlatformTenantManagement.value) await exportTenantUsers(activeTenant.value.id);
      else await exportCurrentTenantUsers();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '成员导出失败');
    }
  }

  async function handleMemberImportFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file || !activeTenant.value) return;
    if (memberImportJobRunning.value) {
      message.warning('已有导入任务正在执行，请等待完成后再导入');
      return;
    }
    try {
      const payload = isPlatformTenantManagement.value
        ? await importTenantUsers(activeTenant.value.id, file)
        : await importCurrentTenantUsers(file);
      memberImportJob.value = payload;
      message.success('导入任务已提交');
      startMemberImportPolling();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '成员导入失败');
    }
  }

  async function refreshMemberImportJobStatus(showFinishedMessage = true) {
    if (!activeTenant.value) return;
    const payload = isPlatformTenantManagement.value
      ? await getTenantUserImportJob(activeTenant.value.id)
      : await getCurrentTenantUserImportJob();
    memberImportJob.value = payload.item || null;
    if (!memberImportJob.value?.is_active) {
      stopMemberImportPolling();
      if (memberImportJob.value?.status === 'succeeded') {
        if (showFinishedMessage) message.success(`导入完成，共导入 ${memberImportJob.value.result_count || 0} 个成员`);
        await loadTenantUsers();
      } else if (memberImportJob.value?.status === 'failed' && showFinishedMessage) {
        message.error(memberImportJob.value.error || '成员导入失败');
      }
    }
  }

  function startMemberImportPolling() {
    stopMemberImportPolling();
    memberImportPollingTimer.value = window.setInterval(() => {
      refreshMemberImportJobStatus().catch((error) => {
        message.error(error instanceof Error ? error.message : '导入进度查询失败');
        stopMemberImportPolling();
      });
    }, 1500);
    refreshMemberImportJobStatus(false).catch(() => undefined);
  }

  function stopMemberImportPolling() {
    if (memberImportPollingTimer.value !== null) {
      window.clearInterval(memberImportPollingTimer.value);
      memberImportPollingTimer.value = null;
    }
  }

  async function openDetail(row: TenantRow) {
    activeTenant.value = row;
    detailVisible.value = true;
    await Promise.all([loadTenantUsers(), loadTenantKeys()]);
    await refreshMemberImportJobStatus(false);
    if (memberImportJobRunning.value) startMemberImportPolling();
  }

  async function ensureRoles() {
    if (roleOptions.value.length) return;
    const payload = isPlatformTenantManagement.value ? await getRbacRoles({ page: 1, page_size: 100 }) : await getCurrentTenantRoles();
    roleOptions.value = (payload.items || []).filter((role) => role.role_scope === 'tenant').map((role) => ({ label: role.name || role.key, value: role.key }));
  }

  async function ensureDepartments() {
    try {
      const payload = await getDepartments({
        include_disabled: false,
        tenant_id: isPlatformTenantManagement.value ? activeTenant.value?.id : undefined,
      });
      departments.value = payload.items || [];
    } catch {
      departments.value = [];
    }
  }

  async function loadTenantUsers(state?: ListRuntimeState) {
    if (!activeTenant.value) return;
    usersLoading.value = true;
    try {
      const tenantId = activeTenant.value.id;
      const params = runtimeListParams(state);
      const departmentsPromise = ensureDepartments();
      const usersPromise = isPlatformTenantManagement.value ? getTenantUsers(tenantId, params) : getCurrentTenantUsers(params);
      const [payload] = await Promise.all([usersPromise, departmentsPromise]);
      if (!activeTenant.value || Number(activeTenant.value.id) !== Number(tenantId)) return;
      tenantUsers.value = payload.items || [];
      tenantUsersPaginationTotal.value = payload.pagination?.total || tenantUsers.value.length;
    } finally {
      usersLoading.value = false;
    }
  }

  async function loadTenantKeys(state?: ListRuntimeState) {
    if (!activeTenant.value) return;
    keysLoading.value = true;
    try {
      const params = runtimeListParams(state);
      const payload = isPlatformTenantManagement.value ? await getTenantApiKeys(activeTenant.value.id, params) : await getCurrentTenantApiKeys(params);
      tenantKeys.value = payload.items || [];
      tenantKeysPaginationTotal.value = payload.pagination?.total || tenantKeys.value.length;
    } finally {
      keysLoading.value = false;
    }
  }

  async function openUserCreate() {
    await Promise.all([ensureRoles(), ensureDepartments()]);
    userFormMode.value = 'create';
    resetUserForm();
    userModalVisible.value = true;
  }

  async function openUserEdit(row: TenantUserRow) {
    await Promise.all([ensureRoles(), ensureDepartments()]);
    userFormMode.value = 'edit';
    Object.assign(userForm, {
      id: row.id,
      username: row.username,
      full_name: row.full_name || '',
      email: row.email || '',
      password: '',
      role_keys: (row.roles || []).map((role) => String(role.key)),
      department_ids: [...(row.department_ids || [])],
      primary_department_id: row.primary_department_id || null,
      manager_user_id: row.manager_user_id || null,
      is_active: !!row.is_active,
      is_superuser: !!row.is_superuser,
    });
    userModalVisible.value = true;
  }

  async function submitUser() {
    if (!activeTenant.value) return;
    try {
      await userFormRef.value?.validate();
    } catch {
      return;
    }
    savingUser.value = true;
    try {
      const primaryId = userForm.primary_department_id && userForm.department_ids.includes(userForm.primary_department_id) ? userForm.primary_department_id : null;
      const payload = {
        username: userForm.username,
        full_name: userForm.full_name,
        email: userForm.email,
        password: userForm.password || undefined,
        role_keys: userForm.role_keys,
        department_ids: [...userForm.department_ids],
        primary_department_id: primaryId,
        manager_user_id: userForm.manager_user_id || null,
        is_active: userForm.is_active,
        is_superuser: userForm.is_superuser,
      };
      if (userFormMode.value === 'create') {
        if (isPlatformTenantManagement.value) await createTenantUser(activeTenant.value.id, { ...payload, password: userForm.password });
        else await createCurrentTenantUser({ ...payload, password: userForm.password });
      } else if (isPlatformTenantManagement.value) await updateTenantUser(activeTenant.value.id, userForm.id, payload);
      else await updateCurrentTenantUser(userForm.id, payload);
      userModalVisible.value = false;
      await loadTenantUsers();
      message.success('成员已保存');
    } finally {
      savingUser.value = false;
    }
  }

  async function createKey() {
    if (!activeTenant.value || !newKeyName.value.trim()) {
      message.warning('请输入 Key 名称');
      return false;
    }
    const payload = isPlatformTenantManagement.value
      ? await createTenantApiKey(activeTenant.value.id, { name: newKeyName.value.trim() })
      : await createCurrentTenantApiKey({ name: newKeyName.value.trim() });
    createdKey.value = payload.key;
    createdKeyVisible.value = true;
    newKeyName.value = '';
    await loadTenantKeys();
    return true;
  }

  function openKeyEdit(row: TenantApiKeyRow) {
    editingKey.value = row;
    editKeyName.value = String(row.name || '');
    keyEditVisible.value = true;
  }

  async function saveKeyEdit() {
    const name = editKeyName.value.trim();
    if (!activeTenant.value || !editingKey.value || !name) {
      message.warning('请输入 Key 名称');
      return false;
    }
    if (isPlatformTenantManagement.value) await updateTenantApiKey(activeTenant.value.id, Number(editingKey.value.id), { name });
    else await updateCurrentTenantApiKey(Number(editingKey.value.id), { name });
    keyEditVisible.value = false;
    editingKey.value = null;
    editKeyName.value = '';
    message.success('API Key 已保存');
    await loadTenantKeys();
    return true;
  }

  async function copyApiKey(row: TenantApiKeyRow) {
    const fullKey = String(row.key || '');
    if (fullKey) {
      await copyText(fullKey);
      message.success('API Key 已复制');
      return;
    }
    const prefix = String(row.prefix || '');
    if (!prefix) {
      message.warning('暂无可复制的 API Key');
      return;
    }
    await copyText(prefix);
    message.warning('仅复制了历史 Key 前缀，完整 Key 需重新创建后复制');
  }

  async function revokeKey(row: TenantApiKeyRow) {
    if (!activeTenant.value) return;
    if (isPlatformTenantManagement.value) await revokeTenantApiKey(activeTenant.value.id, Number(row.id));
    else await revokeCurrentTenantApiKey(Number(row.id));
    message.success('API Key 已撤销');
    await loadTenantKeys();
  }

  async function copyText(value: string) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return;
    }
    const input = document.createElement('textarea');
    input.value = value;
    input.setAttribute('readonly', 'readonly');
    input.style.position = 'fixed';
    input.style.opacity = '0';
    input.style.pointerEvents = 'none';
    document.body.appendChild(input);
    input.select();
    document.execCommand('copy');
    document.body.removeChild(input);
  }

  function departmentNames(ids: number[]) {
    if (!ids.length) return '-';
    const names = ids.map((id) => departments.value.find((item) => item.id === id)).filter(Boolean).map((item) => departmentPath(item as DepartmentRow));
    return names.length ? names.join('、') : ids.join('、');
  }

  function managerUserName(id: number | null) {
    if (!id) return '-';
    const user = tenantUsers.value.find((item) => Number(item.id) === Number(id));
    return user ? `${user.full_name || user.username} (${user.username})` : `#${id}`;
  }

  function handleDepartmentIdsChange(value: number[] | null) {
    const departmentIds = value || [];
    userForm.department_ids = departmentIds;
    if (userForm.primary_department_id && !departmentIds.includes(userForm.primary_department_id)) {
      userForm.primary_department_id = null;
    }
  }

  function buildDepartmentTreeOptions(allowedIds?: Set<number>) {
    const byParent = new Map<number, DepartmentRow[]>();
    departments.value.forEach((department) => {
      const parentId = Number(department.parent_id || 0);
      byParent.set(parentId, [...(byParent.get(parentId) || []), department]);
    });
    const hasAllowedDescendant = (department: DepartmentRow): boolean => {
      if (!allowedIds || allowedIds.has(department.id)) return true;
      return (byParent.get(department.id) || []).some((child) => hasAllowedDescendant(child));
    };
    const build = (parentId: number): TreeSelectOption[] =>
      (byParent.get(parentId) || [])
        .filter(hasAllowedDescendant)
        .sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0) || a.name.localeCompare(b.name))
        .map((department) => {
          const children = build(department.id);
          return {
            label: department.name,
            key: department.id,
            value: department.id,
            disabled: !!allowedIds && !allowedIds.has(department.id),
            children: children.length ? children : undefined,
          };
        });
    return build(0);
  }

  function departmentPath(row: DepartmentRow) {
    const names = [row.name];
    let parentId = Number(row.parent_id || 0);
    const seen = new Set<number>([row.id]);
    while (parentId && !seen.has(parentId)) {
      seen.add(parentId);
      const parent = departments.value.find((item) => item.id === parentId);
      if (!parent) break;
      names.unshift(parent.name);
      parentId = Number(parent.parent_id || 0);
    }
    return names.join(' / ');
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      if (isPlatformTenantManagement.value) {
        const payload = await getTenants({ q: query.value || undefined, ...runtimeListParams(state) });
        tenants.value = payload.items || [];
        tenantPaginationTotal.value = payload.pagination?.total || tenants.value.length;
      } else {
        const tenant = userStore.info?.current_tenant as TenantRow | undefined;
        activeTenant.value = tenant ? { ...tenant, user_count: 0, api_key_count: 0 } : null;
        tenants.value = activeTenant.value ? [activeTenant.value] : [];
        await loadTenantUsers();
        await refreshMemberImportJobStatus(false);
        if (memberImportJobRunning.value) startMemberImportPolling();
      }
    } finally {
      loading.value = false;
    }
  }

  watch(
    () => route.name,
    () => {
      roleOptions.value = [];
      tenantUsers.value = [];
      tenantKeys.value = [];
      memberImportJob.value = null;
      stopMemberImportPolling();
      reload();
    }
  );

  reload();
  onBeforeUnmount(() => stopMemberImportPolling());
</script>

<style lang="less" scoped>
  .tenant-page {
    min-width: 0;
  }

  .tenant-page__search {
    width: min(320px, 100%);
  }

  .tenant-detail-drawer {
    --app-page-embedded-section-gap: 10px;
  }

  .tenant-drawer-note {
    color: var(--app-text-color-2);
    font-size: 13px;
  }

</style>
