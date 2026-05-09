<template>
  <div>
    <div class="n-layout-page-header">
      <n-card :bordered="false" title="用户管理">
        这里维护后台登录用户、角色分配、启用状态和超级用户标记。
      </n-card>
    </div>

    <n-card :bordered="false" size="small" class="proCard mt-4">
      <AppDataTable
        title="用户列表"
        description="维护后台登录用户、角色分配、启用状态和超级用户标记。"
        size="small"
        :columns="columns"
        :data="rows"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
        :row-key="(row) => row.id"
        :scroll-x="1380"
      >
        <template #actions>
          <n-button type="primary" @click="handleCreate">
            <template #icon>
              <n-icon>
                <PlusOutlined />
              </n-icon>
            </template>
            新增用户
          </n-button>
        </template>
      </AppDataTable>
    </n-card>

    <n-modal v-model:show="userModalVisible" preset="card" :style="{ width: '640px' }" :bordered="false">
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
        <n-form-item label="用户名" path="username">
          <n-input v-model:value="userForm.username" placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item :label="userFormMode === 'create' ? '初始密码' : '新密码'" path="password">
          <n-input
            v-model:value="userForm.password"
            type="password"
            show-password-on="mousedown"
            :placeholder="userFormMode === 'create' ? '请输入初始密码' : '留空表示不修改密码'"
          />
        </n-form-item>
        <n-form-item label="角色分配" path="role_keys">
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
            <template #unchecked>禁用</template>
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
  import { PlusOutlined } from '@vicons/antd';
  import { createRbacUser, getRbacRoles, getRbacUsers, updateRbacUser } from '@/api/business';
  import AppDataTable from '@/components/Application/AppDataTable.vue';
  import AppStatusGroup from '@/components/Application/AppStatusGroup.vue';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { formatToDateTime } from '@/utils/dateUtil';

  interface UserRole extends Recordable {
    key: string;
    name: string;
  }

  interface UserRow extends Recordable {
    id: number;
    username: string;
    roles?: UserRole[];
    is_active: boolean;
    is_superuser: boolean;
    create_time?: string;
    update_time?: string;
  }

  interface UserFormState {
    id: number | null;
    username: string;
    password: string;
    role_keys: string[];
    is_active: boolean;
    is_superuser: boolean;
  }

  const message = useMessage();
  const loading = ref(false);
  const savingUser = ref(false);
  const rolesLoading = ref(false);
  const rows = ref<UserRow[]>([]);
  const roleOptions = ref<SelectOption[]>([]);
  const userFormRef = ref<FormInst | null>(null);
  const userModalVisible = ref(false);
  const userFormMode = ref<'create' | 'edit'>('create');
  const userForm = reactive<UserFormState>({
    id: null,
    username: '',
    password: '',
    role_keys: [],
    is_active: true,
    is_superuser: false,
  });

  const userModalTitle = computed(() => (userFormMode.value === 'create' ? '新增用户' : '编辑用户'));
  const userSubmitText = computed(() => (userFormMode.value === 'create' ? '提交' : '保存'));

  const userRules = computed<FormRules>(() => ({
    username: [{ required: true, message: '请输入用户名', trigger: ['blur', 'input'] }],
    password:
      userFormMode.value === 'create'
        ? [{ required: true, message: '请输入初始密码', trigger: ['blur', 'input'] }]
        : [],
  }));

  const columns: DataTableColumns<UserRow> = [
    { title: 'ID', key: 'id', width: 80 },
    { title: '用户名', key: 'username', minWidth: 180 },
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
          label: row.is_active ? '启用' : '禁用',
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
            { label: '编辑', onClick: () => handleEdit(row) },
            {
              label: row.is_active ? '禁用' : '启用',
              tone: row.is_active ? 'danger' : 'primary',
              confirm: true,
              confirmTitle: row.is_active ? '禁用用户' : '启用用户',
              confirmContent: `确认${row.is_active ? '禁用' : '启用'}用户「${row.username}」吗？`,
              onConfirm: () => handleToggleActive(row),
            },
          ],
        });
      },
    },
  ];

  function resetUserForm() {
    userForm.id = null;
    userForm.username = '';
    userForm.password = '';
    userForm.role_keys = [];
    userForm.is_active = true;
    userForm.is_superuser = false;
    userFormRef.value?.restoreValidation();
  }

  function applyUserToForm(row: UserRow) {
    userForm.id = row.id;
    userForm.username = String(row.username || '');
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
      roleOptions.value = (payload.items || []).map((role) => ({
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
        password: userForm.password,
        role_keys: userForm.role_keys,
        is_active: userForm.is_active,
        is_superuser: userForm.is_superuser,
      };

      if (userFormMode.value === 'create') {
        await createRbacUser(payload);
        message.success('用户已新增');
      } else if (userForm.id) {
        await updateRbacUser(userForm.id, payload);
        message.success('用户已更新');
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
        await updateRbacUser(row.id, {
          username: row.username,
          password: '',
          role_keys: (row.roles || []).map((role) => String(role.key)),
          is_active: nextActive,
          is_superuser: !!row.is_superuser,
        });
        await reload();
        message.success(`用户已${nextActive ? '启用' : '禁用'}`);
      } catch (error) {
        message.error(error instanceof Error ? error.message : '用户状态更新失败');
        throw error;
      }
    })();
  }

  async function reload() {
    loading.value = true;
    try {
      const payload = await getRbacUsers();
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>
