<template>
  <div class="page-designer-list">
    <ListPageRuntime :schema="pageSchema" :rows="rows" :loading="loading" :pagination-total="paginationTotal" @refresh="reload">
      <template #filters>
        <n-input v-model:value="keyword" clearable placeholder="搜索页面名称或标识" class="page-designer-list__keyword" @keyup.enter="reload" />
        <n-select v-model:value="statusFilter" clearable placeholder="状态" :options="statusOptions" class="page-designer-list__status" @update:value="reload()" />
      </template>
    </ListPageRuntime>

    <n-drawer v-model:show="drawerVisible" width="560">
      <n-drawer-content :title="form.id ? '编辑页面' : '新建页面'">
        <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
          <n-form-item label="页面名称" path="name">
            <n-input v-model:value="form.name" placeholder="例如：经营驾驶舱" />
          </n-form-item>
          <n-form-item label="页面标识" path="page_key">
            <n-input v-model:value="form.page_key" :disabled="Boolean(form.id)" placeholder="例如：business-dashboard" />
          </n-form-item>
          <n-form-item label="页面类型">
            <n-select v-model:value="form.page_type" :options="pageTypeOptions" disabled />
          </n-form-item>
          <n-form-item label="说明">
            <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存页面</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-modal v-model:show="mountVisible" preset="card" title="挂载到租户菜单" class="page-designer-mount-modal">
      <n-alert type="info" :bordered="false" class="page-designer-mount-modal__hint">
        页面由平台统一设计，挂载后会生成租户菜单项。租户角色绑定该菜单后，对应成员才能看到入口。
      </n-alert>
      <n-form :model="mountForm" label-placement="top">
        <n-form-item label="页面">
          <n-input :value="mountForm.pageName" disabled />
        </n-form-item>
        <n-form-item label="菜单名称">
          <n-input v-model:value="mountForm.label" placeholder="请输入租户菜单名称" />
        </n-form-item>
        <n-form-item label="挂载目录">
          <n-select
            v-model:value="mountForm.parent_key"
            :options="tenantDirectoryOptions"
            :loading="menuLoading"
            clearable
            filterable
            placeholder="选择租户菜单目录"
          />
        </n-form-item>
        <n-form-item label="排序">
          <n-input-number v-model:value="mountForm.sort_order" :min="0" :max="99999" class="page-designer-mount-modal__number" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="mountVisible = false">取消</n-button>
          <n-button type="primary" :loading="mounting" @click="confirmMount">确认挂载</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, reactive, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import type { DataTableColumns, FormInst, FormRules, SelectOption } from 'naive-ui';
  import AppStatusTag from '@/components/Application/AppStatusTag.vue';
  import AppTableActions from '@/components/Application/AppTableActions.vue';
  import { defineListPage, ListPageRuntime, runtimeListParams, type ListRuntimeState } from '@/page-runtime';
  import { usePermission } from '@/hooks/web/usePermission';
  import { formatToDateTime } from '@/utils/dateUtil';
  import {
    createPageDesignerPage,
    deletePageDesignerPage,
    getPageDesignerMountDirectories,
    getPageDesignerPages,
    mountPageDesignerMenu,
    publishPageDesignerPage,
    type PageMenuDirectory,
    type PageDefinition,
    updatePageDesignerPage,
  } from '@/api/pageDesigner';

  const router = useRouter();
  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const mounting = ref(false);
  const menuLoading = ref(false);
  const drawerVisible = ref(false);
  const mountVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<PageDefinition[]>([]);
  const tenantMenus = ref<PageMenuDirectory[]>([]);
  const paginationTotal = ref(0);
  const keyword = ref('');
  const statusFilter = ref<string | null>(null);

  const form = reactive<Partial<PageDefinition>>({
    page_key: '',
    name: '',
    description: '',
    page_type: 'dashboard',
  });

  const mountForm = reactive({
    pageId: 0,
    pageName: '',
    label: '',
    parent_key: '',
    sort_order: 869,
  });

  const statusOptions: SelectOption[] = [
    { label: '草稿', value: 'draft' },
    { label: '已发布', value: 'published' },
    { label: '已停用', value: 'disabled' },
  ];

  const pageTypeOptions: SelectOption[] = [{ label: '仪表盘', value: 'dashboard' }];

  const rules: FormRules = {
    name: [{ required: true, message: '请输入页面名称', trigger: ['blur', 'input'] }],
    page_key: [
      { required: true, message: '请输入页面标识', trigger: ['blur', 'input'] },
      {
        pattern: /^[A-Za-z0-9_-]+$/,
        message: '页面标识只能包含字母、数字、下划线和短横线',
        trigger: ['blur', 'input'],
      },
    ],
  };

  const columns: DataTableColumns<PageDefinition> = [
    { title: '页面名称', key: 'name', minWidth: 180 },
    { title: '页面标识', key: 'page_key', minWidth: 180 },
    { title: '类型', key: 'page_type', width: 110, render: () => '仪表盘' },
    {
      title: '状态',
      key: 'status',
      width: 110,
      render(row) {
        return h(AppStatusTag, statusMeta(row.status));
      },
    },
    {
      title: '菜单',
      key: 'menu_mounted',
      width: 110,
      render(row) {
        return h(AppStatusTag, {
          tone: row.menu_mounted ? 'success' : 'neutral',
          label: row.menu_mounted ? '已挂载' : '未挂载',
        });
      },
    },
    { title: '更新时间', key: 'update_time', width: 180, render: (row) => formatToDateTime(row.update_time || '') },
    {
      title: '操作',
      key: 'actions',
      width: 300,
      fixed: 'right',
      render(row) {
        return h(AppTableActions, {
          actions: [
            { label: '设计', show: canManage(), onClick: () => openDesigner(row) },
            { label: '编辑', show: canManage(), onClick: () => openEdit(row) },
            { label: '发布', show: canManage() && row.status !== 'published', onClick: () => publish(row) },
            { label: row.menu_mounted ? '调整挂载' : '挂载', show: canManage() && row.status === 'published', onClick: () => openMount(row) },
            {
              label: '删除',
              tone: 'danger',
              show: canManage(),
              confirm: true,
              confirmTitle: '删除页面',
              confirmContent: `确定删除「${row.name}」吗？`,
              onConfirm: () => remove(row),
            },
          ],
        });
      },
    },
  ];

  const pageSchema = defineListPage<PageDefinition>({
    id: 'page-designer.pages',
    title: '页面设计',
    description: '平台设计仪表盘页面，发布后挂载为租户菜单',
    variant: 'dense-data',
    density: 'compact',
    view: {
      type: 'table',
      columns,
      rowKey: (row) => row.id,
      scrollX: 1180,
      tableProps: { size: 'small' },
    },
    toolbar: {
      primaryAction: canManage() ? { key: 'create', label: '新建页面', type: 'primary', onClick: () => openCreate() } : undefined,
      rightTools: ['refresh'],
    },
    pagination: { pageSize: 20 },
  });

  const tenantDirectoryOptions = computed<SelectOption[]>(() => {
    const directories = tenantMenus.value.filter((item) => item.menu_type === 'directory' && item.menu_scope === 'tenant');
    const childrenByParent = new Map<string, PageMenuDirectory[]>();
    directories.forEach((item) => {
      const parentKey = String(item.parent_key || '');
      const children = childrenByParent.get(parentKey) || [];
      children.push(item);
      childrenByParent.set(parentKey, children);
    });
    childrenByParent.forEach((items) => items.sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0)));
    const options: SelectOption[] = [{ label: '作为租户根菜单', value: '' }];
    const visited = new Set<string>();

    function append(parentKey: string, level: number) {
      for (const item of childrenByParent.get(parentKey) || []) {
        if (visited.has(item.key)) continue;
        visited.add(item.key);
        options.push({
          label: `${'　'.repeat(level)}${item.label}`,
          value: item.key,
        });
        append(item.key, level + 1);
      }
    }

    append('', 0);
    for (const item of directories) {
      if (!visited.has(item.key)) {
        options.push({ label: item.label, value: item.key });
      }
    }
    return options;
  });

  function canManage() {
    return hasPermission(['page_designer:page:manage']);
  }

  function statusMeta(status: string) {
    if (status === 'published') return { tone: 'success', label: '已发布' };
    if (status === 'disabled') return { tone: 'neutral', label: '已停用' };
    return { tone: 'warning', label: '草稿' };
  }

  function resetForm() {
    Object.assign(form, {
      id: undefined,
      page_key: '',
      name: '',
      description: '',
      page_type: 'dashboard',
    });
    formRef.value?.restoreValidation();
  }

  function openCreate() {
    resetForm();
    drawerVisible.value = true;
  }

  function openEdit(row: PageDefinition) {
    Object.assign(form, row);
    drawerVisible.value = true;
  }

  function openDesigner(row: PageDefinition) {
    router.push({ path: `/page-designer/pages/${row.id}` });
  }

  async function submit() {
    try {
      await formRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      if (form.id) {
        await updatePageDesignerPage(Number(form.id), form as PageDefinition);
      } else {
        await createPageDesignerPage(form as PageDefinition);
      }
      message.success('页面已保存');
      drawerVisible.value = false;
      await reload();
    } finally {
      saving.value = false;
    }
  }

  async function publish(row: PageDefinition) {
    await publishPageDesignerPage(row.id);
    message.success('页面已发布');
    await reload();
  }

  async function openMount(row: PageDefinition) {
    Object.assign(mountForm, {
      pageId: row.id,
      pageName: row.name,
      label: row.name,
      parent_key: '',
      sort_order: 869,
    });
    mountVisible.value = true;
    await loadTenantMenus();
  }

  async function loadTenantMenus() {
    menuLoading.value = true;
    try {
      const payload = await getPageDesignerMountDirectories();
      tenantMenus.value = payload.items || [];
    } finally {
      menuLoading.value = false;
    }
  }

  async function confirmMount() {
    if (!mountForm.pageId) return;
    mounting.value = true;
    try {
      await mountPageDesignerMenu(mountForm.pageId, {
        label: mountForm.label,
        menu_scope: 'tenant',
        parent_key: mountForm.parent_key,
        sort_order: mountForm.sort_order,
      });
      message.success('页面已挂载为租户菜单，请在租户角色中绑定该菜单');
      mountVisible.value = false;
      await reload();
    } finally {
      mounting.value = false;
    }
  }

  async function remove(row: PageDefinition) {
    await deletePageDesignerPage(row.id);
    message.success('页面已删除');
    await reload();
  }

  async function reload(state?: ListRuntimeState) {
    loading.value = true;
    try {
      const payload = await getPageDesignerPages({
        ...runtimeListParams(state),
        keyword: keyword.value,
        status: statusFilter.value,
      });
      rows.value = payload.items || [];
      paginationTotal.value = payload.pagination?.total || rows.value.length;
    } finally {
      loading.value = false;
    }
  }

  reload();
</script>

<style lang="less" scoped>
  .page-designer-list {
    min-width: 0;
  }

  .page-designer-list__keyword {
    width: min(320px, 100%);
  }

  .page-designer-list__status {
    width: 160px;
  }

  .page-designer-mount-modal {
    width: min(560px, calc(100vw - 32px));
  }

  .page-designer-mount-modal__hint {
    margin-bottom: 16px;
  }

  .page-designer-mount-modal__number {
    width: 100%;
  }
</style>
