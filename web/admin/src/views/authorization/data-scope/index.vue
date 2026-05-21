<template>
  <div class="data-scope-page">
    <ListPageRuntime :schema="scopePage" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload">
      <template #filters>
        <n-select v-model:value="subjectTypeFilter" clearable placeholder="主体类型" :options="subjectTypeOptions" class="data-scope-page__filter" />
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

    <n-drawer v-model:show="drawerVisible" width="660">
      <n-drawer-content :title="form.id ? '编辑数据权限' : '配置数据权限'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="主体类型" path="subject_type">
              <n-select v-model:value="form.subject_type" :options="subjectTypeOptions" @update:value="handleSubjectTypeChange" />
            </n-form-item-gi>
            <n-form-item-gi label="业务主体" path="subject_id">
              <n-tree-select
                v-if="form.subject_type === 'department'"
                v-model:value="form.subject_id"
                clearable
                filterable
                checkable
                block-line
                default-expand-all
                :options="departmentTreeOptions"
              />
              <n-select v-else v-model:value="form.subject_id" filterable :options="userOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="数据资源" path="resource_key">
              <n-select v-model:value="form.resource_key" filterable :options="resourceOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="动作" path="action">
              <n-select v-model:value="form.action" :options="actionOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="权限范围" path="scope">
              <n-select v-model:value="form.scope" :options="scopeOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="优先级" path="priority">
              <n-input-number v-model:value="form.priority" :min="0" :max="10000" class="data-scope-page__number" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item v-if="form.scope === 'custom_departments'" label="自定义部门" path="department_ids">
            <n-tree-select
              v-model:value="form.department_ids"
              multiple
              clearable
              filterable
              cascade
              checkable
              block-line
              default-expand-all
              :options="departmentTreeOptions"
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
  import type { DataTableColumns, FormInst, FormRules, SelectOption, TreeSelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    deleteDataAccessPolicy,
    getAuthorizationResources,
    getCurrentTenantUsers,
    getDataAccessPolicies,
    getDepartments,
    saveDataAccessPolicy,
    type DataAccessPolicyPayload,
  } from '@/api/business';

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

  interface UserRow extends Recordable {
    id: number;
    username: string;
  }

  interface PolicyRow extends DataAccessPolicyPayload {
    id: number;
    create_time?: string;
    update_time?: string;
  }

  type SubjectType = 'department' | 'user';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<PolicyRow[]>([]);
  const paginationTotal = ref(0);
  const resources = ref<ResourceRow[]>([]);
  const departments = ref<DepartmentRow[]>([]);
  const users = ref<UserRow[]>([]);
  const subjectTypeFilter = ref<string | null>(null);
  const resourceFilter = ref<string | null>(null);
  const form = reactive<Partial<PolicyRow>>({
    subject_type: 'department',
    subject_id: undefined,
    resource_key: '',
    action: 'read',
    scope: 'self',
    department_ids: [],
    priority: 100,
  });

  const subjectTypeOptions: SelectOption[] = [
    { label: '部门', value: 'department' },
    { label: '用户', value: 'user' },
  ];

  const scopeOptions: SelectOption[] = [
    { label: '本人数据', value: 'self' },
    { label: '本部门数据', value: 'department' },
    { label: '本部门及下级数据', value: 'department_and_children' },
    { label: '自定义部门数据', value: 'custom_departments' },
    { label: '当前租户全部数据', value: 'tenant' },
  ];

  const actionOptions: SelectOption[] = [
    { label: '只读', value: 'read' },
    { label: '可读写', value: 'write' },
    { label: '可管理', value: 'manage' },
  ];

  const rules: FormRules = {
    subject_type: [{ required: true, message: '请选择主体类型', trigger: ['blur', 'change'] }],
    subject_id: [{ required: true, type: 'number', message: '请选择业务主体', trigger: ['blur', 'change'] }],
    resource_key: [{ required: true, message: '请选择数据资源', trigger: ['blur', 'change'] }],
    action: [{ required: true, message: '请选择动作', trigger: ['blur', 'change'] }],
    scope: [{ required: true, message: '请选择权限范围', trigger: ['blur', 'change'] }],
  };

  const resourceOptions = computed<SelectOption[]>(() =>
    resources.value.map((resource) => ({ label: `${resource.name || resource.resource_key} (${resource.resource_key})`, value: resource.resource_key }))
  );
  const departmentOptions = computed<SelectOption[]>(() =>
    departments.value.map((department) => ({ label: `${departmentPath(department)} (${department.code})`, value: department.id }))
  );
  const departmentTreeOptions = computed<TreeSelectOption[]>(() => buildDepartmentTreeOptions());
  const userOptions = computed<SelectOption[]>(() => users.value.map((user) => ({ label: `${user.username} (#${user.id})`, value: user.id })));
  const columns: DataTableColumns<PolicyRow> = [
    { title: '主体类型', key: 'subject_type', width: 110, render: (row) => subjectTypeLabel(String(row.subject_type)) },
    { title: '业务主体', key: 'subject_id', minWidth: 220, render: (row) => subjectLabel(row) },
    { title: '数据资源', key: 'resource_key', minWidth: 220, render: (row) => resourceLabel(row.resource_key) },
    { title: '动作', key: 'action', width: 90, render: (row) => actionLabel(String(row.action || 'read')) },
    {
      title: '权限范围',
      key: 'scope',
      width: 170,
      render(row) {
        return h(AppStatusTag, { tone: row.scope === 'tenant' ? 'success' : 'info', label: scopeLabel(String(row.scope)) });
      },
    },
    { title: '自定义部门', key: 'department_ids', minWidth: 220, render: (row) => departmentNames(row.department_ids || []) },
    { title: '优先级', key: 'priority', width: 90 },
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
              confirmContent: `确认删除 ${subjectLabel(row)} 的 ${resourceLabel(row.resource_key)} 权限？`,
              onConfirm: () => remove(row),
            },
          ],
        });
      },
    },
  ];

  const scopePage = computed(() =>
    defineListPage<PolicyRow>({
      id: 'authorization.data-scope',
      title: '数据权限',
      description: '租户管理员按部门或用户配置当前租户的数据访问范围，资源定义由平台统一维护。',
      variant: 'dense-data',
      density: 'compact',
      view: {
        type: 'table',
        columns,
        rowKey: (row) => Number(row.id),
        scrollX: 1380,
        sort: { remote: true },
        columnRuntime: {
          columns: [
            { key: 'subject_type', sortable: true },
            { key: 'subject_id', sortable: true },
            { key: 'resource_key', sortable: true },
            { key: 'action', sortable: true },
            { key: 'scope', sortable: true },
            { key: 'department_ids', sortable: false },
            { key: 'priority', sortable: true },
            { key: 'update_time', sortable: true },
            { key: 'actions', required: true, sortable: false },
          ],
        },
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
    const subjectType = (subjectTypeFilter.value || 'department') as SubjectType;
    Object.assign(form, {
      id: undefined,
      subject_type: subjectType,
      subject_id: defaultSubjectId(subjectType),
      resource_key: resourceFilter.value || resources.value[0]?.resource_key || '',
      action: 'read',
      scope: 'self',
      department_ids: [],
      priority: 100,
    });
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: PolicyRow) {
    Object.assign(form, { ...row, department_ids: [...(row.department_ids || [])] });
    drawerVisible.value = true;
  }

  function handleSubjectTypeChange(value: string) {
    form.subject_id = defaultSubjectId(value as SubjectType);
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      await saveDataAccessPolicy({
        subject_type: String(form.subject_type || 'department'),
        subject_id: Number(form.subject_id || 0),
        resource_key: String(form.resource_key || ''),
        action: String(form.action || 'read'),
        scope: String(form.scope || 'self'),
        department_ids: form.scope === 'custom_departments' ? [...(form.department_ids || [])] : [],
        priority: Number(form.priority ?? 100),
      });
      message.success('数据权限已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function remove(row: PolicyRow) {
    await deleteDataAccessPolicy(row.id);
    message.success('数据权限已删除');
    await reload();
  }

  function defaultSubjectId(subjectType: SubjectType) {
    return subjectType === 'user' ? users.value[0]?.id : departments.value[0]?.id;
  }

  function scopeLabel(value: string) {
    return String(scopeOptions.find((item) => item.value === value)?.label || value);
  }

  function actionLabel(value: string) {
    const aliasMap: Record<string, string> = {
      create: 'write',
      update: 'write',
      delete: 'manage',
      export: 'read',
      approve: 'manage',
    };
    const normalized = aliasMap[value] || value;
    return String(actionOptions.find((item) => item.value === normalized)?.label || value);
  }

  function subjectTypeLabel(value: string) {
    return String(subjectTypeOptions.find((item) => item.value === value)?.label || value);
  }

  function subjectLabel(row: Pick<PolicyRow, 'subject_type' | 'subject_id'>) {
    if (row.subject_type === 'user') {
      const user = users.value.find((item) => item.id === Number(row.subject_id));
      return user ? `${user.username} (#${user.id})` : `用户 #${row.subject_id}`;
    }
    const department = departments.value.find((item) => item.id === Number(row.subject_id));
    return department ? departmentPath(department) : `部门 #${row.subject_id}`;
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

  function buildDepartmentTreeOptions() {
    const byParent = new Map<number, DepartmentRow[]>();
    departments.value.forEach((department) => {
      byParent.set(Number(department.parent_id || 0), [...(byParent.get(Number(department.parent_id || 0)) || []), department]);
    });
    const build = (parentId: number): TreeSelectOption[] =>
      (byParent.get(parentId) || [])
        .sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0) || a.name.localeCompare(b.name))
        .map((department) => {
          const children = build(department.id);
          return {
            label: department.name,
            key: department.id,
            value: department.id,
            children: children.length ? children : undefined,
          };
        });
    return build(0);
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const [resourcePayload, scopePayload, userPayload] = await Promise.all([
        getAuthorizationResources(),
        getDataAccessPolicies({
          ...runtimeListParams(state),
          subject_type: subjectTypeFilter.value || undefined,
          resource_key: resourceFilter.value || undefined,
        }),
        getCurrentTenantUsers(),
      ]);
      resources.value = resourcePayload.items || [];
      rows.value = scopePayload.items || [];
      paginationTotal.value = scopePayload.pagination?.total || rows.value.length;
      users.value = userPayload.items || [];
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

  .data-scope-page__number {
    width: 100%;
  }
</style>
