<template>
  <section class="variable-schema-editor">
    <div class="variable-schema-editor__head">
      <div>
        <strong>{{ title }}</strong>
        <span v-if="description">{{ description }}</span>
      </div>
      <n-space :size="8">
        <n-button v-if="templateText" size="tiny" secondary @click="syncFromTemplate">同步变量</n-button>
        <n-button size="tiny" type="primary" secondary @click="addVariable">添加变量</n-button>
      </n-space>
    </div>

    <div v-if="rows.length" class="variable-schema-editor__table" :class="{ 'has-values': showValues }">
      <div class="variable-schema-editor__row variable-schema-editor__row--head">
        <span>变量 Key</span>
        <span>变量名称</span>
        <span>类型</span>
        <span>必填</span>
        <span v-if="showValues">测试值</span>
        <span>操作</span>
      </div>
      <div v-for="(row, index) in rows" :key="row.id" class="variable-schema-editor__row">
        <n-input
          v-model:value="row.key"
          size="small"
          clearable
          placeholder="例如：status"
          @update:value="emitSchema"
        />
        <n-input
          v-model:value="row.label"
          size="small"
          clearable
          placeholder="用于表单展示"
          @update:value="emitSchema"
        />
        <n-select
          v-model:value="row.type"
          :options="typeOptions"
          size="small"
          :consistent-menu-width="false"
          @update:value="handleTypeChange(row)"
        />
        <n-switch v-model:value="row.required" size="small" @update:value="emitSchema" />
        <template v-if="showValues">
          <n-switch v-if="row.type === 'boolean'" v-model:value="valueDraft[row.key]" size="small" @update:value="emitValues" />
          <n-input-number
            v-else-if="row.type === 'number' || row.type === 'integer'"
            v-model:value="valueDraft[row.key]"
            size="small"
            clearable
            @update:value="emitValues"
          />
          <n-input v-else v-model:value="valueDraft[row.key]" size="small" clearable :placeholder="`请输入${row.label || row.key}`" @update:value="emitValues" />
        </template>
        <n-button size="tiny" text type="error" @click="removeVariable(index)">删除</n-button>
      </div>
    </div>
    <n-empty v-else size="small" description="暂无变量，点击“添加变量”开始定义。" />
  </section>
</template>

<script lang="ts" setup>
  import { ref, watch } from 'vue';

  export type VariableSchemaType = 'text' | 'string' | 'number' | 'integer' | 'boolean';

  interface VariableRow {
    id: string;
    key: string;
    label: string;
    description: string;
    type: VariableSchemaType;
    required: boolean;
    source: 'template' | 'manual';
  }

  type SchemaRecord = Record<string, unknown>;

  const props = withDefaults(
    defineProps<{
      modelValue?: Record<string, unknown>;
      values?: Record<string, unknown>;
      title?: string;
      description?: string;
      templateText?: string;
      showValues?: boolean;
    }>(),
    {
      modelValue: () => ({}),
      values: () => ({}),
      title: '变量',
      description: '',
      templateText: '',
      showValues: false,
    }
  );

  const emit = defineEmits<{
    'update:modelValue': [value: Record<string, unknown>];
    'update:values': [value: Record<string, unknown>];
  }>();

  const TEMPLATE_VARIABLE_PATTERN = /\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g;
  const RESERVED_SCHEMA_KEYS = new Set(['type', 'title', 'label', 'description', 'properties', 'required', 'default', 'example']);
  const typeOptions = [
    { label: '文本', value: 'text' },
    { label: '数字', value: 'number' },
    { label: '开关', value: 'boolean' },
  ];
  const rows = ref<VariableRow[]>([]);
  const valueDraft = ref<Record<string, any>>({});
  let syncing = false;

  watch(
    () => props.modelValue,
    (value) => {
      if (syncing) return;
      rows.value = rowsFromSchema(value, props.templateText);
      syncValueKeys();
    },
    { immediate: true, deep: true }
  );

  watch(
    () => props.templateText,
    () => {
      rows.value = rowsFromTemplateChange();
      syncValueKeys();
      emitSchema();
    }
  );

  watch(
    () => props.values,
    (value) => {
      const nextValues = flattenValues(asRecord(value) || {});
      if (!isSameValue(valueDraft.value, nextValues)) {
        valueDraft.value = nextValues;
      }
      syncValueKeys({ emit: false });
    },
    { immediate: true, deep: true }
  );

  function addVariable() {
    rows.value = [
      ...rows.value,
      {
        id: uniqueId(),
        key: nextVariableKey(),
        label: '',
        description: '',
        type: 'text',
        required: true,
        source: 'manual',
      },
    ];
    syncValueKeys();
    emitSchema();
  }

  function removeVariable(index: number) {
    const [removed] = rows.value.splice(index, 1);
    if (removed?.key) {
      const nextValues = { ...valueDraft.value };
      delete nextValues[removed.key];
      valueDraft.value = nextValues;
      emitValues();
    }
    emitSchema();
  }

  function syncFromTemplate() {
    rows.value = rowsFromTemplateChange();
    syncValueKeys();
    emitSchema();
  }

  function handleTypeChange(row: VariableRow) {
    if (row.key && typeof valueDraft.value[row.key] !== 'undefined') {
      const nextValues = { ...valueDraft.value };
      nextValues[row.key] = defaultValueForType(row.type);
      valueDraft.value = nextValues;
      emitValues();
    }
    emitSchema();
  }

  function emitSchema() {
    const nextSchema = buildSchema();
    if (isSameValue(nextSchema, props.modelValue || {})) return;
    syncing = true;
    emit('update:modelValue', nextSchema);
    queueMicrotask(() => {
      syncing = false;
    });
  }

  function emitValues() {
    const nextValues = buildNestedValues(compactValues(valueDraft.value));
    if (isSameValue(nextValues, props.values || {})) return;
    emit('update:values', nextValues);
  }

  function syncValueKeys(options: { emit?: boolean } = {}) {
    if (!props.showValues) return;
    const activeKeys = new Set(rows.value.map((row) => row.key).filter(Boolean));
    const nextValues = { ...valueDraft.value };
    Object.keys(nextValues).forEach((key) => {
      if (!activeKeys.has(key)) delete nextValues[key];
    });
    rows.value.forEach((row) => {
      if (!row.key || typeof nextValues[row.key] !== 'undefined') return;
      nextValues[row.key] = defaultValueForType(row.type);
    });
    const changed = !isSameValue(valueDraft.value, nextValues);
    valueDraft.value = nextValues;
    if (options.emit !== false && changed) emitValues();
  }

  function rowsFromSchema(schemaValue: unknown, templateText = ''): VariableRow[] {
    const schema = asRecord(schemaValue);
    const { entries, requiredKeys } = collectSchemaEntries(schema || undefined);
    const templateKeys = extractTemplateVariableKeys(templateText);
    const templateKeySet = new Set(templateKeys);
    const keys = [...new Set([...templateKeys, ...entries.keys()])];
    return keys.map((key) => {
      const raw = entries.get(key);
      const node = asRecord(raw);
      const label = String(node?.label || node?.title || node?.name || (typeof raw === 'string' ? raw : '') || key);
      return {
        id: uniqueId(key),
        key,
        label,
        description: String(node?.description || node?.help || ''),
        type: normalizeType(String(node?.type || '')),
        required: node?.required === false ? false : requiredKeys.has(key) || node?.required === true || templateText.includes(`{{${key}}`),
        source: templateKeySet.has(key) ? 'template' : 'manual',
      };
    });
  }

  function rowsFromTemplateChange(): VariableRow[] {
    const templateKeys = extractTemplateVariableKeys(props.templateText);
    const templateKeySet = new Set(templateKeys);
    const currentRows = new Map(rows.value.map((row) => [row.key, row]));
    const templateRows = templateKeys.map((key) => {
      const current = currentRows.get(key);
      return {
        id: current?.id || uniqueId(key),
        key,
        label: current?.label || key,
        description: current?.description || '',
        type: current?.type || 'text',
        required: current?.required ?? true,
        source: 'template' as const,
      };
    });
    const manualRows = rows.value.filter((row) => row.source === 'manual' && row.key && !templateKeySet.has(row.key));
    return [...templateRows, ...manualRows];
  }

  function buildSchema(): Record<string, unknown> {
    const validRows = rows.value.map((row) => normalizeRow(row)).filter((row) => row.key);
    if (!validRows.length) return {};
    const properties = validRows.reduce<Record<string, unknown>>((result, row) => {
      result[row.key] = {
        type: schemaType(row.type),
        ...(row.label && row.label !== row.key ? { label: row.label } : {}),
        ...(row.description ? { description: row.description } : {}),
        ...(row.required ? {} : { required: false }),
      };
      return result;
    }, {});
    return {
      type: 'object',
      required: validRows.filter((row) => row.required).map((row) => row.key),
      properties,
    };
  }

  function normalizeRow(row: VariableRow): VariableRow {
    return {
      ...row,
      key: row.key.trim(),
      label: row.label.trim(),
      description: row.description.trim(),
      type: normalizeType(row.type),
    };
  }

  function collectSchemaEntries(schema?: SchemaRecord): {
    entries: Map<string, unknown>;
    requiredKeys: Set<string>;
  } {
    const entries = new Map<string, unknown>();
    const requiredKeys = new Set<string>();
    if (!schema) return { entries, requiredKeys };
    const required = Array.isArray(schema.required) ? schema.required : [];
    required.forEach((key) => {
      if (typeof key === 'string') requiredKeys.add(key);
    });

    const properties = asRecord(schema.properties);
    if (properties) {
      Object.entries(properties).forEach(([key, value]) => entries.set(key, value));
      return { entries, requiredKeys };
    }

    const variables = Array.isArray(schema.variables) ? schema.variables : [];
    variables.forEach((item) => {
      if (typeof item === 'string') {
        entries.set(item, {});
        return;
      }
      const record = asRecord(item);
      const key = record && typeof record.key === 'string' ? record.key : record && typeof record.name === 'string' ? record.name : '';
      if (key) entries.set(key, record);
    });

    Object.entries(schema).forEach(([key, value]) => {
      if (!RESERVED_SCHEMA_KEYS.has(key) && !entries.has(key)) entries.set(key, value);
    });
    return { entries, requiredKeys };
  }

  function extractTemplateVariableKeys(template: string): string[] {
    const keys = new Set<string>();
    for (const match of template.matchAll(TEMPLATE_VARIABLE_PATTERN)) {
      keys.add(match[1]);
    }
    return [...keys];
  }

  function asRecord(value: unknown): SchemaRecord | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as SchemaRecord) : null;
  }

  function normalizeType(value: string): VariableSchemaType {
    if (value === 'boolean') return 'boolean';
    if (value === 'number' || value === 'integer') return value;
    return 'text';
  }

  function schemaType(type: VariableSchemaType) {
    return type === 'text' ? 'string' : type;
  }

  function defaultValueForType(type: VariableSchemaType) {
    if (type === 'boolean') return false;
    return null;
  }

  function compactValues(values: Record<string, unknown>) {
    return Object.fromEntries(
      Object.entries(values).filter(([, value]) => value !== null && typeof value !== 'undefined' && !(typeof value === 'string' && value === ''))
    );
  }

  function buildNestedValues(values: Record<string, unknown>) {
    const nested: Record<string, unknown> = {};
    Object.entries(values).forEach(([key, value]) => {
      const parts = key.split('.').filter(Boolean);
      if (!parts.length) return;
      let current = nested;
      parts.forEach((part, index) => {
        if (index === parts.length - 1) {
          current[part] = value;
          return;
        }
        const next = asRecord(current[part]) || {};
        current[part] = next;
        current = next;
      });
    });
    return nested;
  }

  function flattenValues(values: Record<string, unknown>, prefix = '') {
    const flat: Record<string, unknown> = {};
    Object.entries(values).forEach(([key, value]) => {
      const nextKey = prefix ? `${prefix}.${key}` : key;
      const record = asRecord(value);
      if (record) {
        Object.assign(flat, flattenValues(record, nextKey));
        return;
      }
      flat[nextKey] = value;
    });
    return flat;
  }

  function isSameValue(left: unknown, right: unknown) {
    return stableStringify(left) === stableStringify(right);
  }

  function stableStringify(value: unknown): string {
    return JSON.stringify(sortJsonValue(value));
  }

  function sortJsonValue(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(sortJsonValue);
    const record = asRecord(value);
    if (!record) return value;
    return Object.keys(record)
      .sort()
      .reduce<Record<string, unknown>>((result, key) => {
        result[key] = sortJsonValue(record[key]);
        return result;
      }, {});
  }

  function nextVariableKey() {
    const existing = new Set(rows.value.map((row) => row.key));
    let index = rows.value.length + 1;
    while (existing.has(`param${index}`)) index += 1;
    return `param${index}`;
  }

  function uniqueId(prefix = 'variable') {
    return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  }
</script>

<style lang="less" scoped>
  .variable-schema-editor {
    display: grid;
    gap: 0;
    min-width: 0;
  }

  .variable-schema-editor__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
    padding: 14px 16px 12px;
  }

  .variable-schema-editor__head > div {
    display: grid;
    gap: 4px;
    min-width: 0;
  }

  .variable-schema-editor__head strong {
    color: var(--app-text-color-1);
    font-size: 15px;
    font-weight: 650;
    line-height: 1.35;
  }

  .variable-schema-editor__head span {
    color: var(--app-text-color-3);
    font-size: 12px;
    line-height: 1.45;
  }

  .variable-schema-editor__head :deep(.n-space) {
    flex: none;
  }

  .variable-schema-editor__table {
    display: grid;
    min-width: 0;
    overflow-x: auto;
    border-top: 1px solid var(--app-border-color);
    border-radius: 0 0 6px 6px;
  }

  .variable-schema-editor__row {
    display: grid;
    grid-template-columns: minmax(130px, 1.1fr) minmax(130px, 1fr) 108px 72px 54px;
    gap: 8px;
    align-items: center;
    min-width: 560px;
    min-height: 42px;
    padding: 8px 10px;
    border-top: 1px solid var(--app-border-color);
  }

  .variable-schema-editor__table.has-values .variable-schema-editor__row {
    grid-template-columns: minmax(120px, 1fr) minmax(120px, 1fr) 104px 64px minmax(140px, 1fr) 54px;
    min-width: 720px;
  }

  .variable-schema-editor__row:first-child {
    border-top: 0;
  }

  .variable-schema-editor__row--head {
    min-height: 34px;
    background: var(--app-muted-bg);
    color: var(--app-text-color-3);
    font-size: 12px;
  }

  @media (max-width: 720px) {
    .variable-schema-editor__head {
      align-items: stretch;
      flex-direction: column;
      padding: 12px;
    }
  }
</style>
