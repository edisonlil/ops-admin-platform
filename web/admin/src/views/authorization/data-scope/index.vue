<template>
  <div class="data-scope-page">
    <ListPageRuntime :schema="scopePage" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload">
      <template v-if="canManageResource" #header-actions>
        <n-button secondary @click="openResourceConfig">资源配置</n-button>
      </template>
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
              <n-select v-else v-model:value="form.subject_id" filterable :options="userSubjectOptions" />
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

    <n-drawer v-model:show="resourceDrawerVisible" width="720">
      <n-drawer-content title="数据资源配置">
        <n-form ref="resourceFormRef" :model="resourceForm" :rules="resourceRules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="数据资源" path="resource_key">
              <n-select v-model:value="resourceForm.resource_key" filterable :options="resourceOptions" @update:value="handleResourceChange" />
            </n-form-item-gi>
            <n-form-item-gi label="资源名称" path="name">
              <n-input v-model:value="resourceForm.name" />
            </n-form-item-gi>
            <n-form-item-gi label="归属模式" path="access_mode">
              <n-radio-group v-model:value="resourceForm.access_mode">
                <n-space>
                  <n-radio-button v-for="option in accessModeOptions" :key="String(option.value)" :value="String(option.value)">
                    {{ option.label }}
                  </n-radio-button>
                </n-space>
              </n-radio-group>
            </n-form-item-gi>
            <n-form-item-gi label="租户字段" path="tenant_column">
              <n-input v-model:value="resourceForm.tenant_column" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isOwnerColumnsMode" label="创建人字段" path="creator_column">
              <n-input v-model:value="resourceForm.creator_column" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isOwnerColumnsMode" label="负责人字段" path="owner_user_column">
              <n-input v-model:value="resourceForm.owner_user_column" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isOwnerColumnsMode" label="归属部门字段" path="owner_department_column">
              <n-input v-model:value="resourceForm.owner_department_column" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="关系表" path="relation_table">
              <n-input v-model:value="resourceForm.relation_table" placeholder="例如 document_members" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="资源主键字段" path="resource_id_column">
              <n-input v-model:value="resourceForm.resource_id_column" placeholder="默认 id" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="关系表资源字段" path="relation_resource_id_column">
              <n-input v-model:value="resourceForm.relation_resource_id_column" placeholder="例如 document_id" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="用户外键字段" path="relation_user_column">
              <n-input v-model:value="resourceForm.relation_user_column" placeholder="例如 user_id" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="部门外键字段" path="relation_department_column">
              <n-input v-model:value="resourceForm.relation_department_column" placeholder="例如 department_id" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="关系表租户字段" path="relation_tenant_column">
              <n-input v-model:value="resourceForm.relation_tenant_column" placeholder="默认 tenant_id" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="关系表软删字段" path="relation_deleted_column">
              <n-input v-model:value="resourceForm.relation_deleted_column" placeholder="默认 deleted，可留空" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="资源类型字段" path="relation_resource_key_column">
              <n-input v-model:value="resourceForm.relation_resource_key_column" placeholder="统一关系表可填写 resource_key" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="资源类型值" path="relation_resource_key_value">
              <n-input v-model:value="resourceForm.relation_resource_key_value" placeholder="留空时使用资源 key" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="主体类型字段" path="relation_subject_type_column">
              <n-input v-model:value="resourceForm.relation_subject_type_column" placeholder="例如 subject_type，可留空" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="用户主体类型值" path="relation_subject_type_user_value">
              <n-input v-model:value="resourceForm.relation_subject_type_user_value" placeholder="例如 user" />
            </n-form-item-gi>
            <n-form-item-gi v-if="isRelationTableMode" label="部门主体类型值" path="relation_subject_type_department_value">
              <n-input v-model:value="resourceForm.relation_subject_type_department_value" placeholder="例如 department" />
            </n-form-item-gi>
          </n-grid>
          <n-form-item label="资源描述" path="description">
            <n-input v-model:value="resourceForm.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
          </n-form-item>
          <n-form-item label="支持的权限范围" path="supported_scopes">
            <n-checkbox-group v-model:value="resourceForm.supported_scopes">
              <n-space>
                <n-checkbox v-for="option in scopeOptions" :key="String(option.value)" :value="String(option.value)">
                  {{ option.label }}
                </n-checkbox>
              </n-space>
            </n-checkbox-group>
          </n-form-item>
          <n-form-item label="必须配置数据权限" path="requires_data_scope">
            <n-switch v-model:value="resourceForm.requires_data_scope" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="resourceDrawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="resourceSaving" @click="submitResource">保存资源</n-button>
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
    saveAuthorizationResource,
    saveDataAccessPolicy,
    type DataAccessPolicyPayload,
    type DataResourcePayload,
  } from '@/api/business';

  interface ResourceRow extends Recordable {
    resource_key: string;
    name: string;
    description?: string;
    tenant_column?: string;
    creator_column?: string;
    owner_user_column?: string;
    owner_department_column?: string;
    resource_id_column?: string;
    access_mode?: AccessMode;
    relation_table?: string;
    relation_resource_id_column?: string;
    relation_user_column?: string;
    relation_department_column?: string;
    relation_tenant_column?: string;
    relation_deleted_column?: string;
    relation_resource_key_column?: string;
    relation_resource_key_value?: string;
    relation_subject_type_column?: string;
    relation_subject_type_user_value?: string;
    relation_subject_type_department_value?: string;
    supported_scopes?: string[];
    requires_data_scope?: boolean;
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
  type AccessMode = 'owner_columns' | 'relation_table';

  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const resourceSaving = ref(false);
  const drawerVisible = ref(false);
  const resourceDrawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const resourceFormRef = ref<FormInst | null>(null);
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
  const resourceForm = reactive<DataResourcePayload>({
    resource_key: '',
    name: '',
    description: '',
    access_mode: 'owner_columns',
    tenant_column: 'tenant_id',
    creator_column: 'creator_id',
    owner_user_column: 'owner_user_id',
    owner_department_column: 'owner_department_id',
    resource_id_column: 'id',
    relation_table: '',
    relation_resource_id_column: '',
    relation_user_column: 'user_id',
    relation_department_column: 'department_id',
    relation_tenant_column: 'tenant_id',
    relation_deleted_column: 'deleted',
    relation_resource_key_column: '',
    relation_resource_key_value: '',
    relation_subject_type_column: '',
    relation_subject_type_user_value: 'user',
    relation_subject_type_department_value: 'department',
    supported_scopes: [],
    requires_data_scope: false,
  });

  const subjectTypeOptions: SelectOption[] = [
    { label: '部门', value: 'department' },
    { label: '用户', value: 'user' },
  ];

  const scopeOptions: SelectOption[] = [
    { label: '本人数据', value: 'self' },
    { label: '本人及下属数据', value: 'self_and_subordinates' },
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

  const accessModeOptions: SelectOption[] = [
    { label: '单字段归属', value: 'owner_columns' },
    { label: '关系表归属', value: 'relation_table' },
  ];

  const rules: FormRules = {
    subject_type: [{ required: true, message: '请选择主体类型', trigger: ['blur', 'change'] }],
    subject_id: [
      {
        required: true,
        type: 'number',
        message: '请选择业务主体',
        trigger: ['blur', 'change'],
        validator() {
          return form.subject_type === 'user' ? Number(form.subject_id ?? -1) >= 0 : Number(form.subject_id || 0) > 0;
        },
      },
    ],
    resource_key: [{ required: true, message: '请选择数据资源', trigger: ['blur', 'change'] }],
    action: [{ required: true, message: '请选择动作', trigger: ['blur', 'change'] }],
    scope: [{ required: true, message: '请选择权限范围', trigger: ['blur', 'change'] }],
  };
  const resourceRules: FormRules = {
    resource_key: [{ required: true, message: '请选择数据资源', trigger: ['blur', 'change'] }],
    name: [{ required: true, message: '请输入资源名称', trigger: ['blur', 'input'] }],
    access_mode: [{ required: true, message: '请选择归属模式', trigger: ['blur', 'change'] }],
    tenant_column: [{ required: true, message: '请输入租户字段', trigger: ['blur', 'input'] }],
    resource_id_column: [
      {
        required: true,
        message: '关系表归属模式必须填写资源主键字段',
        trigger: ['blur', 'input'],
        validator() {
          return isOwnerColumnsMode.value || Boolean(String(resourceForm.resource_id_column || '').trim());
        },
      },
    ],
    owner_user_column: [
      {
        required: true,
        message: '请输入负责人字段',
        trigger: ['blur', 'input'],
        validator() {
          return isRelationTableMode.value || Boolean(String(resourceForm.owner_user_column || '').trim());
        },
      },
    ],
    owner_department_column: [
      {
        required: true,
        message: '请输入归属部门字段',
        trigger: ['blur', 'input'],
        validator() {
          return isRelationTableMode.value || Boolean(String(resourceForm.owner_department_column || '').trim());
        },
      },
    ],
    relation_table: [
      {
        required: true,
        message: '关系表归属模式必须填写关系表',
        trigger: ['blur', 'input'],
        validator() {
          return isOwnerColumnsMode.value || Boolean(String(resourceForm.relation_table || '').trim());
        },
      },
    ],
    relation_resource_id_column: [
      {
        required: true,
        message: '关系表归属模式必须填写关系表资源字段',
        trigger: ['blur', 'input'],
        validator() {
          return isOwnerColumnsMode.value || Boolean(String(resourceForm.relation_resource_id_column || '').trim());
        },
      },
    ],
    relation_user_column: [
      {
        required: true,
        message: '本人或本人及下属范围必须填写用户外键字段',
        trigger: ['blur', 'input'],
        validator() {
          return (
            isOwnerColumnsMode.value ||
            !hasUserRelationScope(resourceForm.supported_scopes || []) ||
            Boolean(String(resourceForm.relation_user_column || '').trim())
          );
        },
      },
    ],
    relation_department_column: [
      {
        required: true,
        message: '部门范围必须填写部门外键字段',
        trigger: ['blur', 'input'],
        validator() {
          return (
            isOwnerColumnsMode.value ||
            !hasDepartmentRelationScope(resourceForm.supported_scopes || []) ||
            Boolean(String(resourceForm.relation_department_column || '').trim())
          );
        },
      },
    ],
    supported_scopes: [{ required: true, type: 'array', message: '请选择支持的权限范围', trigger: ['blur', 'change'] }],
  };

  const canManageResource = computed(() => hasPermission(['authorization:data-resource:manage']));
  const isOwnerColumnsMode = computed(() => resourceForm.access_mode !== 'relation_table');
  const isRelationTableMode = computed(() => resourceForm.access_mode === 'relation_table');
  const resourceOptions = computed<SelectOption[]>(() =>
    resources.value.map((resource) => ({ label: `${resource.name || resource.resource_key} (${resource.resource_key})`, value: resource.resource_key }))
  );
  const departmentOptions = computed<SelectOption[]>(() =>
    departments.value.map((department) => ({ label: `${departmentPath(department)} (${department.code})`, value: department.id }))
  );
  const departmentTreeOptions = computed<TreeSelectOption[]>(() => buildDepartmentTreeOptions());
  const userOptions = computed<SelectOption[]>(() => users.value.map((user) => ({ label: `${user.username} (#${user.id})`, value: user.id })));
  const userSubjectOptions = computed<SelectOption[]>(() => [{ label: '所有用户', value: 0 }, ...userOptions.value]);
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

  function openResourceConfig() {
    const resourceKey = resourceFilter.value || form.resource_key || resources.value[0]?.resource_key || '';
    applyResourceForm(resources.value.find((item) => item.resource_key === resourceKey) || resources.value[0]);
    resourceDrawerVisible.value = true;
    resourceFormRef.value?.restoreValidation();
  }

  function handleResourceChange(value: string) {
    applyResourceForm(resources.value.find((item) => item.resource_key === value));
  }

  function applyResourceForm(resource?: ResourceRow) {
    Object.assign(resourceForm, {
      resource_key: resource?.resource_key || '',
      name: resource?.name || '',
      description: resource?.description || '',
      access_mode: normalizeAccessMode(resource?.access_mode),
      tenant_column: resource?.tenant_column || 'tenant_id',
      creator_column: resource?.creator_column || 'creator_id',
      owner_user_column: resource?.owner_user_column || 'owner_user_id',
      owner_department_column: resource?.owner_department_column || 'owner_department_id',
      resource_id_column: resource?.resource_id_column || 'id',
      relation_table: resource?.relation_table || '',
      relation_resource_id_column: resource?.relation_resource_id_column || '',
      relation_user_column: resource?.relation_user_column || 'user_id',
      relation_department_column: resource?.relation_department_column || 'department_id',
      relation_tenant_column: resource?.relation_tenant_column || 'tenant_id',
      relation_deleted_column: resource?.relation_deleted_column || 'deleted',
      relation_resource_key_column: resource?.relation_resource_key_column || '',
      relation_resource_key_value: resource?.relation_resource_key_value || '',
      relation_subject_type_column: resource?.relation_subject_type_column || '',
      relation_subject_type_user_value: resource?.relation_subject_type_user_value || 'user',
      relation_subject_type_department_value: resource?.relation_subject_type_department_value || 'department',
      supported_scopes: [...(resource?.supported_scopes || [])],
      requires_data_scope: Boolean(resource?.requires_data_scope),
    });
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

  async function submitResource() {
    try {
      await resourceFormRef.value?.validate();
    } catch {
      return;
    }
    resourceSaving.value = true;
    try {
      await saveAuthorizationResource(resourceForm.resource_key, {
        ...resourcePayload(),
      });
      message.success('数据资源已保存');
      resourceDrawerVisible.value = false;
      await reload();
    } finally {
      resourceSaving.value = false;
    }
  }

  async function remove(row: PolicyRow) {
    await deleteDataAccessPolicy(row.id);
    message.success('数据权限已删除');
    await reload();
  }

  function defaultSubjectId(subjectType: SubjectType) {
    return subjectType === 'user' ? 0 : departments.value[0]?.id;
  }

  function resourcePayload(): DataResourcePayload {
    const supportedScopes = [...(resourceForm.supported_scopes || [])];
    const payload: DataResourcePayload = {
      resource_key: String(resourceForm.resource_key || '').trim(),
      name: String(resourceForm.name || '').trim(),
      description: String(resourceForm.description || '').trim(),
      access_mode: normalizeAccessMode(resourceForm.access_mode),
      tenant_column: String(resourceForm.tenant_column || 'tenant_id').trim(),
      supported_scopes: supportedScopes,
      requires_data_scope: Boolean(resourceForm.requires_data_scope),
    };
    if (payload.access_mode === 'relation_table') {
      payload.resource_id_column = String(resourceForm.resource_id_column || 'id').trim();
      payload.relation_table = String(resourceForm.relation_table || '').trim();
      payload.relation_resource_id_column = String(resourceForm.relation_resource_id_column || '').trim();
      payload.relation_user_column = String(resourceForm.relation_user_column || '').trim();
      payload.relation_department_column = String(resourceForm.relation_department_column || '').trim();
      payload.relation_tenant_column = String(resourceForm.relation_tenant_column || payload.tenant_column || 'tenant_id').trim();
      payload.relation_deleted_column = String(resourceForm.relation_deleted_column || '').trim();
      payload.relation_resource_key_column = String(resourceForm.relation_resource_key_column || '').trim();
      payload.relation_resource_key_value = String(resourceForm.relation_resource_key_value || '').trim();
      payload.relation_subject_type_column = String(resourceForm.relation_subject_type_column || '').trim();
      payload.relation_subject_type_user_value = String(resourceForm.relation_subject_type_user_value || '').trim();
      payload.relation_subject_type_department_value = String(resourceForm.relation_subject_type_department_value || '').trim();
      return payload;
    }
    payload.creator_column = String(resourceForm.creator_column || 'creator_id').trim();
    payload.owner_user_column = String(resourceForm.owner_user_column || 'owner_user_id').trim();
    payload.owner_department_column = String(resourceForm.owner_department_column || 'owner_department_id').trim();
    return payload;
  }

  function normalizeAccessMode(value?: string): AccessMode {
    return value === 'relation_table' ? 'relation_table' : 'owner_columns';
  }

  function hasUserRelationScope(scopes: string[]) {
    return scopes.some((scope) => scope === 'self' || scope === 'self_and_subordinates');
  }

  function hasDepartmentRelationScope(scopes: string[]) {
    return scopes.some((scope) => scope === 'department' || scope === 'department_and_children' || scope === 'custom_departments');
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
      if (Number(row.subject_id) === 0) return '所有用户';
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
