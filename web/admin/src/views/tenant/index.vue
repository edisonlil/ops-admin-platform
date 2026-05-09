<template>
  <div>
    <div class="n-layout-page-header">
      <n-card :bordered="false" :title="pageTitle">
        {{ pageDescription }}
      </n-card>
    </div>

    <n-card v-if="isPlatformTenantManagement" :bordered="false" size="small" class="proCard mt-4">
      <AppDataTable
        title="租户列表"
        description="查询租户、维护状态，并进入详情管理成员与 API Key。"
        compact-search
        size="small"
        :columns="tenantColumns"
        :data="tenants"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
        :row-key="(row) => row.id"
      >
        <template #search>
          <n-input v-model:value="query" clearable placeholder="搜索租户 Key / 名称" @keyup.enter="reload" />
          <n-button @click="reload">查询</n-button>
        </template>
        <template #actions>
          <n-button type="primary" @click="openCreate">新建租户</n-button>
        </template>
      </AppDataTable>
    </n-card>

    <n-card v-else :bordered="false" size="small" class="proCard mt-4">
      <AppDataTable
        :title="activeTenant?.name || '当前租户'"
        description="维护当前租户的成员账号、角色和启用状态。"
        size="small"
        :columns="userColumns"
        :data="tenantUsers"
        :loading="usersLoading || loading"
        :pagination="{ pageSize: 20 }"
        :row-key="(row) => row.id"
      >
        <template #actions>
          <n-tag v-if="activeTenant" size="small" type="info">{{ activeTenant.tenant_key }}</n-tag>
          <n-button type="primary" @click="openUserCreate">新增成员</n-button>
          <n-button :loading="usersLoading" @click="loadTenantUsers">刷新</n-button>
        </template>
      </AppDataTable>
    </n-card>

    <n-modal v-model:show="tenantModalVisible" preset="card" :style="{ width: '560px' }" :bordered="false">
      <template #header>{{ tenantFormMode === 'create' ? '新建租户' : '编辑租户' }}</template>
      <n-form ref="tenantFormRef" :model="tenantForm" :rules="tenantRules" label-placement="left" :label-width="90">
        <n-form-item label="租户 Key" path="key">
          <n-input v-model:value="tenantForm.key" :disabled="tenantFormMode === 'edit'" placeholder="例如 docs-team" />
        </n-form-item>
        <n-form-item label="名称" path="name">
          <n-input v-model:value="tenantForm.name" placeholder="租户显示名称" />
        </n-form-item>
        <n-form-item label="状态" path="status">
          <n-select v-model:value="tenantForm.status" :options="statusOptions" />
        </n-form-item>
        <n-form-item label="备注" path="remark">
          <n-input v-model:value="tenantForm.remark" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
        </n-form-item>
        <n-form-item v-if="tenantFormMode === 'edit'" label="外观主题">
          <n-select
            v-model:value="tenantForm.theme_id"
            clearable
            filterable
            :loading="themesLoading"
            :options="themeOptions"
            placeholder="使用平台默认主题"
          />
        </n-form-item>
        <template v-if="tenantFormMode === 'create'">
          <n-form-item label="管理员账号">
            <n-input v-model:value="tenantAdminForm.username" placeholder="可选，创建租户时同步开通" />
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

    <n-drawer v-model:show="detailVisible" :width="920" placement="right">
      <n-drawer-content :title="activeTenant ? `${activeTenant.name} / ${activeTenant.tenant_key}` : '租户详情'">
        <n-tabs type="line" animated>
          <n-tab-pane name="base" tab="基本信息">
            <n-descriptions bordered :column="2" size="small" v-if="activeTenant">
              <n-descriptions-item label="租户 Key">{{ activeTenant.tenant_key }}</n-descriptions-item>
              <n-descriptions-item label="状态">
                <n-tag :type="activeTenant.status === 'active' ? 'success' : 'warning'" size="small">
                  {{ activeTenant.status === 'active' ? '启用' : '停用' }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="名称">{{ activeTenant.name }}</n-descriptions-item>
              <n-descriptions-item label="更新时间">{{ formatToDateTime(activeTenant.update_time) }}</n-descriptions-item>
              <n-descriptions-item label="备注" :span="2">{{ activeTenant.remark || '-' }}</n-descriptions-item>
            </n-descriptions>
          </n-tab-pane>

          <n-tab-pane name="users" tab="成员用户">
            <AppDataTable
              title="成员用户"
              size="small"
              :columns="userColumns"
              :data="tenantUsers"
              :loading="usersLoading"
              :pagination="{ pageSize: 20 }"
            >
              <template #actions>
                <n-button type="primary" @click="openUserCreate">新增成员</n-button>
                <n-button @click="loadTenantUsers">刷新</n-button>
              </template>
            </AppDataTable>
          </n-tab-pane>

          <n-tab-pane name="keys" tab="API Key">
            <AppDataTable
              title="API Key"
              size="small"
              :columns="keyColumns"
              :data="tenantKeys"
              :loading="keysLoading"
              :pagination="{ pageSize: 20 }"
            >
              <template #actions>
                <n-button type="primary" @click="keyCreateVisible = true">新建 Key</n-button>
                <n-button @click="loadTenantKeys">刷新</n-button>
              </template>
            </AppDataTable>
          </n-tab-pane>

          <n-tab-pane name="init" tab="初始化状态">
            <n-result status="success" title="租户基础数据已初始化">
              <template #footer>
                <span class="text-gray-500">默认 RBAC、菜单与租户上下文由后端初始化和校验。</span>
              </template>
            </n-result>
          </n-tab-pane>
        </n-tabs>
      </n-drawer-content>
    </n-drawer>

    <n-modal v-model:show="userModalVisible" preset="card" :style="{ width: '640px' }" :bordered="false">
      <template #header>{{ userFormMode === 'create' ? '新增成员' : '编辑成员' }}</template>
      <n-form ref="userFormRef" :model="userForm" :rules="userRules" label-placement="left" :label-width="110">
        <n-form-item label="用户名" path="username">
          <n-input v-model:value="userForm.username" />
        </n-form-item>
        <n-form-item :label="userFormMode === 'create' ? '初始密码' : '新密码'" path="password">
          <n-input v-model:value="userForm.password" type="password" show-password-on="mousedown" />
        </n-form-item>
        <n-form-item label="角色" path="role_keys">
          <n-select v-model:value="userForm.role_keys" multiple filterable clearable :options="roleOptions" />
        </n-form-item>
        <n-form-item label="启用" path="is_active">
          <n-switch v-model:value="userForm.is_active" />
        </n-form-item>
        <n-form-item label="租户管理员" path="is_tenant_admin">
          <n-switch v-model:value="userForm.is_tenant_admin" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="userModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="savingUser" @click="submitUser">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="keyCreateVisible" preset="dialog" title="新建 API Key" positive-text="创建" @positive-click="createKey">
      <n-input v-model:value="newKeyName" placeholder="Key 名称" />
    </n-modal>

    <n-modal v-model:show="createdKeyVisible" preset="card" title="API Key 已创建" style="width: 620px">
      <n-alert type="warning" class="mb-3">Key 只显示一次，请妥善保存。</n-alert>
      <n-input :value="createdKey" readonly type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { useRoute } from 'vue-router';
  import { NButton, NTag, useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import {
    activateTenant,
    createCurrentTenantApiKey,
    createCurrentTenantUser,
    createTenant,
    createTenantApiKey,
    createTenantUser,
    getCurrentTenantRoles,
    getCurrentTenantApiKeys,
    getCurrentTenantUsers,
    getRbacRoles,
    getTenantApiKeys,
    getTenantUsers,
    getTenants,
    revokeCurrentTenantApiKey,
    revokeTenantApiKey,
    suspendTenant,
    updateTenant,
    updateCurrentTenantUser,
    updateTenantUser,
  } from '@/api/business';
  import { useUserStore } from '@/store/modules/user';
  import { assignTenantAppearanceTheme, getAppearanceThemes, getTenantAppearanceTheme } from '@/api/appearance';
  import AppDataTable from '@/components/Application/AppDataTable.vue';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
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

  const message = useMessage();
  const userStore = useUserStore();
  const route = useRoute();
  const query = ref('');
  const loading = ref(false);
  const tenants = ref<TenantRow[]>([]);
  const tenantModalVisible = ref(false);
  const tenantFormMode = ref<'create' | 'edit'>('create');
  const savingTenant = ref(false);
  const tenantFormRef = ref<FormInst | null>(null);
  const tenantForm = reactive({ id: 0, key: '', name: '', status: 'active', remark: '', theme_id: null as number | null });
  const tenantAdminForm = reactive({ username: '', password: '' });
  const detailVisible = ref(false);
  const activeTenant = ref<TenantRow | null>(null);
  const tenantUsers = ref<Recordable[]>([]);
  const tenantKeys = ref<Recordable[]>([]);
  const usersLoading = ref(false);
  const keysLoading = ref(false);
  const userModalVisible = ref(false);
  const userFormMode = ref<'create' | 'edit'>('create');
  const savingUser = ref(false);
  const userFormRef = ref<FormInst | null>(null);
  const roleOptions = ref<SelectOption[]>([]);
  const themeOptions = ref<SelectOption[]>([]);
  const themesLoading = ref(false);
  const userForm = reactive({
    id: 0,
    username: '',
    password: '',
    role_keys: [] as string[],
    is_active: true,
    is_superuser: false,
    is_tenant_admin: false,
  });
  const keyCreateVisible = ref(false);
  const createdKeyVisible = ref(false);
  const createdKey = ref('');
  const newKeyName = ref('');
  const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);
  const isTenantUserManagement = computed(() => String(route.name || '') === 'tenant-user-management');
  const isPlatformTenantManagement = computed(() => isPlatformAdmin.value && !isTenantUserManagement.value);
  const pageTitle = computed(() => (isPlatformTenantManagement.value ? '租户管理' : '成员管理'));
  const pageDescription = computed(() =>
    isPlatformTenantManagement.value ? '管理平台租户、成员用户与租户级 API Key。' : '管理当前租户的成员账号、角色和启用状态。'
  );

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
    password: userFormMode.value === 'create' ? [{ required: true, message: '请输入初始密码', trigger: ['blur', 'input'] }] : [],
  }));

  const tenantColumns: DataTableColumns<TenantRow> = [
    { title: 'ID', key: 'id', width: 80 },
    { title: '租户 Key', key: 'tenant_key', minWidth: 160 },
    { title: '名称', key: 'name', minWidth: 180 },
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
    { title: '更新时间', key: 'update_time', width: 190, render: (row) => formatToDateTime(row.update_time) },
    {
      title: '操作',
      key: 'actions',
      width: 250,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '详情', onClick: () => openDetail(row) },
            { label: '编辑', onClick: () => openEdit(row) },
            {
              label: row.status === 'active' ? '停用' : '启用',
              tone: row.status === 'active' ? 'danger' : 'primary',
              confirm: true,
              confirmTitle: row.status === 'active' ? '停用租户' : '启用租户',
              confirmContent: `确认${row.status === 'active' ? '停用' : '启用'}租户「${row.name}」吗？`,
              onConfirm: () => toggleTenant(row),
            },
          ],
        });
      },
    },
  ];

  const userColumns: DataTableColumns<Recordable> = [
    { title: '用户名', key: 'username', minWidth: 160 },
    {
      title: '角色',
      key: 'roles',
      minWidth: 220,
      render(row) {
        const roles = row.roles || [];
        return h('div', {}, roles.length ? roles.map((role) => h(NTag, { size: 'small', type: 'info', style: 'margin-right:6px' }, () => role.name || role.key)) : '-');
      },
    },
    { title: '租户管理员', key: 'is_tenant_admin', width: 120, render: (row) => (row.is_tenant_admin ? '是' : '否') },
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
      width: 110,
      render: (row) =>
        h(AppTableActions, {
          actions: [{ label: '编辑', onClick: () => openUserEdit(row) }],
        }),
    },
  ];

  const keyColumns: DataTableColumns<Recordable> = [
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
    { title: '创建时间', key: 'create_time', width: 190, render: (row) => formatToDateTime(row.create_time) },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render(row) {
        return h(AppTableActions, {
          actions: [
            {
              label: '撤销',
              tone: 'danger',
              disabled: !row.is_active,
              confirm: true,
              confirmTitle: '撤销 API Key',
              confirmContent: `确认撤销 API Key「${row.name || row.prefix}」吗？`,
              onConfirm: () => revokeKey(row),
            },
          ],
        });
      },
    },
  ];

  function resetTenantForm() {
    tenantForm.id = 0;
    tenantForm.key = '';
    tenantForm.name = '';
    tenantForm.status = 'active';
    tenantForm.remark = '';
    tenantForm.theme_id = null;
    tenantAdminForm.username = '';
    tenantAdminForm.password = '';
    tenantFormRef.value?.restoreValidation();
  }

  function openCreate() {
    tenantFormMode.value = 'create';
    resetTenantForm();
    tenantModalVisible.value = true;
  }

  async function openEdit(row: TenantRow) {
    tenantFormMode.value = 'edit';
    tenantForm.id = row.id;
    tenantForm.key = row.tenant_key;
    tenantForm.name = row.name;
    tenantForm.status = row.status;
    tenantForm.remark = row.remark || '';
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
      themeOptions.value = (payload.items || [])
        .filter((theme) => theme.status === 'published')
        .map((theme) => ({ label: theme.name || `主题 ${theme.id}`, value: Number(theme.id) }));
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
        ...(tenantFormMode.value === 'create'
          ? { admin_username: tenantAdminForm.username, admin_password: tenantAdminForm.password }
          : {}),
      };
      if (tenantFormMode.value === 'create') {
        await createTenant(payload);
      } else {
        await updateTenant(tenantForm.id, payload);
        await assignTenantAppearanceTheme(tenantForm.id, tenantForm.theme_id || null);
      }
      tenantModalVisible.value = false;
      await reload();
      message.success('租户已保存');
    } finally {
      savingTenant.value = false;
    }
  }

  function toggleTenant(row: TenantRow) {
    const nextActive = row.status !== 'active';
    return (async () => {
      if (nextActive) await activateTenant(row.id);
      else await suspendTenant(row.id);
      await reload();
    })();
  }

  async function openDetail(row: TenantRow) {
    activeTenant.value = row;
    detailVisible.value = true;
    await Promise.all([loadTenantUsers(), loadTenantKeys()]);
  }

  async function ensureRoles() {
    if (roleOptions.value.length) return;
    const payload = isPlatformTenantManagement.value ? await getRbacRoles() : await getCurrentTenantRoles();
    roleOptions.value = (payload.items || [])
      .filter((role) => role.role_scope === 'tenant')
      .map((role) => ({ label: role.name || role.key, value: role.key }));
  }

  async function loadTenantUsers() {
    if (!activeTenant.value) return;
    usersLoading.value = true;
    try {
      const payload = isPlatformTenantManagement.value ? await getTenantUsers(activeTenant.value.id) : await getCurrentTenantUsers();
      tenantUsers.value = payload.items || [];
    } finally {
      usersLoading.value = false;
    }
  }

  async function loadTenantKeys() {
    if (!activeTenant.value) return;
    keysLoading.value = true;
    try {
      const payload = isPlatformTenantManagement.value ? await getTenantApiKeys(activeTenant.value.id) : await getCurrentTenantApiKeys();
      tenantKeys.value = payload.items || [];
    } finally {
      keysLoading.value = false;
    }
  }

  async function openUserCreate() {
    await ensureRoles();
    userFormMode.value = 'create';
    Object.assign(userForm, { id: 0, username: '', password: '', role_keys: [], is_active: true, is_superuser: false, is_tenant_admin: false });
    userModalVisible.value = true;
  }

  async function openUserEdit(row: Recordable) {
    await ensureRoles();
    userFormMode.value = 'edit';
    Object.assign(userForm, {
      id: row.id,
      username: row.username,
      password: '',
      role_keys: (row.roles || []).map((role) => role.key),
      is_active: !!row.is_active,
      is_superuser: !!row.is_superuser,
      is_tenant_admin: !!row.is_tenant_admin,
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
      const payload = {
        username: userForm.username,
        password: userForm.password,
        role_keys: userForm.role_keys,
        is_active: userForm.is_active,
        is_superuser: userForm.is_superuser,
        is_tenant_admin: userForm.is_tenant_admin,
      };
      if (userFormMode.value === 'create') {
        if (isPlatformTenantManagement.value) await createTenantUser(activeTenant.value.id, payload);
        else await createCurrentTenantUser(payload);
      } else if (isPlatformTenantManagement.value) await updateTenantUser(activeTenant.value.id, userForm.id, payload);
      else await updateCurrentTenantUser(userForm.id, payload);
      userModalVisible.value = false;
      await loadTenantUsers();
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

  async function revokeKey(row: Recordable) {
    if (!activeTenant.value) return;
    if (isPlatformTenantManagement.value) await revokeTenantApiKey(activeTenant.value.id, Number(row.id));
    else await revokeCurrentTenantApiKey(Number(row.id));
    await loadTenantKeys();
  }

  async function reload() {
    loading.value = true;
    try {
      if (isPlatformTenantManagement.value) {
        const payload = await getTenants({ q: query.value || undefined });
        tenants.value = payload.items || [];
      } else {
        const tenant = userStore.info?.current_tenant as TenantRow | undefined;
        activeTenant.value = tenant ? { ...tenant, user_count: 0, api_key_count: 0 } : null;
        tenants.value = activeTenant.value ? [activeTenant.value] : [];
        await loadTenantUsers();
      }
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>
