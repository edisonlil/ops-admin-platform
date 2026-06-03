<template>
  <div ref="containerRef" class="code-preview nodrag nopan nowheel"></div>
</template>

<script lang="ts" setup>
  import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
  import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
  import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
  import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';

  const EDITOR_LINE_HEIGHT = 21;
  const EDITOR_VERTICAL_PADDING = 20;

  const props = withDefaults(
    defineProps<{
      value: string;
      language?: string;
      height?: string | number;
      minHeight?: string | number;
      maxHeight?: string | number;
      readOnly?: boolean;
      autoHeight?: boolean;
    }>(),
    {
      language: 'plaintext',
      height: '420px',
      minHeight: 120,
      maxHeight: 520,
      readOnly: true,
      autoHeight: true,
    }
  );
  const emit = defineEmits<{
    (event: 'update:value', value: string): void;
  }>();

  const containerRef = ref<HTMLElement | null>(null);
  let monacoApi: typeof Monaco | null = null;
  let editor: Monaco.editor.IStandaloneCodeEditor | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let contentSizeDisposable: { dispose: () => void } | null = null;
  let layoutFrame: number | null = null;
  let disposed = false;

  self.MonacoEnvironment = {
    getWorker(_workerId: string, label: string) {
      if (label === 'json') return new jsonWorker();
      return new editorWorker();
    },
  };

  function toPixelSize(value: string | number | undefined, fallback: number) {
    if (typeof value === 'number') return value;
    const parsed = Number.parseFloat(value ?? '');
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function toCssSize(value: string | number) {
    return typeof value === 'number' ? `${value}px` : value;
  }

  function scheduleEditorLayout() {
    if (layoutFrame !== null) window.cancelAnimationFrame(layoutFrame);
    layoutFrame = window.requestAnimationFrame(() => {
      layoutFrame = null;
      applyEditorLayout();
    });
  }

  function applyEditorLayout() {
    if (!containerRef.value) return;

    if (!props.autoHeight || !editor) {
      containerRef.value.style.height = toCssSize(props.height);
      editor?.layout();
      return;
    }

    const minHeight = toPixelSize(props.minHeight, 120);
    const maxHeight = toPixelSize(props.maxHeight, toPixelSize(props.height, 520));
    const lineCount = editor.getModel()?.getLineCount() || 1;
    const estimatedHeight = lineCount * EDITOR_LINE_HEIGHT + EDITOR_VERTICAL_PADDING;
    const measuredHeight = editor.getContentHeight();
    const contentHeight = Math.max(estimatedHeight, measuredHeight);
    const nextHeight = Math.max(minHeight, Math.min(maxHeight, contentHeight));

    containerRef.value.style.height = `${nextHeight}px`;
    editor.layout({
      width: containerRef.value.clientWidth,
      height: nextHeight,
    });
  }

  onMounted(async () => {
    if (!containerRef.value) return;
    containerRef.value.style.height = props.autoHeight
      ? `${toPixelSize(props.minHeight, 120)}px`
      : toCssSize(props.height);
    const [monaco] = await Promise.all([
      import('monaco-editor/esm/vs/editor/editor.api'),
      props.language === 'json'
        ? import('monaco-editor/esm/vs/language/json/monaco.contribution')
        : props.language === 'sql'
          ? import('monaco-editor/esm/vs/basic-languages/sql/sql.contribution')
          : props.language === 'python'
            ? import('monaco-editor/esm/vs/basic-languages/python/python.contribution')
        : Promise.resolve(),
    ]);
    if (disposed || !containerRef.value) return;
    monacoApi = monaco;
    editor = monaco.editor.create(containerRef.value, {
      value: props.value,
      language: props.language,
      readOnly: props.readOnly,
      automaticLayout: false,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      wordWrap: 'on',
      wrappingIndent: 'same',
      renderLineHighlight: 'none',
      folding: true,
      lineNumbersMinChars: 3,
      fontSize: 13,
      lineHeight: 21,
      padding: { top: 10, bottom: 10 },
      overviewRulerLanes: 0,
    });
    contentSizeDisposable = editor.onDidContentSizeChange(scheduleEditorLayout);
    editor.onDidChangeModelContent(() => {
      if (props.readOnly) return;
      const value = editor?.getValue() ?? '';
      if (value !== props.value) emit('update:value', value);
    });
    resizeObserver = new ResizeObserver(scheduleEditorLayout);
    resizeObserver.observe(containerRef.value);
    scheduleEditorLayout();
  });

  watch(
    () => props.value,
    (value) => {
      const model = editor?.getModel();
      if (model && model.getValue() !== value) model.setValue(value);
      scheduleEditorLayout();
    }
  );

  watch(
    () => props.language,
    async (language) => {
      if (language === 'json') await import('monaco-editor/esm/vs/language/json/monaco.contribution');
      if (language === 'sql') await import('monaco-editor/esm/vs/basic-languages/sql/sql.contribution');
      if (language === 'python') await import('monaco-editor/esm/vs/basic-languages/python/python.contribution');
      const model = editor?.getModel();
      if (model) monacoApi?.editor.setModelLanguage(model, language);
      scheduleEditorLayout();
    }
  );

  watch(
    () => props.readOnly,
    (readOnly) => {
      editor?.updateOptions({ readOnly });
    }
  );

  watch(
    () => [props.height, props.minHeight, props.maxHeight, props.autoHeight],
    scheduleEditorLayout
  );

  onBeforeUnmount(() => {
    disposed = true;
    if (layoutFrame !== null) window.cancelAnimationFrame(layoutFrame);
    resizeObserver?.disconnect();
    contentSizeDisposable?.dispose();
    editor?.dispose();
    layoutFrame = null;
    resizeObserver = null;
    contentSizeDisposable = null;
    editor = null;
  });
</script>

<style lang="less" scoped>
  .code-preview {
    width: 100%;
    min-width: 0;
    overflow: hidden;
    background: var(--app-surface-bg);
  }
</style>
