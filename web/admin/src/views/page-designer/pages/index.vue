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
  </div>
</template>

<script lang="ts" setup>
  import { h, reactive, ref } from 'vue';
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
    getPageDesignerPages,
    mountPageDesignerMenu,
    publishPageDesignerPage,
    type PageDefinition,
    updatePageDesignerPage,
  } from '@/api/pageDesigner';

  const router = useRouter();
  const message = useMessage();
  const { hasPermission } = usePermission();
  const loading = ref(false);
  const saving = ref(false);
  const drawerVisible = ref(false);
  const formRef = ref<FormInst | null>(null);
  const rows = ref<PageDefinition[]>([]);
  const paginationTotal = ref(0);
  const keyword = ref('');
  const statusFilter = ref<string | null>(null);

  const form = reactive<Partial<PageDefinition>>({
    page_key: '',
    name: '',
    description: '',
    page_type: 'dashboard',
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
            { label: '挂载', show: canManage() && row.status === 'published' && !row.menu_mounted, onClick: () => mount(row) },
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
    description: '创建、设计、发布并挂载租户自定义页面',
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

  async function mount(row: PageDefinition) {
    await mountPageDesignerMenu(row.id);
    message.success('页面已挂载到菜单');
    await reload();
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
</style>
