<template>
  <div>
    <ListPageRuntime :schema="userListPage" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload">
      <template #filters>
        <n-input v-model:value="query.keyword" clearable placeholder="搜索用户名、姓名或邮箱" @keyup.enter="reload" />
        <n-select
          v-model:value="query.status"
          clearable
          placeholder="用户状态"
          :options="statusOptions"
          @update:value="reload"
        />
        <n-button secondary @click="resetQuery">重置</n-button>
        <n-button type="primary" @click="reload">查询</n-button>
      </template>
    </ListPageRuntime>

    <n-modal v-model:show="userModalVisible" preset="card" :style="{ width: '680px' }" :bordered="false">
      <template #header>
        <span>{{ userModalTitle }}</span>
      </template>

      <n-form
        ref="userFormRef"
        :model="userForm"
        :rules="userRules"
        label-placement="left"
        :label-width="110"
      >
        <n-form-item label="姓名" path="full_name">
          <n-input v-model:value="userForm.full_name" placeholder="请输入用户姓名" />
        </n-form-item>
        <n-form-item label="用户名" path="username">
          <n-input v-model:value="userForm.username" placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="userForm.email" placeholder="请输入邮箱" />
        </n-form-item>
        <n-form-item :label="userFormMode === 'create' ? '登录密码' : '重置密码'" path="password">
          <n-input
            v-model:value="userForm.password"
            type="password"
            show-password-on="mousedown"
            :placeholder="userFormMode === 'create' ? '请输入登录密码' : '留空则不修改密码'"
          />
        </n-form-item>
        <n-form-item label="角色" path="role_keys">
          <n-select
            v-model:value="userForm.role_keys"
            multiple
            filterable
            clearable
            :options="roleOptions"
            placeholder="请选择用户角色"
          />
        </n-form-item>
        <n-form-item label="启用状态" path="is_active">
          <n-switch v-model:value="userForm.is_active">
            <template #checked>启用</template>
            <template #unchecked>停用</template>
          </n-switch>
        </n-form-item>
        <n-form-item label="超级用户" path="is_superuser">
          <n-switch v-model:value="userForm.is_superuser">
            <template #checked>是</template>
            <template #unchecked>否</template>
          </n-switch>
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="userModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="savingUser" @click="submitUserForm">{{ userSubmitText }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import { createRbacUser, disableRbacUser, enableRbacUser, getRbacRoles, getRbacUsers, updateRbacUser } from '@/api/business';
  import AppStatusGroup from '@/components/Application/AppStatusGroup.vue';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { usePermission } from '@/hooks/web/usePermission';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { formatToDateTime } from '@/utils/dateUtil';

  interface UserRole extends Recordable {
    key: string;
    name: string;
  }

  interface UserRow extends Recordable {
    id: number;
    username: string;
    full_name?: string;
    email?: string;
    roles?: UserRole[];
    is_active: boolean;
    is_superuser: boolean;
    create_time?: string;
    update_time?: string;
  }

  interface UserFormState {
    id: number | null;
    username: string;
    full_name: string;
    email: string;
    password: string;
    role_keys: string[];
    is_active: boolean;
    is_superuser: boolean;
  }

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const savingUser = ref(false);
  const rolesLoading = ref(false);
  const rows = ref<UserRow[]>([]);
  const paginationTotal = ref(0);
  const roleOptions = ref<SelectOption[]>([]);
  const userFormRef = ref<FormInst | null>(null);
  const userModalVisible = ref(false);
  const userFormMode = ref<'create' | 'edit'>('create');
  const query = reactive({
    keyword: '',
    status: null as 'active' | 'disabled' | null,
  });
  const userForm = reactive<UserFormState>({
    id: null,
    username: '',
    full_name: '',
    email: '',
    password: '',
    role_keys: [],
    is_active: true,
    is_superuser: false,
  });

  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const statusOptions: SelectOption[] = [
    { label: '启用', value: 'active' },
    { label: '停用', value: 'disabled' },
  ];
  const userModalTitle = computed(() => (userFormMode.value === 'create' ? '新增用户' : '编辑用户'));
  const userSubmitText = computed(() => (userFormMode.value === 'create' ? '创建' : '保存'));

  const userRules = computed<FormRules>(() => ({
    username: [{ required: true, message: '请输入用户名', trigger: ['blur', 'input'] }],
    full_name: [{ required: true, message: '请输入姓名', trigger: ['blur', 'input'] }],
    email: [
      {
        validator: (_rule, value: string) => !value || emailPattern.test(String(value).trim()),
        message: '请输入正确的邮箱',
        trigger: ['blur', 'input'],
      },
    ],
    password:
      userFormMode.value === 'create'
        ? [{ required: true, message: '请输入登录密码', trigger: ['blur', 'input'] }]
        : [],
  }));

  const columns: DataTableColumns<UserRow> = [
    { title: 'ID', key: 'id', width: 80 },
    { title: '用户名', key: 'username', minWidth: 180 },
    { title: '姓名', key: 'full_name', minWidth: 160 },
    { title: '邮箱', key: 'email', minWidth: 220, render: (row) => row.email || '-' },
    {
      title: '角色',
      key: 'roles',
      minWidth: 240,
      render(row) {
        const roles = row.roles || [];
        return h(AppStatusGroup, {
          items: roles.length
            ? roles.map((role) => ({
                key: String(role.key || role.name),
                label: String(role.name || role.key),
                tone: 'info',
              }))
            : [{ statusKey: 'unassigned' }],
        });
      },
    },
    {
      title: '状态',
      key: 'is_active',
      width: 100,
      render(row) {
        return h(AppStatusTag, {
          tone: row.is_active ? 'success' : 'error',
          label: row.is_active ? '启用' : '停用',
        });
      },
    },
    {
      title: '超级用户',
      key: 'is_superuser',
      width: 120,
      render(row) {
        return h(AppStatusTag, {
          tone: row.is_superuser ? 'warning' : 'neutral',
          label: row.is_superuser ? '是' : '否',
        });
      },
    },
    {
      title: '创建时间',
      key: 'create_time',
      width: 220,
      render: (row) => formatToDateTime(row.create_time),
    },
    {
      title: '更新时间',
      key: 'update_time',
      width: 220,
      render: (row) => formatToDateTime(row.update_time),
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['system:users:update']), onClick: () => handleEdit(row) },
            {
              label: row.is_active ? '停用' : '启用',
              tone: row.is_active ? 'danger' : 'primary',
              show: hasPermission([row.is_active ? 'system:users:disable' : 'system:users:enable']),
              confirm: true,
              confirmTitle: row.is_active ? '停用用户' : '启用用户',
              confirmContent: `确认${row.is_active ? '停用' : '启用'}用户「${row.username}」？`,
              onConfirm: () => handleToggleActive(row),
            },
          ],
        });
      },
    },
  ];

  const userListPage = defineListPage<UserRow>({
    id: 'rbac.users',
    title: '用户管理',
    description: '统一管理用户、角色关系、绑定邮箱和用户状态。',
    variant: 'enterprise',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1600,
      sort: { remote: true },
      columnRuntime: {
        columns: [
          { key: 'id', sortable: true },
          { key: 'username', sortable: true },
          { key: 'full_name', sortable: true },
          { key: 'email', sortable: true },
          { key: 'roles', sortable: false },
          { key: 'is_active', sortable: true },
          { key: 'is_superuser', sortable: true },
          { key: 'create_time', sortable: true },
          { key: 'update_time', sortable: true },
          { key: 'actions', required: true, sortable: false },
        ],
      },
      tableProps: {
        size: 'small',
      },
    },
    filters: [
      { key: 'keyword', type: 'keyword', placeholder: '搜索用户名、姓名或邮箱' },
      { key: 'status', type: 'select', placeholder: '用户状态', options: statusOptions },
    ],
    toolbar: {
      primaryAction: hasPermission(['system:users:create'])
        ? { key: 'create', label: '新增用户', type: 'primary', onClick: () => handleCreate() }
        : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  function resetUserForm() {
    userForm.id = null;
    userForm.username = '';
    userForm.full_name = '';
    userForm.email = '';
    userForm.password = '';
    userForm.role_keys = [];
    userForm.is_active = true;
    userForm.is_superuser = false;
    userFormRef.value?.restoreValidation();
  }

  function applyUserToForm(row: UserRow) {
    userForm.id = row.id;
    userForm.username = String(row.username || '');
    userForm.full_name = String(row.full_name || '');
    userForm.email = String(row.email || '');
    userForm.password = '';
    userForm.role_keys = (row.roles || []).map((role) => String(role.key));
    userForm.is_active = !!row.is_active;
    userForm.is_superuser = !!row.is_superuser;
    userFormRef.value?.restoreValidation();
  }

  async function ensureRolesLoaded() {
    if (roleOptions.value.length) {
      return;
    }
    rolesLoading.value = true;
    try {
      const payload = await getRbacRoles();
      roleOptions.value = (payload.items || [])
        .filter((role) => role.role_scope === 'platform')
        .map((role) => ({
          label: String(role.name || role.key),
          value: String(role.key),
        }));
    } finally {
      rolesLoading.value = false;
    }
  }

  async function submitUserForm() {
    try {
      await userFormRef.value?.validate();
    } catch {
      return;
    }

    savingUser.value = true;
    try {
      const payload = {
        username: userForm.username.trim(),
        full_name: userForm.full_name.trim(),
        email: userForm.email.trim(),
        password: userForm.password,
        role_keys: userForm.role_keys,
        is_active: userForm.is_active,
        is_superuser: userForm.is_superuser,
      };

      if (userFormMode.value === 'create') {
        await createRbacUser(payload);
        message.success('用户创建成功');
      } else if (userForm.id) {
        await updateRbacUser(userForm.id, payload);
        message.success('用户保存成功');
      }

      userModalVisible.value = false;
      resetUserForm();
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '用户保存失败');
    } finally {
      savingUser.value = false;
    }
  }

  async function handleCreate() {
    await ensureRolesLoaded();
    userFormMode.value = 'create';
    resetUserForm();
    userModalVisible.value = true;
  }

  async function handleEdit(row: UserRow) {
    await ensureRolesLoaded();
    userFormMode.value = 'edit';
    applyUserToForm(row);
    userModalVisible.value = true;
  }

  function handleToggleActive(row: UserRow) {
    const nextActive = !row.is_active;
    return (async () => {
      try {
        if (nextActive) await enableRbacUser(row.id);
        else await disableRbacUser(row.id);
        await reload();
        message.success(`用户已${nextActive ? '启用' : '停用'}`);
      } catch (error) {
        message.error(error instanceof Error ? error.message : '用户状态更新失败');
        throw error;
      }
    })();
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const payload = await getRbacUsers(runtimeListParams(state));
      rows.value = payload.items || [];
      paginationTotal.value = payload.pagination?.total || rows.value.length;
    } finally {
      loading.value = false;
    }
  }

  function resetQuery() {
    query.keyword = '';
    query.status = null;
    reload();
  }

  reload();
</script>
