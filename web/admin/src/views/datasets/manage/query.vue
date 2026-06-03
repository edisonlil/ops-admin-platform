<template>
  <div class="dataset-query-page">
    <header class="dataset-query-page__header">
      <div class="dataset-query-page__titlebar">
        <n-button quaternary size="small" @click="goBack">
          <template #icon>
            <n-icon><ArrowLeftOutlined /></n-icon>
          </template>
          平台数据集
        </n-button>
        <div class="dataset-query-page__title">
          <strong>{{ dataset?.name || '数据源查询' }}</strong>
        </div>
        <n-tag size="small" :bordered="false">{{ sourceSchemaBackend || '数据源' }}</n-tag>
      </div>
      <n-space :size="8" align="center" class="dataset-query-page__actions">
        <n-button :loading="datasetLoading" @click="loadDataset">刷新数据集</n-button>
        <n-button :loading="schemaLoading" @click="loadSourceSchema">刷新表结构</n-button>
        <n-button type="primary" secondary :loading="savingQuery" @click="saveQueryConfig">
          <template #icon>
            <n-icon><SaveOutlined /></n-icon>
          </template>
          保存 SQL
        </n-button>
        <n-button type="primary" secondary :loading="queryLoading" @click="runQuery">
          <template #icon>
            <n-icon><PlayCircleOutlined /></n-icon>
          </template>
          运行 SQL
        </n-button>
      </n-space>
    </header>

    <main class="dataset-query-workbench">
      <aside class="dataset-query-workbench__schema">
        <div class="dataset-query-workbench__schema-head">
          <div>
            <strong>表结构</strong>
            <span>{{ sourceTables.length }} 张表</span>
          </div>
          <n-button text size="tiny" :loading="schemaLoading" @click="loadSourceSchema">刷新</n-button>
        </div>
        <div class="dataset-query-workbench__schema-search">
          <n-input v-model:value="schemaKeyword" clearable size="small" placeholder="搜索表或字段" />
        </div>
        <n-spin :show="schemaLoading" class="dataset-query-workbench__schema-body">
          <n-empty v-if="!filteredSourceTables.length" size="small" :description="schemaEmptyText" />
          <div v-else class="dataset-query-workbench__tables">
            <section v-for="table in filteredSourceTables" :key="tableKey(table)" class="dataset-query-workbench__table">
              <button type="button" class="dataset-query-workbench__table-name" @click="toggleSourceTable(table)">
                <span>{{ expandedTableKeys.includes(tableKey(table)) ? '−' : '+' }}</span>
                <strong :title="qualifiedTableName(table)">{{ displayTableName(table) }}</strong>
                <small>{{ table.columns.length }}</small>
              </button>
              <div v-if="expandedTableKeys.includes(tableKey(table))" class="dataset-query-workbench__columns">
                <button
                  v-for="column in table.columns"
                  :key="column.name"
                  type="button"
                  class="dataset-query-workbench__column"
                  @click="appendColumnToSql(column.name)"
                >
                  <span :title="column.name">{{ column.name }}</span>
                  <small>{{ column.data_type || '-' }}</small>
                </button>
              </div>
            </section>
          </div>
        </n-spin>
      </aside>

      <section class="dataset-query-workbench__main">
        <div class="dataset-query-workbench__editor-card">
          <div class="dataset-query-workbench__toolbar">
            <n-space :size="6">
              <n-button quaternary size="small" type="primary" :loading="queryLoading" @click="runQuery">
                <template #icon>
                  <n-icon><PlayCircleOutlined /></n-icon>
                </template>
                运行
              </n-button>
              <n-button quaternary size="small" :loading="savingQuery" @click="saveQueryConfig">
                <template #icon>
                  <n-icon><SaveOutlined /></n-icon>
                </template>
                保存
              </n-button>
              <n-button quaternary size="small" @click="formatQuerySql">格式化</n-button>
              <n-button quaternary size="small" @click="resetQueryFromDataset">还原</n-button>
            </n-space>
            <span>{{ querySqlLineCount }} 行</span>
          </div>
          <CodePreview v-model:value="querySql" language="sql" :read-only="false" :height="queryEditorHeight" :auto-height="false" />
        </div>

        <div class="dataset-query-workbench__access-card">
          <div class="dataset-query-workbench__access-head">
            <div>
              <strong>数据权限</strong>
              <span>选择要追加租户和数据范围条件的主业务表。</span>
            </div>
            <n-tag size="small" :type="hasMultiTableQuery ? 'warning' : 'default'" :bordered="false">
              {{ hasMultiTableQuery ? '多表 SQL' : '自动识别' }}
            </n-tag>
          </div>
          <div class="dataset-query-workbench__access-row">
            <n-select
              v-model:value="selectedDataAccessSource"
              clearable
              filterable
              size="small"
              :options="dataAccessSourceOptions"
              :disabled="!dataAccessSourceOptions.length"
              placeholder="请选择主业务表别名，例如 wo"
            />
            <n-button
              v-if="suggestedDataAccessOption"
              secondary
              size="small"
              type="primary"
              @click="useSuggestedDataAccessSource"
            >
              使用建议：{{ suggestedDataAccessOption.label }}
            </n-button>
          </div>
          <n-alert v-if="hasMultiTableQuery && !selectedDataAccessSource" type="warning" :bordered="false">
            {{ dataAccessWarningText }}
          </n-alert>
          <p v-else class="dataset-query-workbench__access-tip">{{ dataAccessSourceHelpText }}</p>
        </div>

        <VariableSchemaEditor
          v-if="hasQueryVariables"
          v-model="queryVariablesSchema"
          v-model:values="queryVariables"
          title="查询变量"
          description="运行 SQL 时传入的变量，数据权限由系统按当前租户和用户自动过滤。"
          :template-text="querySql"
          show-values
        />

        <div class="dataset-query-workbench__result">
          <div class="dataset-query-workbench__result-head">
            <n-tabs v-model:value="queryResultTab" type="line" size="small" animated>
              <n-tab-pane name="result" tab="结果" />
              <n-tab-pane name="info" tab="信息" />
            </n-tabs>
            <span v-if="queryError" class="dataset-query-workbench__result-status">执行失败</span>
            <span v-else-if="queryExecuted" class="dataset-query-workbench__result-status">返回 {{ queryRows.length }} 行 / 共 {{ queryTotal }} 行</span>
          </div>
          <div v-if="queryResultTab === 'result'" class="dataset-query-workbench__result-body">
            <n-result v-if="queryError" status="error" title="执行失败" :description="queryError" />
            <n-empty v-else-if="queryExecuted && !queryRows.length" description="执行完成，未返回数据" />
            <n-data-table
              v-else
              class="dataset-query-workbench__result-table"
              :columns="queryResultColumns"
              :data="queryRows"
              :loading="queryLoading"
              :pagination="false"
              size="small"
              :max-height="queryResultTableMaxHeight"
              :scroll-x="queryResultScrollX"
            />
            <div v-if="queryExecuted" class="dataset-query-workbench__pagination">
              <span>共 {{ queryTotal }} 行</span>
              <n-pagination v-model:page="queryPage" :page-size="queryPageSize" :item-count="queryTotal" @update:page="executeQuery" />
            </div>
          </div>
          <div v-else class="dataset-query-workbench__info">
            <n-result
              v-if="queryExecuted"
              status="success"
              title="执行成功"
              :description="`当前页返回 ${queryRows.length} 行，匹配 ${queryTotal} 行`"
            />
            <n-empty v-else description="运行后在这里查看执行信息" />
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script lang="ts" setup>
  import { computed, h, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { NTag, useMessage } from 'naive-ui';
  import type { DataTableColumns } from 'naive-ui';
  import { ArrowLeftOutlined, PlayCircleOutlined, SaveOutlined } from '@vicons/antd';
  import CodePreview from '@/components/CodePreview/index.vue';
  import VariableSchemaEditor from '@/components/VariableSchemaEditor/index.vue';
  import {
    executeDatasetQuery,
    getDataset,
    getDatasetSourceSchema,
    saveDataset,
    type Dataset,
    type DatasetField,
    type DatasetSourceColumn,
    type DatasetSourceTable,
  } from '@/api/datasets';

  type DataAccessSourceKind = 'alias' | 'table';

  interface DataAccessSourceOption {
    label: string;
    value: string;
    kind: DataAccessSourceKind;
    name: string;
    table: string;
    alias: string;
  }

  const route = useRoute();
  const router = useRouter();
  const message = useMessage();
  const datasetId = computed(() => Number(route.params.id || 0));
  const datasetLoading = ref(false);
  const queryLoading = ref(false);
  const savingQuery = ref(false);
  const schemaLoading = ref(false);
  const queryExecuted = ref(false);
  const queryError = ref('');
  const queryResultTab = ref<'info' | 'result'>('result');
  const dataset = ref<Dataset | null>(null);
  const datasetFields = ref<DatasetField[]>([]);
  const querySql = ref('');
  const queryParams = ref<unknown[] | Record<string, unknown>>([]);
  const queryDataAccess = ref<Record<string, unknown>>({});
  const queryVariablesSchema = ref<Record<string, unknown>>({});
  const queryVariables = ref<Record<string, unknown>>({});
  const queryRows = ref<Record<string, unknown>[]>([]);
  const queryFields = ref<DatasetField[]>([]);
  const queryTotal = ref(0);
  const queryPage = ref(1);
  const queryPageSize = 20;
  const queryEditorHeight = 'clamp(180px, 24vh, 240px)';
  const queryResultTableMaxHeight = 'clamp(260px, calc(100vh - 560px), 520px)';
  const sourceTables = ref<DatasetSourceTable[]>([]);
  const sourceSchemaBackend = ref('');
  const expandedTableKeys = ref<string[]>([]);
  const schemaKeyword = ref('');

  const filteredSourceTables = computed(() => {
    const keyword = schemaKeyword.value.trim().toLowerCase();
    if (!keyword) return sourceTables.value;
    return sourceTables.value
      .map((table) => {
        const tableMatched = qualifiedTableName(table).toLowerCase().includes(keyword);
        const columns = table.columns.filter((column) => column.name.toLowerCase().includes(keyword) || column.data_type.toLowerCase().includes(keyword));
        return tableMatched ? table : { ...table, columns };
      })
      .filter((table) => qualifiedTableName(table).toLowerCase().includes(keyword) || table.columns.length);
  });

  const schemaEmptyText = computed(() => {
    if (schemaKeyword.value.trim()) return '没有匹配的表或字段';
    return sourceSchemaBackend.value ? '暂无表结构' : '表结构尚未加载';
  });

  const querySqlLineCount = computed(() => Math.max(1, querySql.value.split(/\r?\n/).length));
  const hasQueryVariables = computed(() => extractTemplateVariableKeys(querySql.value).length > 0 || schemaVariableKeys(queryVariablesSchema.value).length > 0);

  const queryResultColumns = computed<DataTableColumns<Record<string, unknown>>>(() => {
    const columnsFromRows = inferColumnsFromRows(queryRows.value);
    if (columnsFromRows.length) return columnsFromRows;
    const fields = queryFields.value.length ? queryFields.value : datasetFields.value;
    const columnsFromFields = fields
      .filter((field) => field.visible !== false)
      .map((field) => ({
        title: field.label || field.field_key,
        key: field.field_key,
        minWidth: 140,
        ellipsis: { tooltip: true },
        render: (row: Record<string, unknown>) => formatCellValue(row[field.field_key]),
      }));
    if (columnsFromFields.length) return columnsFromFields;
    return inferColumnsFromRows(queryRows.value);
  });

  const queryResultScrollX = computed(() => Math.max(queryResultColumns.value.length * 150, 760));
  const queryTableReferences = computed(() => extractSqlTableReferences(querySql.value));
  const hasMultiTableQuery = computed(() => queryTableReferences.value.length > 1);
  const selectedDataAccessSource = computed({
    get(): string | null {
      return currentDataAccessSourceValue();
    },
    set(value: string | null) {
      const next = { ...queryDataAccess.value };
      delete next.source_alias;
      delete next.source_table;
      const source = parseDataAccessSourceValue(value);
      if (source?.kind === 'alias') next.source_alias = source.name;
      if (source?.kind === 'table') next.source_table = source.name;
      queryDataAccess.value = pruneEmptyDataAccess(next);
    },
  });
  const dataAccessSourceOptions = computed<DataAccessSourceOption[]>(() => {
    const seen = new Set<string>();
    const options = queryTableReferences.value.filter((option) => {
      if (seen.has(option.value)) return false;
      seen.add(option.value);
      return true;
    });
    const current = currentDataAccessSourceOption();
    if (current && !seen.has(current.value)) {
      options.unshift(current);
    }
    return options;
  });
  const suggestedDataAccessOption = computed(() => {
    const firstReference = queryTableReferences.value[0];
    if (!firstReference) return dataAccessSourceOptions.value[0] || null;
    return dataAccessSourceOptions.value.find((option) => option.value === firstReference.value) || firstReference;
  });
  const dataAccessWarningText = computed(() => {
    const suggestion = suggestedDataAccessOption.value?.label;
    if (!suggestion) return '检测到多表 SQL，请选择用于注入权限条件的主业务表/别名。';
    return `检测到 ${queryTableReferences.value.length} 张表，请选择用于注入权限条件的主业务表/别名。通常选择 FROM 后面的业务主表，当前建议为 ${suggestion}。`;
  });
  const dataAccessSourceHelpText = computed(() => {
    const selected = dataAccessSourceOptions.value.find((option) => option.value === selectedDataAccessSource.value);
    if (selected) return `已选择 ${selected.label}，系统会把当前租户和数据范围条件加到这张表上。`;
    if (queryTableReferences.value.length === 1) return '单表 SQL 通常无需手动配置；如果后续增加 JOIN，可以在这里固定主业务表。';
    return '系统会根据 SQL 中的 FROM/JOIN 自动列出候选表。';
  });
  const dataAccessRequiredMessage = computed(() => {
    const suggestion = suggestedDataAccessOption.value?.label;
    return suggestion
      ? `检测到多表 SQL，请先在“数据权限”中选择主业务表/别名。建议选择 ${suggestion}。`
      : '检测到多表 SQL，请先在“数据权限”中选择主业务表/别名。';
  });

  async function loadDataset() {
    if (!datasetId.value) return;
    datasetLoading.value = true;
    try {
      const detail = await getDataset(datasetId.value);
      dataset.value = detail.item;
      datasetFields.value = detail.fields || [];
      resetQueryFromDataset();
      if (detail.item?.dataset_type !== 'source_query') {
        message.error('只有数据源查询类型支持 SQL 工作台');
      }
    } finally {
      datasetLoading.value = false;
    }
  }

  async function loadSourceSchema() {
    if (!datasetId.value) return;
    schemaLoading.value = true;
    try {
      const payload = await getDatasetSourceSchema(datasetId.value);
      sourceTables.value = payload.tables || [];
      sourceSchemaBackend.value = payload.backend || '';
      expandedTableKeys.value = sourceTables.value.slice(0, 4).map(tableKey);
    } finally {
      schemaLoading.value = false;
    }
  }

  function resetQueryFromDataset() {
    const config = dataset.value?.query_config || {};
    querySql.value = String(config.sql || '');
    queryParams.value = normalizeQueryParams(config.params);
    queryDataAccess.value = pruneEmptyDataAccess(normalizeSchemaObject(config.data_access));
    queryVariablesSchema.value = normalizeSchemaObject(config.variables_schema);
    queryVariables.value = {};
    queryRows.value = [];
    queryFields.value = [];
    queryTotal.value = 0;
    queryPage.value = 1;
    queryExecuted.value = false;
    queryError.value = '';
  }

  async function executeQuery() {
    if (!dataset.value) return;
    const queryConfig = buildCurrentQueryConfig();
    if (!queryConfig) return;
    queryLoading.value = true;
    queryError.value = '';
    try {
      const payload = await executeDatasetQuery(
        dataset.value.id,
        {
          query_config: queryConfig,
          variables: queryVariables.value,
        },
        { page: queryPage.value, page_size: queryPageSize }
      );
      queryFields.value = payload.fields || [];
      queryRows.value = payload.items || [];
      queryTotal.value = payload.pagination?.total || queryRows.value.length;
      queryExecuted.value = true;
      queryResultTab.value = 'result';
      message.success(`执行完成，返回 ${queryRows.value.length} 行`);
    } catch (error) {
      queryRows.value = [];
      queryFields.value = [];
      queryTotal.value = 0;
      queryExecuted.value = false;
      queryResultTab.value = 'result';
      queryError.value = normalizeQueryExecutionError(error);
      message.error(queryError.value);
    } finally {
      queryLoading.value = false;
    }
  }

  async function runQuery() {
    queryPage.value = 1;
    await executeQuery();
  }

  async function saveQueryConfig() {
    if (!dataset.value) return;
    const queryConfig = buildCurrentQueryConfig();
    if (!queryConfig) return;
    savingQuery.value = true;
    try {
      const payload = await saveDataset({
        ...dataset.value,
        dataset_type: 'source_query',
        query_config: queryConfig,
      });
      dataset.value = payload.item;
      resetQueryFromDataset();
      message.success('SQL 配置已保存，数据预览将使用当前配置');
    } finally {
      savingQuery.value = false;
    }
  }

  function buildCurrentQueryConfig() {
    const sql = querySql.value.trim();
    if (!sql) {
      message.error('请输入查询 SQL');
      return null;
    }
    if (hasMultiTableQuery.value && !selectedDataAccessSource.value) {
      message.warning(dataAccessRequiredMessage.value);
      return null;
    }
    const queryConfig: Record<string, unknown> = {
      sql,
      variables_schema: queryVariablesSchema.value,
      max_rows: 1000,
    };
    queryConfig.params = buildQueryParams(sql, queryVariablesSchema.value, queryParams.value);
    if (Object.keys(queryDataAccess.value).length) {
      queryConfig.data_access = queryDataAccess.value;
    }
    return queryConfig;
  }

  function normalizeQueryParams(value: unknown): unknown[] | Record<string, unknown> {
    if (Array.isArray(value)) return value;
    if (value && typeof value === 'object') return value as Record<string, unknown>;
    return [];
  }

  function normalizeSchemaObject(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
  }

  function pruneEmptyDataAccess(value: Record<string, unknown>): Record<string, unknown> {
    return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== '' && item !== null && item !== undefined));
  }

  function buildQueryParams(sql: string, schema: Record<string, unknown>, fallback: unknown[] | Record<string, unknown>) {
    if (!sql.includes('?')) return fallback;
    const keys = schemaVariableKeys(schema);
    return keys.length ? keys.map((key) => `{{${key}}}`) : fallback;
  }

  function schemaVariableKeys(schema: Record<string, unknown>): string[] {
    const properties = normalizeSchemaObject(schema.properties);
    if (Object.keys(properties).length) return Object.keys(properties);
    const variables = Array.isArray(schema.variables) ? schema.variables : [];
    return variables
      .map((item) => {
        if (typeof item === 'string') return item;
        const record = normalizeSchemaObject(item);
        return typeof record.key === 'string' ? record.key : typeof record.name === 'string' ? record.name : '';
      })
      .filter(Boolean);
  }

  function extractTemplateVariableKeys(template: string): string[] {
    const keys = new Set<string>();
    for (const match of template.matchAll(/\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g)) {
      keys.add(match[1]);
    }
    return [...keys];
  }

  function extractSqlTableReferences(sql: string): DataAccessSourceOption[] {
    const cleanedSql = stripSqlComments(sql).replace(/\s+/g, ' ');
    const reservedAliases = new Set(['where', 'on', 'left', 'right', 'inner', 'full', 'cross', 'join', 'group', 'order', 'limit', 'having', 'union', 'offset']);
    const tablePattern = /\b(?:from|join)\s+([`"\[]?[a-zA-Z_][\w$]*(?:\.[`"\[]?[a-zA-Z_][\w$]*)?[`"\]]?)(?:\s+(?:as\s+)?([`"\[]?[a-zA-Z_][\w$]*[`"\]]?))?/gi;
    const references: DataAccessSourceOption[] = [];
    for (const match of cleanedSql.matchAll(tablePattern)) {
      const table = normalizeSqlIdentifier(match[1] || '');
      const rawAlias = normalizeSqlIdentifier(match[2] || '');
      const alias = rawAlias && !reservedAliases.has(rawAlias.toLowerCase()) ? rawAlias : '';
      if (!table) continue;
      const kind: DataAccessSourceKind = alias ? 'alias' : 'table';
      const name = alias || table;
      references.push({
        label: alias ? `${alias}（${table}）` : table,
        value: `${kind}:${name}`,
        kind,
        name,
        table,
        alias,
      });
    }
    return references;
  }

  function stripSqlComments(sql: string) {
    return sql.replace(/--.*$/gm, ' ').replace(/\/\*[\s\S]*?\*\//g, ' ');
  }

  function normalizeSqlIdentifier(value: string) {
    return value.trim().replace(/^[`"\[]+|[`"\]]+$/g, '');
  }

  function currentDataAccessSourceValue() {
    const alias = typeof queryDataAccess.value.source_alias === 'string' ? queryDataAccess.value.source_alias.trim() : '';
    if (alias) return `alias:${alias}`;
    const table = typeof queryDataAccess.value.source_table === 'string' ? queryDataAccess.value.source_table.trim() : '';
    return table ? `table:${table}` : null;
  }

  function currentDataAccessSourceOption(): DataAccessSourceOption | null {
    const source = parseDataAccessSourceValue(currentDataAccessSourceValue());
    if (!source) return null;
    return {
      label: source.kind === 'alias' ? `当前别名：${source.name}` : `当前表：${source.name}`,
      value: `${source.kind}:${source.name}`,
      kind: source.kind,
      name: source.name,
      table: source.kind === 'table' ? source.name : '',
      alias: source.kind === 'alias' ? source.name : '',
    };
  }

  function parseDataAccessSourceValue(value: string | null | undefined): { kind: DataAccessSourceKind; name: string } | null {
    if (!value) return null;
    const separatorIndex = value.indexOf(':');
    if (separatorIndex <= 0) return null;
    const kind = value.slice(0, separatorIndex);
    const name = value.slice(separatorIndex + 1).trim();
    if ((kind === 'alias' || kind === 'table') && name) return { kind, name };
    return null;
  }

  function useSuggestedDataAccessSource() {
    if (!suggestedDataAccessOption.value) return;
    selectedDataAccessSource.value = suggestedDataAccessOption.value.value;
  }

  function normalizeQueryExecutionError(error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'SQL 执行失败';
    if (errorMessage.includes('多表 SQL 需要配置 data_access.source_table 或 source_alias')) {
      return dataAccessRequiredMessage.value;
    }
    if (errorMessage.includes('data_access.source_alias 未匹配到唯一数据表')) {
      return '数据权限里选择的表别名没有匹配到 SQL 中的唯一表，请重新选择主业务表/别名。';
    }
    if (errorMessage.includes('data_access.source_table 未匹配到唯一数据表')) {
      return '数据权限里选择的主表没有匹配到 SQL 中的唯一表，请重新选择主业务表/别名。';
    }
    return errorMessage;
  }

  function inferColumnsFromRows(items: Record<string, unknown>[]): DataTableColumns<Record<string, unknown>> {
    const keys = Array.from(new Set(items.flatMap((item) => Object.keys(item)))).slice(0, 40);
    return keys.map((key) => ({
      title: key,
      key,
      minWidth: 140,
      ellipsis: { tooltip: true },
      render: (row) => formatCellValue(row[key]),
    }));
  }

  function formatCellValue(value: unknown) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'boolean') {
      return h(
        NTag,
        { size: 'small', bordered: false, type: value ? 'success' : 'default' },
        { default: () => (value ? '是' : '否') }
      );
    }
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

  function tableKey(table: DatasetSourceTable) {
    return `${table.schema || 'default'}.${table.name}`;
  }

  function qualifiedTableName(table: DatasetSourceTable) {
    return table.schema ? `${table.schema}.${table.name}` : table.name;
  }

  function displayTableName(table: DatasetSourceTable) {
    return table.name;
  }

  function toggleSourceTable(table: DatasetSourceTable) {
    const key = tableKey(table);
    if (expandedTableKeys.value.includes(key)) {
      expandedTableKeys.value = expandedTableKeys.value.filter((item) => item !== key);
      return;
    }
    expandedTableKeys.value = [...expandedTableKeys.value, key];
  }

  function appendColumnToSql(columnName: DatasetSourceColumn['name']) {
    const current = querySql.value.trimEnd();
    querySql.value = `${current}${current ? ' ' : ''}${columnName}`;
  }

  function formatQuerySql() {
    querySql.value = querySql.value
      .replace(/\s+(from|where|group by|order by|limit)\s+/gi, '\n$1 ')
      .replace(/\s*,\s*/g, ', ')
      .trim();
  }

  function goBack() {
    router.push({ name: 'dataset-management' });
  }

  void loadDataset();
  void loadSourceSchema();
</script>

<style lang="less" scoped>
  .dataset-query-page {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-width: 0;
    height: calc(100vh - 116px);
    min-height: calc(100vh - 116px);
    overflow: hidden;
    background: var(--app-body-bg);
  }

  .dataset-query-page__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    min-width: 0;
    padding: 10px 12px 14px;
    border-bottom: 1px solid var(--app-border-color);
  }

  .dataset-query-page__titlebar,
  .dataset-query-page__actions {
    min-width: 0;
  }

  .dataset-query-page__titlebar {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .dataset-query-page__title {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .dataset-query-page__title span {
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .dataset-query-page__title strong {
    overflow: hidden;
    font-size: 18px;
    font-weight: 650;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dataset-query-workbench {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }

  .dataset-query-workbench__schema {
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--app-surface-bg);
    border-right: 1px solid var(--app-border-color);
  }

  .dataset-query-workbench__schema-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-height: 52px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--app-border-color);
  }

  .dataset-query-workbench__schema-head div {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .dataset-query-workbench__schema-head strong {
    font-weight: 650;
  }

  .dataset-query-workbench__schema-head span,
  .dataset-query-workbench__toolbar span,
  .dataset-query-workbench__result-head > span {
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .dataset-query-workbench__schema-search {
    min-width: 0;
    padding: 10px 12px;
    border-bottom: 1px solid var(--app-border-color);
  }

  .dataset-query-workbench__schema-search :deep(.n-input) {
    width: 100%;
  }

  .dataset-query-workbench__schema-body {
    min-height: 0;
    overflow: hidden;
  }

  .dataset-query-workbench__schema-body :deep(.n-spin-content) {
    height: 100%;
    min-height: 0;
  }

  .dataset-query-workbench__tables {
    height: 100%;
    min-height: 0;
    padding: 0 8px 12px;
    overflow: auto;
  }

  .dataset-query-workbench__table {
    border-radius: 6px;
  }

  .dataset-query-workbench__table-name,
  .dataset-query-workbench__column {
    display: flex;
    align-items: center;
    width: 100%;
    min-width: 0;
    border: 0;
    background: transparent;
    color: inherit;
    text-align: left;
    cursor: pointer;
  }

  .dataset-query-workbench__table-name {
    gap: 8px;
    height: 34px;
    padding: 0 8px;
    border-radius: 6px;
  }

  .dataset-query-workbench__table-name:hover,
  .dataset-query-workbench__column:hover {
    background: var(--app-hover-color);
  }

  .dataset-query-workbench__table-name span {
    width: 16px;
    color: var(--app-text-color-3);
    text-align: center;
  }

  .dataset-query-workbench__table-name strong {
    flex: 1;
    overflow: hidden;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dataset-query-workbench__table-name small,
  .dataset-query-workbench__column small {
    flex: none;
    color: var(--app-text-color-3);
  }

  .dataset-query-workbench__columns {
    padding: 2px 0 8px 30px;
  }

  .dataset-query-workbench__column {
    justify-content: space-between;
    gap: 8px;
    min-height: 28px;
    padding: 0 8px;
    border-radius: 5px;
  }

  .dataset-query-workbench__column span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dataset-query-workbench__main {
    display: grid;
    grid-template-rows: auto auto;
    gap: 12px;
    min-width: 0;
    min-height: 0;
    padding: 12px;
    overflow: auto;
  }

  .dataset-query-workbench__editor-card,
  .dataset-query-workbench__access-card,
  .dataset-query-workbench__result,
  .dataset-query-workbench__main :deep(.variable-schema-editor) {
    min-width: 0;
    overflow: hidden;
    background: var(--app-surface-bg);
    border: 1px solid var(--app-border-color);
    border-radius: 6px;
  }

  .dataset-query-workbench__editor-card :deep(.code-preview) {
    max-height: 240px;
  }

  .dataset-query-workbench__access-card {
    display: grid;
    gap: 10px;
    padding: 12px;
  }

  .dataset-query-workbench__access-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
  }

  .dataset-query-workbench__access-head div {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .dataset-query-workbench__access-head strong {
    color: var(--app-text-color-1);
    font-weight: 650;
  }

  .dataset-query-workbench__access-head span,
  .dataset-query-workbench__access-tip {
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  .dataset-query-workbench__access-row {
    display: grid;
    grid-template-columns: minmax(260px, 420px) auto;
    gap: 8px;
    align-items: center;
  }

  .dataset-query-workbench__access-tip {
    margin: 0;
    line-height: 1.5;
  }

  .dataset-query-workbench__toolbar,
  .dataset-query-workbench__result-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 40px;
    padding: 0 12px;
    border-bottom: 1px solid var(--app-border-color);
  }

  .dataset-query-workbench__result {
    display: grid;
    grid-template-rows: auto auto;
    min-height: 0;
  }

  .dataset-query-workbench__result-status {
    flex: none;
    white-space: nowrap;
  }

  .dataset-query-workbench__result-head :deep(.n-tabs-nav) {
    line-height: 40px;
  }

  .dataset-query-workbench__result-body {
    display: grid;
    grid-template-rows: auto auto;
    min-height: 0;
    padding: 12px;
    overflow: hidden;
  }

  .dataset-query-workbench__result-table {
    min-width: 0;
    min-height: 0;
  }

  .dataset-query-workbench__result-table :deep(.n-data-table-base-table-body) {
    overflow: auto;
  }

  .dataset-query-workbench__pagination {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding-top: 12px;
  }

  .dataset-query-workbench__pagination span {
    color: var(--app-text-color-3);
  }

  .dataset-query-workbench__info {
    display: grid;
    place-items: center;
    min-height: 220px;
    padding: 24px;
  }

  @media (max-width: 980px) {
    .dataset-query-page {
      height: auto;
      min-height: 0;
    }

    .dataset-query-page__header {
      align-items: stretch;
      flex-direction: column;
    }

    .dataset-query-page__actions {
      justify-content: flex-start;
    }

    .dataset-query-workbench {
      grid-template-columns: 1fr;
      overflow: visible;
    }

    .dataset-query-workbench__schema {
      max-height: 320px;
      border-right: 0;
      border-bottom: 1px solid var(--app-border-color);
    }

    .dataset-query-workbench__main {
      overflow: visible;
    }

    .dataset-query-workbench__access-row {
      grid-template-columns: 1fr;
    }

    .dataset-query-workbench__editor-card :deep(.code-preview) {
      max-height: 220px;
    }
  }
</style>
