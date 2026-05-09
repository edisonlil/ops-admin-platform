import type { CSSProperties } from 'vue';
import type { GlobalThemeOverrides } from 'naive-ui';

export type Density = 'compact' | 'default' | 'comfortable';
export type CardStyle = 'bordered' | 'shadow' | 'flat';

export interface PrimitiveTokens {
  blue50: string;
  blue100: string;
  blue500: string;
  blue600: string;
  gray50: string;
  gray100: string;
  gray200: string;
  gray300: string;
  gray500: string;
  gray700: string;
  gray900: string;
  green500: string;
  amber500: string;
  red500: string;
  cyan500: string;
  white: string;
  fontFamilySans: string;
  fontSizeXs: string;
  fontSizeSm: string;
  fontSizeMd: string;
  fontSizeLg: string;
  radiusXs: string;
  radiusSm: string;
  radiusMd: string;
  radiusLg: string;
  spacingXs: string;
  spacingSm: string;
  spacingMd: string;
  spacingLg: string;
  borderWidthBase: string;
  shadowNone: string;
  shadowSm: string;
  shadowMd: string;
}

export interface SemanticTokens {
  primaryColor: string;
  primaryColorHover: string;
  primaryColorPressed: string;
  primaryColorSoft: string;
  successColor: string;
  warningColor: string;
  errorColor: string;
  infoColor: string;
  textColorBase: string;
  textColorSecondary: string;
  textColorMuted: string;
  pageBgColor: string;
  surfaceColor: string;
  surfaceMutedColor: string;
  borderColorBase: string;
  borderColorStrong: string;
  borderRadiusBase: string;
  fontFamilyBase: string;
  fontSizeBase: string;
  shadowBase: string;
}

export interface ButtonTokens {
  radius: string;
  height: string;
  paddingX: string;
  primaryBg: string;
  primaryBgHover: string;
  primaryBgPressed: string;
  primaryText: string;
  borderColor: string;
}

export interface FieldTokens {
  radius: string;
  height: string;
  borderColor: string;
  focusBorderColor: string;
  bgColor: string;
}

export interface FormTokens {
  labelTextColor: string;
  feedbackTextColor: string;
  itemMarginBottom: string;
}

export interface DataTableTokens {
  bodyBg: string;
  headerBg: string;
  headerHoverBg: string;
  rowHoverBg: string;
  rowStripedBg: string;
  rowSortingBg: string;
  rowSelectedBg: string;
  rowSelectedHoverBg: string;
  borderColor: string;
  thTextColor: string;
  tdTextColor: string;
  thHeight: string;
  tdHeight: string;
  cellPaddingX: string;
  cellPaddingY: string;
  radius: string;
  selectionColor: string;
  selectionBorderColor: string;
  selectionColumnWidth: string;
  fixedColumnShadow: string;
  emptyTextColor: string;
  loadingColor: string;
  expandedRowBg: string;
}

export interface TableToolbarTokens {
  minHeight: string;
  bgColor: string;
  borderColor: string;
  radius: string;
  paddingX: string;
  paddingY: string;
  gap: string;
  titleTextColor: string;
  iconColor: string;
  iconHoverBg: string;
  iconHoverColor: string;
}

export interface TableSearchTokens {
  bgColor: string;
  borderColor: string;
  radius: string;
  paddingX: string;
  paddingY: string;
  fieldGap: string;
  rowGap: string;
  labelWidth: string;
  inputWidth: string;
  actionGap: string;
}

export interface TableBatchActionTokens {
  minHeight: string;
  bgColor: string;
  borderColor: string;
  radius: string;
  paddingX: string;
  gap: string;
  textColor: string;
}

export interface StatusTagTokens {
  radius: string;
  height: string;
  paddingX: string;
  fontWeight: string;
  successText: string;
  successBg: string;
  successBorder: string;
  warningText: string;
  warningBg: string;
  warningBorder: string;
  errorText: string;
  errorBg: string;
  errorBorder: string;
  infoText: string;
  infoBg: string;
  infoBorder: string;
  neutralText: string;
  neutralBg: string;
  neutralBorder: string;
}

export interface TableActionTokens {
  gap: string;
  buttonHeight: string;
  buttonPaddingX: string;
  buttonRadius: string;
  defaultTextColor: string;
  defaultBgColor: string;
  defaultBorderColor: string;
  primaryTextColor: string;
  primaryBgColor: string;
  primaryBorderColor: string;
  dangerTextColor: string;
  dangerBgColor: string;
  dangerBorderColor: string;
  disabledTextColor: string;
  disabledBgColor: string;
  disabledBorderColor: string;
  moreIconColor: string;
  confirmWidth: string;
  confirmRadius: string;
  confirmBgColor: string;
  confirmBorderColor: string;
  confirmShadow: string;
}

export interface SurfaceTokens {
  radius: string;
  borderColor: string;
  bgColor: string;
  shadow: string;
}

export interface MenuTokens {
  itemHeight: string;
  itemTextColor: string;
  itemTextColorActive: string;
  itemBgActive: string;
  itemBgHover: string;
  itemTextColorInverted: string;
  itemTextColorActiveInverted: string;
  itemBgActiveInverted: string;
  itemBgHoverInverted: string;
}

export interface ComponentTokens {
  Button: ButtonTokens;
  Form: FormTokens;
  Input: FieldTokens;
  InputNumber: FieldTokens;
  Select: FieldTokens;
  Switch: {
    railColorActive: string;
  };
  Checkbox: {
    borderColor: string;
    borderColorChecked: string;
  };
  Radio: {
    borderColor: string;
    dotColorActive: string;
  };
  DataTable: DataTableTokens;
  TableToolbar: TableToolbarTokens;
  TableSearch: TableSearchTokens;
  TableBatchAction: TableBatchActionTokens;
  StatusTag: StatusTagTokens;
  TableAction: TableActionTokens;
  Pagination: {
    itemRadius: string;
    itemBorderColor: string;
    itemColorActive: string;
  };
  Dropdown: SurfaceTokens;
  Tag: {
    radius: string;
    primaryText: string;
    primaryBg: string;
    borderColor: string;
  };
  Card: SurfaceTokens;
  Modal: SurfaceTokens;
  Drawer: SurfaceTokens;
  Menu: MenuTokens;
  Tooltip: {
    bgColor: string;
    textColor: string;
  };
  LoadingBar: {
    color: string;
  };
}

export interface LayoutTokens {
  density: Density;
  headerHeight: number;
  tabsHeight: number;
  menuWidth: number;
  collapsedMenuWidth: number;
  contentPadding: number;
  pageMaxWidth: string;
  cardStyle: CardStyle;
  tableDensity: Density;
}

export interface ProjectBehaviorOverrides {
  navMode?: string;
  navTheme?: string;
  headerSetting?: {
    fixed?: boolean;
    isReload?: boolean;
  };
  menuSetting?: {
    mixMenu?: boolean;
  };
  multiTabsSetting?: {
    fixed?: boolean;
    show?: boolean;
  };
  crumbsSetting?: {
    show?: boolean;
    showIcon?: boolean;
  };
  isPageAnimate?: boolean;
  pageAnimateType?: string;
}

export interface AppearanceTokens {
  primitive: PrimitiveTokens;
  semantic: SemanticTokens;
  component: ComponentTokens;
  layout: LayoutTokens;
}

export interface AppearancePreset {
  id: string;
  name: string;
  description: string;
  skinClass?: string;
  tokens: AppearanceTokens;
  darkSemantic?: Partial<SemanticTokens>;
}

export interface TokenValidationError {
  path: string;
  code: string;
  message: string;
}

export interface ResolvedAppearance {
  tokens: AppearanceTokens;
  errors: TokenValidationError[];
}

export type AppearanceCssVars = CSSProperties & Record<`--${string}`, string>;

export interface RuntimeAppearance {
  themeOverrides: GlobalThemeOverrides;
  cssVars: AppearanceCssVars;
  layoutConfig: LayoutTokens;
}

export type TokenOverrides = Partial<{
  primitive: Partial<PrimitiveTokens>;
  semantic: Partial<SemanticTokens>;
  darkSemantic: Partial<SemanticTokens>;
  component: Partial<Record<keyof ComponentTokens, Record<string, string>>>;
}>;

export interface AppearanceStoragePayload {
  version: number;
  presetId: string;
  tokenOverrides: TokenOverrides;
  layoutOverrides: Partial<LayoutTokens>;
  projectOverrides?: ProjectBehaviorOverrides;
  skinClass: string;
}
