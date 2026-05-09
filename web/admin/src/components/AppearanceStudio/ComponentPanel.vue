<template>
  <div class="component-token-panel">
    <section v-if="activeTarget === 'Button'" class="component-token-panel__section">
      <header class="component-token-panel__header">
        <span>组件样式</span>
        <strong>按钮</strong>
      </header>
      <TokenColorRow
        label="主按钮背景"
        token-path="component.Button.primaryBg"
        :model-value="component.Button.primaryBg"
        :resolved-value="resolved.Button.primaryBg"
        @update:model-value="(value) => update('Button', 'primaryBg', value)"
      />
      <TokenColorRow
        label="主按钮悬停"
        token-path="component.Button.primaryBgHover"
        :model-value="component.Button.primaryBgHover"
        :resolved-value="resolved.Button.primaryBgHover"
        @update:model-value="(value) => update('Button', 'primaryBgHover', value)"
      />
      <TokenColorRow
        label="主按钮按下"
        token-path="component.Button.primaryBgPressed"
        :model-value="component.Button.primaryBgPressed"
        :resolved-value="resolved.Button.primaryBgPressed"
        @update:model-value="(value) => update('Button', 'primaryBgPressed', value)"
      />
      <TokenSizeRow
        label="圆角"
        token-path="component.Button.radius"
        :model-value="component.Button.radius"
        :resolved-value="resolved.Button.radius"
        :min="0"
        :max="32"
        @update:model-value="(value) => update('Button', 'radius', value)"
      />
      <TokenSizeRow
        label="高度"
        token-path="component.Button.height"
        :model-value="component.Button.height"
        :min="24"
        :max="64"
        @update:model-value="(value) => update('Button', 'height', value)"
      />
    </section>

    <section v-else-if="activeTarget === 'Field'" class="component-token-panel__section">
      <header class="component-token-panel__header">
        <span>组件样式</span>
        <strong>表单控件</strong>
      </header>
      <TokenColorRow
        label="输入框边框"
        token-path="component.Input.borderColor"
        :model-value="component.Input.borderColor"
        :resolved-value="resolved.Input.borderColor"
        @update:model-value="(value) => update('Input', 'borderColor', value)"
      />
      <TokenColorRow
        label="输入框聚焦"
        token-path="component.Input.focusBorderColor"
        :model-value="component.Input.focusBorderColor"
        :resolved-value="resolved.Input.focusBorderColor"
        @update:model-value="(value) => update('Input', 'focusBorderColor', value)"
      />
      <TokenSizeRow
        label="输入框高度"
        token-path="component.Input.height"
        :model-value="component.Input.height"
        :min="24"
        :max="64"
        @update:model-value="(value) => update('Input', 'height', value)"
      />
      <TokenSizeRow
        label="选择器高度"
        token-path="component.Select.height"
        :model-value="component.Select.height"
        :min="24"
        :max="64"
        @update:model-value="(value) => update('Select', 'height', value)"
      />
    </section>

    <section v-else-if="activeTarget === 'DataTable'" class="component-token-panel__section">
      <header class="component-token-panel__header">
        <span>组件样式</span>
        <strong>数据表格</strong>
      </header>
      <TokenColorRow
        label="表格背景"
        token-path="component.DataTable.bodyBg"
        :model-value="component.DataTable.bodyBg"
        :resolved-value="resolved.DataTable.bodyBg"
        @update:model-value="(value) => update('DataTable', 'bodyBg', value)"
      />
      <TokenColorRow
        label="表头背景"
        token-path="component.DataTable.headerBg"
        :model-value="component.DataTable.headerBg"
        :resolved-value="resolved.DataTable.headerBg"
        @update:model-value="(value) => update('DataTable', 'headerBg', value)"
      />
      <TokenColorRow
        label="表头交互背景"
        token-path="component.DataTable.headerHoverBg"
        :model-value="component.DataTable.headerHoverBg"
        :resolved-value="resolved.DataTable.headerHoverBg"
        @update:model-value="(value) => update('DataTable', 'headerHoverBg', value)"
      />
      <TokenColorRow
        label="行悬停背景"
        token-path="component.DataTable.rowHoverBg"
        :model-value="component.DataTable.rowHoverBg"
        :resolved-value="resolved.DataTable.rowHoverBg"
        @update:model-value="(value) => update('DataTable', 'rowHoverBg', value)"
      />
      <TokenColorRow
        label="条纹行背景"
        token-path="component.DataTable.rowStripedBg"
        :model-value="component.DataTable.rowStripedBg"
        :resolved-value="resolved.DataTable.rowStripedBg"
        @update:model-value="(value) => update('DataTable', 'rowStripedBg', value)"
      />
      <TokenColorRow
        label="排序列背景"
        token-path="component.DataTable.rowSortingBg"
        :model-value="component.DataTable.rowSortingBg"
        :resolved-value="resolved.DataTable.rowSortingBg"
        @update:model-value="(value) => update('DataTable', 'rowSortingBg', value)"
      />
      <TokenColorRow
        label="选中行背景"
        token-path="component.DataTable.rowSelectedBg"
        :model-value="component.DataTable.rowSelectedBg"
        :resolved-value="resolved.DataTable.rowSelectedBg"
        @update:model-value="(value) => update('DataTable', 'rowSelectedBg', value)"
      />
      <TokenColorRow
        label="选中行悬停"
        token-path="component.DataTable.rowSelectedHoverBg"
        :model-value="component.DataTable.rowSelectedHoverBg"
        :resolved-value="resolved.DataTable.rowSelectedHoverBg"
        @update:model-value="(value) => update('DataTable', 'rowSelectedHoverBg', value)"
      />
      <TokenColorRow
        label="正文文字"
        token-path="component.DataTable.tdTextColor"
        :model-value="component.DataTable.tdTextColor"
        :resolved-value="resolved.DataTable.tdTextColor"
        @update:model-value="(value) => update('DataTable', 'tdTextColor', value)"
      />
      <TokenSizeRow
        label="表头高度"
        token-path="component.DataTable.thHeight"
        :model-value="component.DataTable.thHeight"
        :min="28"
        :max="72"
        @update:model-value="(value) => update('DataTable', 'thHeight', value)"
      />
      <TokenSizeRow
        label="单元格高度"
        token-path="component.DataTable.tdHeight"
        :model-value="component.DataTable.tdHeight"
        :min="28"
        :max="72"
        @update:model-value="(value) => update('DataTable', 'tdHeight', value)"
      />
      <TokenSizeRow
        label="横向内边距"
        token-path="component.DataTable.cellPaddingX"
        :model-value="component.DataTable.cellPaddingX"
        :min="4"
        :max="32"
        @update:model-value="(value) => update('DataTable', 'cellPaddingX', value)"
      />
      <TokenSizeRow
        label="纵向内边距"
        token-path="component.DataTable.cellPaddingY"
        :model-value="component.DataTable.cellPaddingY"
        :min="2"
        :max="24"
        @update:model-value="(value) => update('DataTable', 'cellPaddingY', value)"
      />
      <TokenSizeRow
        label="表格圆角"
        token-path="component.DataTable.radius"
        :model-value="component.DataTable.radius"
        :resolved-value="resolved.DataTable.radius"
        :min="0"
        :max="32"
        @update:model-value="(value) => update('DataTable', 'radius', value)"
      />
      <TokenColorRow
        label="选择框颜色"
        token-path="component.DataTable.selectionColor"
        :model-value="component.DataTable.selectionColor"
        :resolved-value="resolved.DataTable.selectionColor"
        @update:model-value="(value) => update('DataTable', 'selectionColor', value)"
      />
    </section>

    <section v-else-if="activeTarget === 'TableToolbar'" class="component-token-panel__section">
      <header class="component-token-panel__header">
        <span>组件样式</span>
        <strong>表格工具栏与筛选区</strong>
      </header>
      <TokenColorRow
        label="工具栏背景"
        token-path="component.TableToolbar.bgColor"
        :model-value="component.TableToolbar.bgColor"
        :resolved-value="resolved.TableToolbar.bgColor"
        @update:model-value="(value) => update('TableToolbar', 'bgColor', value)"
      />
      <TokenColorRow
        label="工具栏边框"
        token-path="component.TableToolbar.borderColor"
        :model-value="component.TableToolbar.borderColor"
        :resolved-value="resolved.TableToolbar.borderColor"
        @update:model-value="(value) => update('TableToolbar', 'borderColor', value)"
      />
      <TokenSizeRow
        label="工具栏高度"
        token-path="component.TableToolbar.minHeight"
        :model-value="component.TableToolbar.minHeight"
        :min="32"
        :max="72"
        @update:model-value="(value) => update('TableToolbar', 'minHeight', value)"
      />
      <TokenSizeRow
        label="工具栏圆角"
        token-path="component.TableToolbar.radius"
        :model-value="component.TableToolbar.radius"
        :resolved-value="resolved.TableToolbar.radius"
        :min="0"
        :max="32"
        @update:model-value="(value) => update('TableToolbar', 'radius', value)"
      />
      <TokenSizeRow
        label="筛选字段间距"
        token-path="component.TableSearch.fieldGap"
        :model-value="component.TableSearch.fieldGap"
        :min="4"
        :max="32"
        @update:model-value="(value) => update('TableSearch', 'fieldGap', value)"
      />
      <TokenSizeRow
        label="筛选输入宽度"
        token-path="component.TableSearch.inputWidth"
        :model-value="component.TableSearch.inputWidth"
        :min="140"
        :max="360"
        @update:model-value="(value) => update('TableSearch', 'inputWidth', value)"
      />
      <TokenColorRow
        label="批量栏背景"
        token-path="component.TableBatchAction.bgColor"
        :model-value="component.TableBatchAction.bgColor"
        :resolved-value="resolved.TableBatchAction.bgColor"
        @update:model-value="(value) => update('TableBatchAction', 'bgColor', value)"
      />
      <TokenSizeRow
        label="批量栏高度"
        token-path="component.TableBatchAction.minHeight"
        :model-value="component.TableBatchAction.minHeight"
        :min="28"
        :max="64"
        @update:model-value="(value) => update('TableBatchAction', 'minHeight', value)"
      />
    </section>

    <section v-else-if="activeTarget === 'StatusAction'" class="component-token-panel__section">
      <header class="component-token-panel__header">
        <span>组件样式</span>
        <strong>状态与表格操作</strong>
      </header>
      <TokenColorRow
        label="成功状态背景"
        token-path="component.StatusTag.successBg"
        :model-value="component.StatusTag.successBg"
        :resolved-value="resolved.StatusTag.successBg"
        @update:model-value="(value) => update('StatusTag', 'successBg', value)"
      />
      <TokenColorRow
        label="成功状态文字"
        token-path="component.StatusTag.successText"
        :model-value="component.StatusTag.successText"
        :resolved-value="resolved.StatusTag.successText"
        @update:model-value="(value) => update('StatusTag', 'successText', value)"
      />
      <TokenColorRow
        label="警告状态背景"
        token-path="component.StatusTag.warningBg"
        :model-value="component.StatusTag.warningBg"
        :resolved-value="resolved.StatusTag.warningBg"
        @update:model-value="(value) => update('StatusTag', 'warningBg', value)"
      />
      <TokenColorRow
        label="错误状态背景"
        token-path="component.StatusTag.errorBg"
        :model-value="component.StatusTag.errorBg"
        :resolved-value="resolved.StatusTag.errorBg"
        @update:model-value="(value) => update('StatusTag', 'errorBg', value)"
      />
      <TokenSizeRow
        label="状态标签高度"
        token-path="component.StatusTag.height"
        :model-value="component.StatusTag.height"
        :min="18"
        :max="40"
        @update:model-value="(value) => update('StatusTag', 'height', value)"
      />
      <TokenSizeRow
        label="状态标签圆角"
        token-path="component.StatusTag.radius"
        :model-value="component.StatusTag.radius"
        :resolved-value="resolved.StatusTag.radius"
        :min="0"
        :max="24"
        @update:model-value="(value) => update('StatusTag', 'radius', value)"
      />
      <TokenSizeRow
        label="操作按钮间距"
        token-path="component.TableAction.gap"
        :model-value="component.TableAction.gap"
        :min="0"
        :max="24"
        @update:model-value="(value) => update('TableAction', 'gap', value)"
      />
      <TokenSizeRow
        label="操作按钮高度"
        token-path="component.TableAction.buttonHeight"
        :model-value="component.TableAction.buttonHeight"
        :min="22"
        :max="48"
        @update:model-value="(value) => update('TableAction', 'buttonHeight', value)"
      />
      <TokenColorRow
        label="默认操作文字"
        token-path="component.TableAction.defaultTextColor"
        :model-value="component.TableAction.defaultTextColor"
        :resolved-value="resolved.TableAction.defaultTextColor"
        @update:model-value="(value) => update('TableAction', 'defaultTextColor', value)"
      />
      <TokenColorRow
        label="危险操作文字"
        token-path="component.TableAction.dangerTextColor"
        :model-value="component.TableAction.dangerTextColor"
        :resolved-value="resolved.TableAction.dangerTextColor"
        @update:model-value="(value) => update('TableAction', 'dangerTextColor', value)"
      />
      <TokenColorRow
        label="危险操作背景"
        token-path="component.TableAction.dangerBgColor"
        :model-value="component.TableAction.dangerBgColor"
        :resolved-value="resolved.TableAction.dangerBgColor"
        @update:model-value="(value) => update('TableAction', 'dangerBgColor', value)"
      />
      <TokenSizeRow
        label="确认层宽度"
        token-path="component.TableAction.confirmWidth"
        :model-value="component.TableAction.confirmWidth"
        :min="160"
        :max="360"
        @update:model-value="(value) => update('TableAction', 'confirmWidth', value)"
      />
    </section>

    <section v-else-if="activeTarget === 'Tree'" class="component-token-panel__section">
      <header class="component-token-panel__header">
        <span>组件样式</span>
        <strong>树组件</strong>
      </header>
      <TokenColorRow
        label="节点文字"
        token-path="component.Tree.textColor"
        :model-value="component.Tree.textColor"
        :resolved-value="resolved.Tree.textColor"
        @update:model-value="(value) => update('Tree', 'textColor', value)"
      />
      <TokenColorRow
        label="选中文字"
        token-path="component.Tree.textColorSelected"
        :model-value="component.Tree.textColorSelected"
        :resolved-value="resolved.Tree.textColorSelected"
        @update:model-value="(value) => update('Tree', 'textColorSelected', value)"
      />
      <TokenColorRow
        label="悬停背景"
        token-path="component.Tree.hoverBg"
        :model-value="component.Tree.hoverBg"
        :resolved-value="resolved.Tree.hoverBg"
        @update:model-value="(value) => update('Tree', 'hoverBg', value)"
      />
      <TokenColorRow
        label="选中背景"
        token-path="component.Tree.selectedBg"
        :model-value="component.Tree.selectedBg"
        :resolved-value="resolved.Tree.selectedBg"
        @update:model-value="(value) => update('Tree', 'selectedBg', value)"
      />
      <TokenSizeRow
        label="节点高度"
        token-path="component.Tree.nodeHeight"
        :model-value="component.Tree.nodeHeight"
        :min="24"
        :max="54"
        @update:model-value="(value) => update('Tree', 'nodeHeight', value)"
      />
      <TokenSizeRow
        label="节点缩进"
        token-path="component.Tree.indent"
        :model-value="component.Tree.indent"
        :min="12"
        :max="36"
        @update:model-value="(value) => update('Tree', 'indent', value)"
      />
      <TokenSizeRow
        label="节点圆角"
        token-path="component.Tree.nodeRadius"
        :model-value="component.Tree.nodeRadius"
        :resolved-value="resolved.Tree.nodeRadius"
        :min="0"
        :max="24"
        @update:model-value="(value) => update('Tree', 'nodeRadius', value)"
      />
    </section>

    <section v-else-if="activeTarget === 'Upload'" class="component-token-panel__section">
      <header class="component-token-panel__header">
        <span>组件样式</span>
        <strong>上传组件</strong>
      </header>
      <TokenColorRow
        label="卡片背景"
        token-path="component.Upload.itemBgColor"
        :model-value="component.Upload.itemBgColor"
        :resolved-value="resolved.Upload.itemBgColor"
        @update:model-value="(value) => update('Upload', 'itemBgColor', value)"
      />
      <TokenColorRow
        label="卡片边框"
        token-path="component.Upload.itemBorderColor"
        :model-value="component.Upload.itemBorderColor"
        :resolved-value="resolved.Upload.itemBorderColor"
        @update:model-value="(value) => update('Upload', 'itemBorderColor', value)"
      />
      <TokenColorRow
        label="悬停边框"
        token-path="component.Upload.itemBorderHoverColor"
        :model-value="component.Upload.itemBorderHoverColor"
        :resolved-value="resolved.Upload.itemBorderHoverColor"
        @update:model-value="(value) => update('Upload', 'itemBorderHoverColor', value)"
      />
      <TokenColorRow
        label="触发区背景"
        token-path="component.Upload.triggerBgColor"
        :model-value="component.Upload.triggerBgColor"
        :resolved-value="resolved.Upload.triggerBgColor"
        @update:model-value="(value) => update('Upload', 'triggerBgColor', value)"
      />
      <TokenColorRow
        label="触发区文字"
        token-path="component.Upload.triggerTextColor"
        :model-value="component.Upload.triggerTextColor"
        :resolved-value="resolved.Upload.triggerTextColor"
        @update:model-value="(value) => update('Upload', 'triggerTextColor', value)"
      />
      <TokenSizeRow
        label="卡片尺寸"
        token-path="component.Upload.itemSize"
        :model-value="component.Upload.itemSize"
        :min="72"
        :max="160"
        @update:model-value="(value) => update('Upload', 'itemSize', value)"
      />
      <TokenSizeRow
        label="卡片圆角"
        token-path="component.Upload.itemRadius"
        :model-value="component.Upload.itemRadius"
        :resolved-value="resolved.Upload.itemRadius"
        :min="0"
        :max="24"
        @update:model-value="(value) => update('Upload', 'itemRadius', value)"
      />
    </section>

    <section v-else class="component-token-panel__section">
      <header class="component-token-panel__header">
        <span>组件样式</span>
        <strong>外壳与内容面</strong>
      </header>
      <TokenColorRow
        label="菜单选中背景"
        token-path="component.Menu.itemBgActive"
        :model-value="component.Menu.itemBgActive"
        :resolved-value="resolved.Menu.itemBgActive"
        @update:model-value="(value) => update('Menu', 'itemBgActive', value)"
      />
      <TokenColorRow
        label="菜单悬停背景"
        token-path="component.Menu.itemBgHover"
        :model-value="component.Menu.itemBgHover"
        :resolved-value="resolved.Menu.itemBgHover"
        @update:model-value="(value) => update('Menu', 'itemBgHover', value)"
      />
      <TokenColorRow
        label="菜单选中文字"
        token-path="component.Menu.itemTextColorActive"
        :model-value="component.Menu.itemTextColorActive"
        :resolved-value="resolved.Menu.itemTextColorActive"
        @update:model-value="(value) => update('Menu', 'itemTextColorActive', value)"
      />
      <TokenColorRow
        label="深色菜单选中背景"
        token-path="component.Menu.itemBgActiveInverted"
        :model-value="component.Menu.itemBgActiveInverted"
        :resolved-value="resolved.Menu.itemBgActiveInverted"
        @update:model-value="(value) => update('Menu', 'itemBgActiveInverted', value)"
      />
      <TokenColorRow
        label="深色菜单悬停背景"
        token-path="component.Menu.itemBgHoverInverted"
        :model-value="component.Menu.itemBgHoverInverted"
        :resolved-value="resolved.Menu.itemBgHoverInverted"
        @update:model-value="(value) => update('Menu', 'itemBgHoverInverted', value)"
      />
      <TokenColorRow
        label="深色菜单选中文字"
        token-path="component.Menu.itemTextColorActiveInverted"
        :model-value="component.Menu.itemTextColorActiveInverted"
        :resolved-value="resolved.Menu.itemTextColorActiveInverted"
        @update:model-value="(value) => update('Menu', 'itemTextColorActiveInverted', value)"
      />
      <TokenSizeRow
        label="卡片圆角"
        token-path="component.Card.radius"
        :model-value="component.Card.radius"
        :resolved-value="resolved.Card.radius"
        :min="0"
        :max="32"
        @update:model-value="(value) => update('Card', 'radius', value)"
      />
      <TokenSizeRow
        label="弹窗圆角"
        token-path="component.Modal.radius"
        :model-value="component.Modal.radius"
        :resolved-value="resolved.Modal.radius"
        :min="0"
        :max="32"
        @update:model-value="(value) => update('Modal', 'radius', value)"
      />
    </section>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import TokenColorRow from './TokenColorRow.vue';
  import TokenSizeRow from './TokenSizeRow.vue';

  const props = defineProps<{
    target?: string;
  }>();

  const appearanceStore = useAppearanceStore();
  const component = computed(() => appearanceStore.editorMergedTokens.component);
  const resolved = computed(() => appearanceStore.editorResolvedTokens.component);
  const activeTarget = computed(() => props.target || 'Button');

  function update(componentName: string, key: string, value: string) {
    appearanceStore.updateComponentToken(componentName, key, value);
  }
</script>

<style lang="less" scoped>
  .component-token-panel {
    min-width: 0;
  }

  .component-token-panel__section {
    display: grid;
    gap: 0;
    min-width: 0;
  }

  .component-token-panel__header {
    display: grid;
    gap: 2px;
    margin-bottom: 14px;

    span {
      color: var(--app-icon-color);
      font-size: var(--app-font-size-base, 14px);
      line-height: 18px;
    }

    strong {
      color: var(--app-text-color);
      font-size: calc(var(--app-font-size-base, 14px) + 6px);
      font-weight: 700;
      line-height: 26px;
    }
  }
</style>
