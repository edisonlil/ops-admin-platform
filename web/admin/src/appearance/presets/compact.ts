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
      },
      TableAction: {
        ...primevueLikePreset.tokens.component.TableAction,
        gap: '6px',
        buttonHeight: '28px',
        buttonPaddingX: '10px',
      },
      Menu: {
        ...primevueLikePreset.tokens.component.Menu,
        itemHeight: '36px',
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
  },
};
