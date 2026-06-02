import type { AppearancePreset } from '../types';
import { primevueLikePreset } from './primevueLike';

export const compactEnterprisePreset: AppearancePreset = {
  id: 'compact-enterprise',
  name: '紧凑企业风',
  description: '压缩表格和表单高度，适合高频后台审核和运维操作。',
  skinClass: 'skin-primevue-like skin-compact-enterprise',
  tokens: {
    primitive: {
      ...primevueLikePreset.tokens.primitive,
      radiusMd: '4px',
      radiusLg: '6px',
      fontSizeMd: '13px',
      spacingMd: '10px',
      spacingLg: '12px',
    },
    semantic: {
      ...primevueLikePreset.tokens.semantic,
      fontSizeBase: '{fontSizeMd}',
    },
    component: {
      ...primevueLikePreset.tokens.component,
      Button: {
        ...primevueLikePreset.tokens.component.Button,
        height: '30px',
        paddingX: '10px',
      },
      Input: {
        ...primevueLikePreset.tokens.component.Input,
        height: '30px',
      },
      InputNumber: {
        ...primevueLikePreset.tokens.component.InputNumber,
        height: '30px',
      },
      Select: {
        ...primevueLikePreset.tokens.component.Select,
        height: '30px',
      },
      Form: {
        ...primevueLikePreset.tokens.component.Form,
        itemMarginBottom: '10px',
      },
      DataTable: {
        ...primevueLikePreset.tokens.component.DataTable,
        thHeight: '36px',
        tdHeight: '36px',
        cellPaddingX: '10px',
        cellPaddingY: '6px',
        selectionColumnWidth: '42px',
      },
      TableToolbar: {
        ...primevueLikePreset.tokens.component.TableToolbar,
        minHeight: '38px',
        paddingX: '10px',
        paddingY: '8px',
        gap: '8px',
      },
      TableSearch: {
        ...primevueLikePreset.tokens.component.TableSearch,
        paddingX: '10px',
        paddingY: '10px',
        fieldGap: '8px',
        rowGap: '8px',
        labelWidth: '76px',
        inputWidth: '200px',
      },
      TableBatchAction: {
        ...primevueLikePreset.tokens.component.TableBatchAction,
        minHeight: '34px',
        paddingX: '10px',
        gap: '6px',
      },
      TableAction: {
        ...primevueLikePreset.tokens.component.TableAction,
        gap: '6px',
        buttonHeight: '28px',
        buttonPaddingX: '10px',
        confirmWidth: '200px',
      },
      Menu: {
        ...primevueLikePreset.tokens.component.Menu,
        itemHeight: '36px',
      },
      Tree: {
        ...primevueLikePreset.tokens.component.Tree,
        nodeHeight: '30px',
        indent: '18px',
        iconSize: '16px',
      },
      Upload: {
        ...primevueLikePreset.tokens.component.Upload,
        itemSize: '88px',
        itemPadding: '6px',
      },
    },
    layout: {
      ...primevueLikePreset.tokens.layout,
      density: 'compact',
      headerHeight: 56,
      tabsHeight: 38,
      contentPadding: 10,
      tableDensity: 'compact',
    },
    page: {
      ...primevueLikePreset.tokens.page,
      density: 'compact',
      variant: 'dense-data',
      header: {
        ...primevueLikePreset.tokens.page.header,
        minHeight: 60,
        paddingBlock: 10,
        titleSize: 18,
      },
      section: {
        ...primevueLikePreset.tokens.page.section,
        gap: 8,
        blockMargin: 8,
      },
      filter: {
        ...primevueLikePreset.tokens.page.filter,
        minHeight: 36,
        padding: 8,
        fieldGap: 8,
        rowGap: 8,
        labelWidth: 76,
      },
      toolbar: {
        ...primevueLikePreset.tokens.page.toolbar,
        minHeight: 36,
        gap: 8,
        paddingInline: 10,
      },
      table: {
        ...primevueLikePreset.tokens.page.table,
        rowHeight: 36,
        headerHeight: 36,
        cellPaddingInline: 10,
      },
      card: {
        ...primevueLikePreset.tokens.page.card,
        padding: 12,
        gap: 8,
      },
    },
  },
  darkSemantic: {
    ...primevueLikePreset.darkSemantic,
  },
  darkComponent: {
    ...primevueLikePreset.darkComponent,
  },
};
