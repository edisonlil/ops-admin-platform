<template>
  <div class="data-scope-page">
    <ListPageRuntime :schema="scopePage" :rows="filteredRows" :loading="loading" @refresh="reload">
      <template #filters>
        <n-select v-model:value="roleFilter" clearable filterable placeholder="角色" :options="roleOptions" class="data-scope-page__filter" />
        <n-select
          v-model:value="resourceFilter"
          clearable
          filterable
          placeholder="数据资源"
          :options="resourceOptions"
          class="data-scope-page__filter"
        />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="620">
      <n-drawer-content :title="form.id ? '编辑数据权限' : '配置数据权限'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="角色" path="role_key">
              <n-select v-model:value="form.role_key" filterable :options="roleOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="数据资源" path="resource_key">
              <n-select v-model:value="form.resource_key" filterable :options="resourceOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="动作" path="action">
              <n-input v-model:value="form.action" placeholder="read" />
            </n-form-item-gi>
            <n-form-item-gi label="权限范围" path="scope">
              <n-select v-model:value="form.scope" :options="scopeOptions" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item v-if="form.scope === 'custom_departments'" label="自定义部门" path="department_ids">
            <n-select
              v-model:value="form.department_ids"
              multiple
              clearable
              filterable
              :options="departmentOptions"
              placeholder="选择允许访问的部门"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存配置</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deleteRoleDataScope,
    getAuthorizationResources,
    getDepartments,
    getRbacRoles,
    getRoleDataScopes,
    saveRoleDataScope,
    type RoleDataScopePayload,
  } from '@/api/business';

  interface RoleRow extends Recordable {
    id: number;
    key: string;
    name: string;
    role_scope?: string;
  }

  interface ResourceRow extends Recordable {
    resource_key: string;
    name: string;
    supported_scopes?: string[];
  }

  interface DepartmentRow extends Recordable {
    id: number;
    parent_id?: number | null;
    code: string;
    name: string;
  }

  interface ScopeRow extends RoleDataScopePayload {
    id: number;
    create_time?: string;
    update_time?: string;
  }

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<ScopeRow[]>([]);
  const roles = ref<RoleRow[]>([]);
  const resources = ref<ResourceRow[]>([]);
  const departments = ref<DepartmentRow[]>([]);
  const roleFilter = ref<string | null>(null);
  const resourceFilter = ref<string | null>(null);
  const form = reactive<Partial<ScopeRow>>({
    role_key: '',
    resource_key: '',
    action: 'read',
    scope: 'self',
    department_ids: [],
  });

  const scopeOptions: SelectOption[] = [
    { label: '本人数据', value: 'self' },
    { label: '本部门数据', value: 'department' },
    { label: '本部门及下级数据', value: 'department_and_children' },
    { label: '自定义部门数据', value: 'custom_departments' },
    { label: '当前租户全部数据', value: 'tenant' },
  ];

  const rules: FormRules = {
    role_key: [{ required: true, message: '请选择角色', trigger: ['blur', 'change'] }],
    resource_key: [{ required: true, message: '请选择数据资源', trigger: ['blur', 'change'] }],
    scope: [{ required: true, message: '请选择权限范围', trigger: ['blur', 'change'] }],
  };

  const roleOptions = computed<SelectOption[]>(() => roles.value.map((role) => ({ label: `${role.name || role.key} (${role.key})`, value: role.key })));
  const resourceOptions = computed<SelectOption[]>(() =>
    resources.value.map((resource) => ({ label: `${resource.name || resource.resource_key} (${resource.resource_key})`, value: resource.resource_key }))
  );
  const departmentOptions = computed<SelectOption[]>(() =>
    departments.value.map((department) => ({ label: `${departmentPath(department)} (${department.code})`, value: department.id }))
  );
  const filteredRows = computed(() =>
    rows.value.filter((row) => {
      const matchedRole = !roleFilter.value || row.role_key === roleFilter.value;
      const matchedResource = !resourceFilter.value || row.resource_key === resourceFilter.value;
      return matchedRole && matchedResource;
    })
  );

  const columns: DataTableColumns<ScopeRow> = [
    { title: '角色', key: 'role_key', minWidth: 190, render: (row) => roleLabel(row.role_key) },
    { title: '数据资源', key: 'resource_key', minWidth: 220, render: (row) => resourceLabel(row.resource_key) },
    { title: '动作', key: 'action', width: 90 },
    {
      title: '权限范围',
      key: 'scope',
      width: 160,
      render(row) {
        return h(AppStatusTag, { tone: row.scope === 'tenant' ? 'success' : 'info', label: scopeLabel(String(row.scope)) });
      },
    },
    { title: '自定义部门', key: 'department_ids', minWidth: 220, render: (row) => departmentNames(row.department_ids || []) },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['authorization:data-scope:manage']), onClick: () => openEdit(row) },
            {
              label: '删除',
              tone: 'danger',
              show: hasPermission(['authorization:data-scope:manage']),
              confirm: true,
              confirmTitle: '删除数据权限',
              confirmContent: `确认删除 ${roleLabel(row.role_key)} 的 ${resourceLabel(row.resource_key)} 权限？`,
              onConfirm: () => remove(row),
            },
          ],
        });
      },
    },
  ];

  const scopePage = computed(() =>
    defineListPage<ScopeRow>({
      id: 'authorization.data-scope',
      title: '数据权限',
      description: '按角色配置数据访问范围，授权模块通过可插拔 provider 聚合 RBAC、组织部门和资源描述。',
      variant: 'dense-data',
      density: 'compact',
      view: {
        type: 'table',
        columns,
        rowKey: (row) => Number(row.id),
        scrollX: 1220,
        tableProps: { size: 'small' },
      },
      toolbar: {
        primaryAction: hasPermission(['authorization:data-scope:manage'])
          ? { key: 'create', label: '新增配置', type: 'primary', onClick: () => openCreate() }
          : undefined,
        rightTools: ['refresh'],
      },
      pagination: { pageSize: 20 },
    })
  );

  function resetForm() {
    Object.assign(form, {
      id: undefined,
      role_key: roleFilter.value || '',
      resource_key: resourceFilter.value || resources.value[0]?.resource_key || '',
      action: 'read',
      scope: 'self',
      department_ids: [],
    });
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: ScopeRow) {
    Object.assign(form, { ...row, department_ids: [...(row.department_ids || [])] });
    drawerVisible.value = true;
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      await saveRoleDataScope({
        role_key: String(form.role_key || ''),
        resource_key: String(form.resource_key || ''),
        action: String(form.action || 'read'),
        scope: String(form.scope || 'self'),
        department_ids: form.scope === 'custom_departments' ? [...(form.department_ids || [])] : [],
      });
      message.success('数据权限已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function remove(row: ScopeRow) {
    await deleteRoleDataScope(row.id);
    message.success('数据权限已删除');
    await reload();
  }

  function scopeLabel(value: string) {
    return String(scopeOptions.find((item) => item.value === value)?.label || value);
  }

  function roleLabel(roleKey: string) {
    const role = roles.value.find((item) => item.key === roleKey);
    return role ? `${role.name || role.key} (${role.key})` : roleKey;
  }

  function resourceLabel(resourceKey: string) {
    const resource = resources.value.find((item) => item.resource_key === resourceKey);
    return resource ? `${resource.name || resource.resource_key}` : resourceKey;
  }

  function departmentNames(ids: number[]) {
    if (!ids.length) return '-';
    const names = ids.map((id) => departments.value.find((item) => item.id === id)).filter(Boolean).map((item) => departmentPath(item as DepartmentRow));
    return names.length ? names.join('、') : ids.join('、');
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

  async function reload() {
    loading.value = true;
    try {
      const [rolePayload, resourcePayload, scopePayload] = await Promise.all([getRbacRoles(), getAuthorizationResources(), getRoleDataScopes()]);
      roles.value = rolePayload.items || [];
      resources.value = resourcePayload.items || [];
      rows.value = scopePayload.items || [];
      try {
        const departmentPayload = await getDepartments({ include_disabled: false });
        departments.value = departmentPayload.items || [];
      } catch {
        departments.value = [];
      }
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>

<style lang="less" scoped>
  .data-scope-page {
    min-width: 0;
  }

  .data-scope-page__filter {
    width: min(280px, 100%);
  }
</style>
