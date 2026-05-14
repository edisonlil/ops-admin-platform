<template>
  <div class="department-page">
    <ListPageRuntime :schema="departmentPage" :rows="treeRows" :loading="loading" @refresh="reload">
      <template #filters>
        <n-select
          v-if="isPlatformAdmin"
          v-model:value="selectedTenantId"
          filterable
          placeholder="选择租户"
          :loading="tenantLoading"
          :options="tenantOptions"
          class="department-page__tenant"
          @update:value="reload"
        />
        <n-input v-model:value="keyword" clearable placeholder="搜索部门编码、名称或所在地" class="department-page__filter" />
        <n-select v-model:value="statusFilter" clearable placeholder="状态" :options="statusOptions" class="department-page__status" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="560">
      <n-drawer-content :title="form.id ? '编辑部门' : '新建部门'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-grid :cols="2" :x-gap="16" responsive="screen">
            <n-form-item-gi label="上级部门">
              <n-tree-select
                v-model:value="form.parent_id"
                clearable
                filterable
                block-line
                default-expand-all
                :options="parentTreeOptions"
                placeholder="不选择则为一级部门"
              />
            </n-form-item-gi>
            <n-form-item-gi label="编码" path="code">
              <n-input v-model:value="form.code" placeholder="sales-east" />
            </n-form-item-gi>
            <n-form-item-gi label="名称" path="name">
              <n-input v-model:value="form.name" placeholder="华东销售部" />
            </n-form-item-gi>
            <n-form-item-gi label="状态" path="status">
              <n-select v-model:value="form.status" :options="statusOptions" />
            </n-form-item-gi>
            <n-form-item-gi label="Base 地">
              <n-input v-model:value="form.base_location" placeholder="上海" />
            </n-form-item-gi>
            <n-form-item-gi label="区域">
              <n-input v-model:value="form.region" placeholder="华东" />
            </n-form-item-gi>
            <n-form-item-gi label="排序">
              <n-input-number v-model:value="form.sort_order" class="department-page__number" />
            </n-form-item-gi>
          </n-grid>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存部门</n-button>
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
  import { defineListPage, ListPageRuntime } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { useUserStore } from '@/store/modules/user';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { createDepartment, deleteDepartment, getDepartments, getTenants, updateDepartment, type DepartmentPayload } from '@/api/business';

  interface DepartmentRow extends DepartmentPayload {
    id: number;
    tenant_id: number;
    create_time?: string;
    update_time?: string;
    children?: DepartmentRow[];
  }

  const message = useMessage();
  const { hasPermission } = usePermission();
  const userStore = useUserStore();
  const loading = ref(false);
  const tenantLoading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<DepartmentRow[]>([]);
  const selectedTenantId = ref<number | null>(null);
  const tenantOptions = ref<SelectOption[]>([]);
  const keyword = ref('');
  const statusFilter = ref<string | null>(null);
  const form = reactive<DepartmentPayload>({
    parent_id: null,
    code: '',
    name: '',
    base_location: '',
    region: '',
    status: 'active',
    sort_order: 0,
  });

  const statusOptions: SelectOption[] = [
    { label: '启用', value: 'active' },
    { label: '停用', value: 'disabled' },
  ];
  const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);

  const rules: FormRules = {
    code: [{ required: true, message: '请输入部门编码', trigger: ['blur', 'input'] }],
    name: [{ required: true, message: '请输入部门名称', trigger: ['blur', 'input'] }],
  };

  const parentTreeOptions = computed<TreeSelectOption[]>(() => buildParentTreeOptions());

  const treeRows = computed(() => {
    const text = keyword.value.trim().toLowerCase();
    const childrenByParent = new Map<number | null, DepartmentRow[]>();
    for (const row of rows.value) {
      const parentId = row.parent_id ? Number(row.parent_id) : null;
      const item = { ...row, children: [] };
      const siblings = childrenByParent.get(parentId) || [];
      siblings.push(item);
      childrenByParent.set(parentId, siblings);
    }
    const sortRows = (items: DepartmentRow[]) =>
      items.sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0) || Number(a.id) - Number(b.id));
    const build = (parentId: number | null): DepartmentRow[] =>
      sortRows(childrenByParent.get(parentId) || []).map((row) => {
        const children = build(row.id);
        return {
          ...row,
          children: children.length ? children : undefined,
        };
      });
    const rootRows = build(null);
    return filterTree(rootRows, text, statusFilter.value);
  });

  const columns: DataTableColumns<DepartmentRow> = [
    { title: '部门', key: 'name', minWidth: 220 },
    { title: '编码', key: 'code', width: 160 },
    { title: 'Base 地', key: 'base_location', width: 140 },
    { title: '区域', key: 'region', width: 120 },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render(row) {
        return h(AppStatusTag, {
          tone: row.status === 'active' ? 'success' : 'neutral',
          label: row.status === 'active' ? '启用' : '停用',
        });
      },
    },
    { title: '排序', key: 'sort_order', width: 90 },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '编辑', show: hasPermission(['organization:departments:manage']), onClick: () => openEdit(row) },
            {
              label: '删除',
              tone: 'danger',
              show: hasPermission(['organization:departments:manage']),
              confirm: true,
              confirmTitle: '删除部门',
              confirmContent: `确认删除部门 ${row.name}？`,
              onConfirm: () => remove(row),
            },
          ],
        });
      },
    },
  ];

  const departmentPage = computed(() =>
    defineListPage<DepartmentRow>({
      id: 'organization.departments',
      title: '部门管理',
      description: '维护租户组织部门，数据权限会基于用户所属部门计算本人、本部门、下级部门和自定义部门范围。',
      variant: 'dense-data',
      density: 'compact',
      view: {
        type: 'table',
        columns,
        rowKey: (row) => Number(row.id),
        scrollX: 1120,
        tableProps: { size: 'small', defaultExpandAll: true },
      },
      toolbar: {
        primaryAction: hasPermission(['organization:departments:manage'])
          ? { key: 'create', label: '新建部门', type: 'primary', onClick: () => openCreate() }
          : undefined,
        rightTools: ['refresh'],
      },
      pagination: { pageSize: 20 },
    })
  );

  function resetForm() {
    Object.assign(form, {
      id: undefined,
      parent_id: null,
      code: '',
      name: '',
      base_location: '',
      region: '',
      status: 'active',
      sort_order: 0,
    });
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: DepartmentRow) {
    Object.assign(form, row);
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
      const payload = { ...form, tenant_id: selectedTenantForRequest() };
      if (form.id) await updateDepartment(form.id, payload);
      else await createDepartment(payload);
      message.success('部门已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function remove(row: DepartmentRow) {
    await deleteDepartment(row.id, { tenant_id: selectedTenantForRequest() });
    message.success('部门已删除');
    await reload();
  }

  function departmentPath(row: DepartmentRow) {
    const names = [row.name];
    let parentId = Number(row.parent_id || 0);
    const seen = new Set<number>([row.id]);
    while (parentId && !seen.has(parentId)) {
      seen.add(parentId);
      const parent = rows.value.find((item) => item.id === parentId);
      if (!parent) break;
      names.unshift(parent.name);
      parentId = Number(parent.parent_id || 0);
    }
    return names.join(' / ');
  }

  function filterTree(items: DepartmentRow[], text: string, status: string | null): DepartmentRow[] {
    return items
      .map((row) => {
        const children = filterTree(row.children || [], text, status);
        const matchedText =
          !text ||
          row.code.toLowerCase().includes(text) ||
          row.name.toLowerCase().includes(text) ||
          String(row.base_location || '').toLowerCase().includes(text) ||
          String(row.region || '').toLowerCase().includes(text);
        const matchedStatus = !status || row.status === status;
        if ((matchedText && matchedStatus) || children.length) {
          return { ...row, children: children.length ? children : undefined };
        }
        return null;
      })
      .filter(Boolean) as DepartmentRow[];
  }

  function isDescendant(candidateId: number, targetId: number) {
    let parentId = rows.value.find((item) => item.id === candidateId)?.parent_id;
    while (parentId) {
      if (Number(parentId) === targetId) return true;
      parentId = rows.value.find((item) => item.id === Number(parentId))?.parent_id;
    }
    return false;
  }

  function buildParentTreeOptions() {
    const childrenByParent = new Map<number | null, DepartmentRow[]>();
    for (const row of rows.value) {
      if (row.id === form.id) continue;
      if (form.id && isDescendant(row.id, form.id)) continue;
      const parentId = row.parent_id ? Number(row.parent_id) : null;
      const siblings = childrenByParent.get(parentId) || [];
      siblings.push(row);
      childrenByParent.set(parentId, siblings);
    }
    const sortRows = (items: DepartmentRow[]) =>
      items.sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0) || Number(a.id) - Number(b.id));
    const build = (parentId: number | null): TreeSelectOption[] =>
      sortRows(childrenByParent.get(parentId) || []).map((row) => {
        const children = build(row.id);
        return {
          label: row.name,
          key: row.id,
          value: row.id,
          children: children.length ? children : undefined,
        };
      });
    return build(null);
  }

  async function reload() {
    loading.value = true;
    try {
      await ensureTenantOptions();
      const tenantId = selectedTenantForRequest();
      if (isPlatformAdmin.value && !tenantId) {
        rows.value = [];
        return;
      }
      const payload = await getDepartments({ include_disabled: true, tenant_id: tenantId });
      rows.value = payload.items || [];
    } finally {
      loading.value = false;
    }
  }

  async function ensureTenantOptions() {
    if (!isPlatformAdmin.value || tenantOptions.value.length) return;
    tenantLoading.value = true;
    try {
      const payload = await getTenants();
      tenantOptions.value = (payload.items || []).map((tenant) => ({
        label: `${tenant.name || tenant.tenant_key} (${tenant.tenant_key})`,
        value: Number(tenant.id),
      }));
      const currentTenant = userStore.info?.current_tenant as { id?: number } | undefined;
      selectedTenantId.value = Number(currentTenant?.id || tenantOptions.value[0]?.value || 0) || null;
    } finally {
      tenantLoading.value = false;
    }
  }

  function selectedTenantForRequest() {
    return isPlatformAdmin.value ? selectedTenantId.value : undefined;
  }

  reload();
</script>

<style lang="less" scoped>
  .department-page {
    min-width: 0;
  }

  .department-page__filter {
    width: min(340px, 100%);
  }

  .department-page__tenant {
    width: min(280px, 100%);
  }

  .department-page__status {
    width: 150px;
  }

  .department-page__number {
    width: 100%;
  }
</style>
